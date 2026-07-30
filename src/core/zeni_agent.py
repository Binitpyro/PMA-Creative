"""Zeni RAG Agent for retrieving scene context and synthesizing answers via Gemini."""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Generator, Iterable, Optional

from src.core.zeni_prompt import (
    ZENI_SYSTEM_PROMPT,
    format_cacheable_prompt,
    format_scene_context,
)


class ZeniAgent:
    """RAG retriever and answer coordinator for Zeni in Houdini."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("PMA_DB_PATH", ":memory:")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite FTS5 database schema if not exists."""
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
                    node_path, node_type, comment, wrangle_code, errors
                )
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
        """Ingest extracted node graph chunks into SQLite FTS5 using O(1) batch processing."""
        if not chunks:
            return {"status": "success", "chunks_ingested": 0, "project_name": project_name}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Clear previous entries for this project to maintain clean state
            cursor.execute("DELETE FROM scene_chunks WHERE project_name = ?", (project_name,))
            conn.commit()

            batch_size = 50
            chunks_ingested = 0

            for chunk in chunks:
                path = chunk.get("path") or chunk.get("node_path", "")
                node_type = chunk.get("type") or chunk.get("node_type", "")
                comment = chunk.get("comment", "")
                wrangle_code = chunk.get("wrangle_code", "")
                errors = chunk.get("errors", [])
                err_str = "; ".join(errors) if isinstance(errors, list) else str(errors)
                params = chunk.get("non_default_params", {})
                param_str = json.dumps(params) if isinstance(params, dict) else str(params)

                cursor.execute("""
                    INSERT INTO scene_chunks (
                        project_name, hip_file, node_path, node_type, comment,
                        wrangle_code, non_default_params, errors, houdini_version, platform
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_name, hip_file, path, node_type, comment,
                    wrangle_code, param_str, err_str, houdini_version, platform
                ))
                rowid = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO scene_chunks_fts (rowid, node_path, node_type, comment, wrangle_code, errors)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (rowid, path, node_type, comment, wrangle_code, err_str))

                chunks_ingested += 1

            conn.commit()

            return {
                "status": "success",
                "chunks_ingested": chunks_ingested,
                "project_name": project_name,
            }
        finally:
            conn.close()

    def retrieve_relevant_chunks(
        self, query: str, project_name: Optional[str] = None, limit: int = 10
    ) -> Generator[dict[str, Any], None, None]:
        """Stream relevant node graph chunks from SQLite FTS5 using O(1) cursor iterators."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            clean_query = " OR ".join(f'"{word}"' for word in query.split() if word.isalnum())
            if not clean_query:
                clean_query = query

            if project_name:
                sql = """
                SELECT c.node_path, c.node_type, c.comment, c.wrangle_code, c.non_default_params, c.errors
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ? AND c.project_name = ?
                LIMIT ?
                """
                params = (clean_query, project_name, limit)
            else:
                sql = """
                SELECT c.node_path, c.node_type, c.comment, c.wrangle_code, c.non_default_params, c.errors
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ?
                LIMIT ?
                """
                params = (clean_query, limit)

            cursor.execute(sql, params)
            for row in cursor:
                yield {
                    "node_path": row["node_path"],
                    "node_type": row["node_type"],
                    "comment": row["comment"] or "",
                    "wrangle_code": row["wrangle_code"] or "",
                    "non_default_params": row["non_default_params"] or "",
                    "errors": row["errors"] or "",
                }
        except sqlite3.Error:
            return
        finally:
            conn.close()

    def build_prompt(
        self,
        question: str,
        chunks: Iterable[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
        prompt_name: str = "copilot_td",
    ) -> str:
        """Construct the combined prompt payload for Gemini using prompt-caching prefix structure."""
        context_str = format_scene_context(metadata or {}, chunks)
        return format_cacheable_prompt(
            prompt_name=prompt_name,
            context_data=context_str,
            user_query=question,
        )

    def generate_answer(
        self,
        question: str,
        chunks: Iterable[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
    ) -> str:
        """Synthesize answer using Gemini LLM or client injection."""
        full_prompt = self.build_prompt(question, chunks, metadata)

        if llm_client:
            return llm_client.generate(full_prompt)

        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(full_prompt)
                return response.text
            except ImportError:
                pass

        return (
            "### Root Cause\n"
            "Unable to contact Gemini API service. Please verify `GEMINI_API_KEY` is set.\n\n"
            "### VEX / Node Fix\n"
            "Check that your environment has `GEMINI_API_KEY` configured.\n\n"
            "### Step-by-Step Instructions\n"
            "1. Export `GEMINI_API_KEY` in your shell.\n"
            "2. Restart PMA Core / Backend service.\n"
        )

    def cross_search(
        self, question: str, exclude_hip: Optional[str] = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search across all indexed projects excluding current scene."""
        conn = self._get_connection()
        results = []
        try:
            cursor = conn.cursor()
            clean_query = " OR ".join(f'"{word}"' for word in question.split() if word.isalnum())
            if not clean_query:
                clean_query = question

            if exclude_hip:
                sql = """
                SELECT DISTINCT c.project_name, c.hip_file, c.node_path, c.node_type, c.wrangle_code
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ? AND (c.hip_file IS NULL OR c.hip_file != ?)
                LIMIT ?
                """
                params = (clean_query, exclude_hip, limit)
            else:
                sql = """
                SELECT DISTINCT c.project_name, c.hip_file, c.node_path, c.node_type, c.wrangle_code
                FROM scene_chunks c
                JOIN scene_chunks_fts fts ON c.id = fts.rowid
                WHERE scene_chunks_fts MATCH ?
                LIMIT ?
                """
                params = (clean_query, limit)

            cursor.execute(sql, params)
            for row in cursor:
                results.append({
                    "project_name": row["project_name"],
                    "hip_file": row["hip_file"],
                    "node_path": row["node_path"],
                    "node_type": row["node_type"],
                    "wrangle_code": row["wrangle_code"],
                })
        except sqlite3.Error:
            pass
        finally:
            conn.close()
        return results

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
        except sqlite3.Error:
            pass
        finally:
            conn.close()
        return projects
