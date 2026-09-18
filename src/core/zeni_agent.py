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
    format_context,
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
            # For simplicity during migration to DCC-agnostic schema, drop old tables
            cursor.execute("DROP TABLE IF EXISTS scene_chunks")
            cursor.execute("DROP TABLE IF EXISTS scene_chunks_fts")
            
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
                    dcc_properties TEXT,
                    flags TEXT,
                    dependencies TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, node_path)
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
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS sc_au AFTER UPDATE ON scene_chunks BEGIN
                    INSERT INTO scene_chunks_fts(scene_chunks_fts, rowid, node_path, node_type, comment, wrangle_code, errors)
                    VALUES ('delete', old.id, old.node_path, old.node_type, old.comment, old.wrangle_code, old.errors);
                    INSERT INTO scene_chunks_fts(rowid, node_path, node_type, comment, wrangle_code, errors)
                    VALUES (new.id, new.node_path, new.node_type, new.comment, new.wrangle_code, new.errors);
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
            cursor.execute("BEGIN TRANSACTION")
            
            # Since this is a full sync, we delete existing nodes for this project first
            cursor.execute("DELETE FROM scene_chunks WHERE project_name = ?", (project_name,))

            insert_rows = []
            for chunk in chunks:
                path = chunk.get("node_path") or chunk.get("path", "")
                node_type = chunk.get("node_type") or chunk.get("type", "")
                comment = chunk.get("comment", "")
                
                dcc_props = chunk.get("dcc_properties", {})
                vex_snippet = dcc_props.get("code_snippet") or chunk.get("vex_snippet") or chunk.get("wrangle_code", "")
                
                errors = chunk.get("errors", [])
                err_str = "; ".join(errors) if isinstance(errors, list) else str(errors)
                params = chunk.get("non_default_parms") or chunk.get("non_default_params", {})
                param_str = json.dumps(params) if isinstance(params, dict) else str(params)
                
                flags = chunk.get("flags", {})
                flags_str = json.dumps(flags) if isinstance(flags, dict) else str(flags)
                
                deps = chunk.get("dependencies", [])
                deps_str = json.dumps(deps) if isinstance(deps, list) else str(deps)
                
                dcc_props_str = json.dumps(dcc_props) if isinstance(dcc_props, dict) else str(dcc_props)

                insert_rows.append((
                    project_name, hip_file, path, node_type, comment,
                    vex_snippet, param_str, err_str, houdini_version, platform,
                    dcc_props_str, flags_str, deps_str
                ))

            cursor.executemany("""
                INSERT INTO scene_chunks (
                    project_name, hip_file, node_path, node_type, comment,
                    wrangle_code, non_default_params, errors, houdini_version, platform,
                    dcc_properties, flags, dependencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, insert_rows)

            conn.commit()
            return {
                "status": "success",
                "chunks_ingested": len(insert_rows),
                "project_name": project_name,
            }
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed ingesting scene chunks into SQLite: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def upsert_nodes(self, project_name: str, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Atomically upsert multiple nodes."""
        if not nodes:
            return {"status": "success", "nodes_upserted": 0}
            
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            upsert_rows = []
            for chunk in nodes:
                path = chunk.get("node_path") or chunk.get("path", "")
                node_type = chunk.get("node_type") or chunk.get("type", "")
                comment = chunk.get("comment", "")
                
                dcc_props = chunk.get("dcc_properties", {})
                vex_snippet = dcc_props.get("code_snippet") or chunk.get("vex_snippet") or chunk.get("wrangle_code", "")
                
                errors = chunk.get("errors", [])
                err_str = "; ".join(errors) if isinstance(errors, list) else str(errors)
                params = chunk.get("non_default_parms") or chunk.get("non_default_params", {})
                param_str = json.dumps(params) if isinstance(params, dict) else str(params)
                
                flags = chunk.get("flags", {})
                flags_str = json.dumps(flags) if isinstance(flags, dict) else str(flags)
                
                deps = chunk.get("dependencies", [])
                deps_str = json.dumps(deps) if isinstance(deps, list) else str(deps)
                
                dcc_props_str = json.dumps(dcc_props) if isinstance(dcc_props, dict) else str(dcc_props)
                
                upsert_rows.append((
                    project_name, path, node_type, comment, vex_snippet, param_str, 
                    err_str, dcc_props_str, flags_str, deps_str
                ))

            cursor.executemany("""
                INSERT INTO scene_chunks (
                    project_name, node_path, node_type, comment,
                    wrangle_code, non_default_params, errors,
                    dcc_properties, flags, dependencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_name, node_path) DO UPDATE SET
                    node_type=excluded.node_type,
                    comment=excluded.comment,
                    wrangle_code=excluded.wrangle_code,
                    non_default_params=excluded.non_default_params,
                    errors=excluded.errors,
                    dcc_properties=excluded.dcc_properties,
                    flags=excluded.flags,
                    dependencies=excluded.dependencies
            """, upsert_rows)

            conn.commit()
            return {"status": "success", "nodes_upserted": len(upsert_rows)}
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed upserting scene nodes: {e}", exc_info=True)
            raise
        finally:
            conn.close()
            
    def delete_node(self, project_name: str, node_path: str) -> dict[str, Any]:
        """Atomically delete a node."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            cursor.execute("DELETE FROM scene_chunks WHERE project_name = ? AND node_path = ?", (project_name, node_path))
            conn.commit()
            return {"status": "success", "node_deleted": node_path}
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed deleting scene node: {e}", exc_info=True)
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
        """Construct prompt payload using deterministic prompt routing and fetch corpus."""
        import httpx
        chunk_list = list(chunks)
        selected_prompt = prompt_name or _route_prompt(question, chunk_list)
        
        corpus_chunks = []
        try:
            core_url = os.environ.get("PMA_CORE_URL", "http://127.0.0.1:8000")
            resp = httpx.post(f"{core_url}/api/corpus/retrieve", json={"query": question}, timeout=1.5)
            if resp.status_code == 200:
                corpus_chunks = resp.json().get("chunks", [])
        except Exception as e:
            logger.warning(f"Corpus retrieval failed or timed out: {e}")
            
        context_str = format_context(metadata or {}, chunk_list, corpus_chunks)
        return format_cacheable_prompt(
            prompt_name=selected_prompt,
            context_data=context_str,
            user_query=question,
        )

    def evaluate_node_insight(
        self,
        node_data: dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Evaluate a node for sidecar insights, using zero-cost heuristics as a gatekeeper."""
        node_path = node_data.get("node_path") or node_data.get("path", "")
        node_type = node_data.get("node_type") or node_data.get("type", "")
        dcc_props = node_data.get("dcc_properties", {})
        code_snippet = dcc_props.get("code_snippet") or node_data.get("vex_snippet") or ""
        errors = node_data.get("errors", [])

        # HEURISTIC 1: Basic Node Errors (Zero Cost)
        if errors:
            return {
                "insight_type": "Rule",
                "message": f"Node has active errors: {'; '.join(errors) if isinstance(errors, list) else str(errors)}"
            }

        # HEURISTIC 2: VEX Code Linting (Zero Cost)
        if code_snippet:
            if "vel" in code_snippet and "v@vel" not in code_snippet:
                return {
                    "insight_type": "Rule",
                    "message": "Potential VEX error: 'vel' used without vector qualifier 'v@vel'."
                }

        # HEURISTIC 3: Corpus Keyword Match (Zero Cost before LLM)
        # If code snippet or node name matches specific keywords, we can query corpus
        keywords = ["tonemap", "lookdev", "render", "flip", "pyro", "rbd", "vellum"]
        if not any(k in node_type.lower() or k in node_path.lower() for k in keywords):
            return None # Skip LLM if no heuristics pass

        # If it passed heuristics, query LLM for a high-confidence hit
        try:
            import httpx
            core_url = os.environ.get("PMA_CORE_URL", "http://127.0.0.1:8000")
            query = f"Check {node_type} ({node_path}) against standard practices."
            resp = httpx.post(f"{core_url}/api/corpus/retrieve", json={"query": query}, timeout=1.5)
            corpus_chunks = resp.json().get("chunks", []) if resp.status_code == 200 else []
            
            if not corpus_chunks:
                return None
                
            prompt = (
                f"You are evaluating a node: {node_path} ({node_type}).\n"
                f"Corpus mentions:\n{json.dumps(corpus_chunks)}\n"
                "If there is a clear contradiction or serendipitous connection, reply with a short 1-sentence insight. Otherwise reply 'NONE'."
            )
            answer = pma_llm_chat([{"role": "user", "content": prompt}], provider=provider, model=model)
            if "NONE" not in answer.strip().upper():
                return {
                    "insight_type": "AI Insight",
                    "message": answer.strip()
                }
        except Exception as e:
            logger.warning(f"Sidecar LLM evaluation failed: {e}")
            
        return None

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
