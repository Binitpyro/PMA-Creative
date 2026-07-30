"""Zeni RAG Agent for retrieving scene context and synthesizing answers via PMA Core Provider Layer."""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from typing import Any, Generator, Iterable, Optional

from src.core.pma_llm import chat as pma_llm_chat
from src.core.zeni_prompt import (
    ZENI_SYSTEM_PROMPT,
    format_cacheable_prompt,
    format_scene_context,
)

logger = logging.getLogger("zeni.agent")


def _fts_query(q: str) -> str:
    """Sanitize search query for FTS5 preserving @P, v@vel, and VEX tokens."""
    toks = [t for t in re.findall(r"[A-Za-z0-9_@]+", q) if len(t) > 1]
    if not toks:
        toks = [q.strip()] if q.strip() else ["*"]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in toks)


def _route_prompt(question: str, chunks: Iterable[dict[str, Any]]) -> str:
    """Deterministic prompt router based on question keywords and retrieved node types."""
    q_lower = question.lower()
    types_lower = " ".join(str(c.get("node_type", "")).lower() for c in chunks)

    if any(k in q_lower or k in types_lower for k in ["wrangle", "vex", "@"]):
        return "vex_expert"
    elif any(k in q_lower or k in types_lower for k in ["pyro", "flip", "vellum", "rbd", "solver", "substep"]):
        return "sim_debugger"
    else:
        return "copilot_td"


class ZeniAgent:
    """RAG retriever and answer coordinator for Zeni in Houdini."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_path = os.environ.get("ZENI_DB_PATH", os.path.join("data", "zeni.db"))
        self.db_path = db_path
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite FTS5 database schema with sync triggers."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scene_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    hip_file TEXT,
                    node_path TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    comment TEXT,
                    wrangle_code TEXT,
                    non_default_params TEXT,
                    errors TEXT,
                    houdini_version TEXT,
                    platform TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS scene_chunks_fts USING fts5(
                    node_path, node_type, comment, wrangle_code, errors,
                    content='scene_chunks',
                    content_rowid='id',
                    tokenize="unicode61 tokenchars '@'"
                )
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS sc_ai AFTER INSERT ON scene_chunks BEGIN
                    INSERT INTO scene_chunks_fts(rowid, node_path, node_type, comment, wrangle_code, errors)
                    VALUES (new.id, new.node_path, new.node_type, new.comment, new.wrangle_code, new.errors);
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS sc_ad AFTER DELETE ON scene_chunks BEGIN
                    INSERT INTO scene_chunks_fts(scene_chunks_fts, rowid, node_path, node_type, comment, wrangle_code, errors)
                    VALUES ('delete', old.id, old.node_path, old.node_type, old.comment, old.wrangle_code, old.errors);
                END;
            """)
            conn.commit()
        finally:
            conn.close()

    def ingest_scene(
        self,
        project_name: str,
        hip_file: str,
        chunks: list[dict[str, Any]],
        houdini_version: str = "",
        platform: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Ingest extracted node graph chunks into SQLite FTS5 using O(1) executemany batching."""
        if not chunks:
            return {"status": "success", "chunks_ingested": 0, "project_name": project_name}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scene_chunks WHERE project_name = ?", (project_name,))

            insert_rows = []
            for chunk in chunks:
                path = chunk.get("node_path") or chunk.get("path", "")
                node_type = chunk.get("node_type") or chunk.get("type", "")
                comment = chunk.get("comment", "")
                vex_snippet = chunk.get("vex_snippet") or chunk.get("wrangle_code", "")
                errors = chunk.get("errors", [])
                err_str = "; ".join(errors) if isinstance(errors, list) else str(errors)
                params = chunk.get("non_default_parms") or chunk.get("non_default_params", {})
                param_str = json.dumps(params) if isinstance(params, dict) else str(params)

                insert_rows.append((
                    project_name, hip_file, path, node_type, comment,
                    vex_snippet, param_str, err_str, houdini_version, platform
                ))

            cursor.executemany("""
                INSERT INTO scene_chunks (
                    project_name, hip_file, node_path, node_type, comment,
                    wrangle_code, non_default_params, errors, houdini_version, platform
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, insert_rows)

            conn.commit()
            return {
                "status": "success",
                "chunks_ingested": len(insert_rows),
                "project_name": project_name,
            }
        except sqlite3.Error as e:
            logger.error(f"Failed ingesting scene chunks into SQLite: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def retrieve_relevant_chunks(
        self, query: str, project_name: Optional[str] = None, limit: int = 10
    ) -> Generator[dict[str, Any], None, None]:
        """Stream relevant node graph chunks from SQLite FTS5 ordered by rank."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            fts_q = _fts_query(query)

            if project_name:
                sql = """
                SELECT c.node_path, c.node_type, c.comment, c.wrangle_code, c.non_default_params, c.errors
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ? AND c.project_name = ?
                ORDER BY rank
                LIMIT ?
                """
                params = (fts_q, project_name, limit)
            else:
                sql = """
                SELECT c.node_path, c.node_type, c.comment, c.wrangle_code, c.non_default_params, c.errors
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """
                params = (fts_q, limit)

            cursor.execute(sql, params)
            for row in cursor:
                code_val = row["wrangle_code"] or ""
                params_val = row["non_default_params"] or ""
                yield {
                    "node_path": row["node_path"],
                    "node_type": row["node_type"],
                    "comment": row["comment"] or "",
                    "vex_snippet": code_val,
                    "wrangle_code": code_val,
                    "non_default_parms": params_val,
                    "non_default_params": params_val,
                    "errors": row["errors"] or "",
                }
        except sqlite3.Error as e:
            logger.error(f"FTS5 retrieval query failed: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def build_prompt(
        self,
        question: str,
        chunks: Iterable[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
        prompt_name: Optional[str] = None,
    ) -> str:
        """Construct prompt payload using deterministic prompt routing."""
        chunk_list = list(chunks)
        selected_prompt = prompt_name or _route_prompt(question, chunk_list)
        context_str = format_scene_context(metadata or {}, chunk_list)
        return format_cacheable_prompt(
            prompt_name=selected_prompt,
            context_data=context_str,
            user_query=question,
        )

    def generate_answer(
        self,
        question: str,
        chunks: Iterable[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Synthesize answer using Core provider layer or test client injection."""
        full_prompt = self.build_prompt(question, chunks, metadata)

        if llm_client:
            return llm_client.generate(full_prompt)

        try:
            messages = [{"role": "user", "content": full_prompt}]
            return pma_llm_chat(messages, provider=provider, model=model)
        except Exception as e:
            logger.warning(f"Core LLM chat request failed: {e}")
            return (
                "### Root Cause\n"
                f"Unable to complete LLM synthesis through PMA Core.\n\n"
                "### Diagnostic Info\n"
                f"{e}\n\n"
                "### Action Required\n"
                "1. Check that PMA Core is running at `http://localhost:8000`.\n"
                "2. Ensure a valid Provider and Model are configured in Zeni Settings.\n"
            )

    def cross_search(
        self,
        question: str,
        exclude_hip: Optional[str] = None,
        limit: int = 5,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search across indexed projects and synthesize cross-project answer."""
        conn = self._get_connection()
        results = []
        try:
            cursor = conn.cursor()
            fts_q = _fts_query(question)

            if exclude_hip:
                sql = """
                SELECT DISTINCT c.project_name, c.hip_file, c.node_path, c.node_type, c.wrangle_code
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ? AND (c.hip_file IS NULL OR c.hip_file != ?)
                ORDER BY rank
                LIMIT ?
                """
                params = (fts_q, exclude_hip, limit)
            else:
                sql = """
                SELECT DISTINCT c.project_name, c.hip_file, c.node_path, c.node_type, c.wrangle_code
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """
                params = (fts_q, limit)

            cursor.execute(sql, params)
            for row in cursor:
                results.append({
                    "project_name": row["project_name"],
                    "hip_file": row["hip_file"] or "",
                    "node_path": row["node_path"],
                    "node_type": row["node_type"],
                    "vex_snippet": row["wrangle_code"] or "",
                })
        except sqlite3.Error as e:
            logger.error(f"Cross search FTS query failed: {e}", exc_info=True)
            raise
        finally:
            conn.close()

        # Build prompt and generate answer via LLM
        prompt = format_cacheable_prompt(
            prompt_name="cross_search",
            context_data=json.dumps(results, indent=2),
            user_query=question,
        )
        try:
            answer = pma_llm_chat([{"role": "user", "content": prompt}], provider=provider, model=model)
        except Exception as e:
            answer = f"Cross-project solution lookup completed with {len(results)} matches, but LLM synthesis failed: {e}"

        return {"answer": answer, "results": results}

    def list_projects(self) -> list[dict[str, Any]]:
        """List distinct indexed projects in the database."""
        conn = self._get_connection()
        projects = []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT project_name, hip_file, COUNT(*) as node_count, MAX(created_at) as last_indexed
                FROM scene_chunks
                GROUP BY project_name
            """)
            for row in cursor:
                projects.append({
                    "project_name": row["project_name"],
                    "hip_file": row["hip_file"] or "",
                    "node_count": row["node_count"],
                    "last_indexed": str(row["last_indexed"]),
                })
        except sqlite3.Error as e:
            logger.error(f"Failed listing projects: {e}", exc_info=True)
            raise
        finally:
            conn.close()
        return projects
