#!/usr/bin/env python3
"""
ABS Memory API Server
HTTP API for the Starship OS Memory Layer
"""

from __future__ import annotations

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import memory
from memory import MemoryManager, MemoryType, simple_embed, cosine_similarity, _memory_to_dict

DB_PATH = os.environ.get("ABS_MEMORY_DB", "/data/abs_memory.db")

# Global memory manager
_manager = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = MemoryManager(os.environ.get("ABS_MEMORY_DB", "/data/abs_memory.db"))
    return _manager


class MemoryAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _parse_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode()
            return json.loads(body) if body else {}
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        try:
            mgr = get_manager()

            # Health check
            if path == "/api/health":
                self._send_json(200, {"status": "ok", "service": "abs-memory-api"})
                return

            # Stats
            if path == "/api/memory/stats":
                stats = mgr.stats()
                self._send_json(200, stats)
                return

            # Search
            if path == "/api/memory/search":
                query = params.get("q", [""])[0]
                agent = params.get("agent", [None])[0]
                mem_type = params.get("type", [None])[0]
                limit = int(params.get("limit", ["10"])[0])
                min_importance = float(params.get("min_importance", ["0.0"])[0])

                if mem_type:
                    try:
                        mem_type = MemoryType(mem_type)
                    except ValueError:
                        self._send_json(400, {"error": f"Invalid memory type: {mem_type}"})
                        return

                results = mgr.search(query, agent, mem_type, limit, min_importance)
                self._send_json(200, {"results": [_memory_to_dict(m) for m in results]})
                return

            # Context for agent
            if path.startswith("/api/memory/context/"):
                agent = path.split("/api/memory/context/")[1]
                query = params.get("q", [""])[0]
                max_tokens = int(params.get("max_tokens", ["2000"])[0])
                context = mgr.get_context(query, agent, max_tokens)
                self._send_json(200, {"context": context})
                return

            # Recall specific memory
            if path.startswith("/api/memory/recall/"):
                mem_id = path.split("/api/memory/recall/")[1]
                memory = mgr.recall(mem_id)
                if memory:
                    self._send_json(200, _memory_to_dict(memory))
                else:
                    self._send_json(404, {"error": "Memory not found"})
                return

            self._send_json(404, {"error": "Not found"})

        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            mgr = get_manager()
            body = self._parse_body()

            # Store
            if path == "/api/memory/store":
                agent = body.get("agent")
                mem_type = body.get("type")
                content = body.get("content")
                summary = body.get("summary", "")
                importance = float(body.get("importance", 0.5))
                metadata = body.get("metadata", {})

                if not agent or not mem_type or not content:
                    self._send_json(400, {"error": "Missing required fields: agent, type, content"})
                    return

                try:
                    mem_type = MemoryType(mem_type)
                except ValueError:
                    self._send_json(400, {"error": f"Invalid memory type: {mem_type}"})
                    return

                mem_id = mgr.store(agent, mem_type, content, summary, importance, metadata)
                self._send_json(201, {"id": mem_id})
                return

            # Consolidate
            if path == "/api/memory/consolidate":
                agent = body.get("agent")
                if not agent:
                    self._send_json(400, {"error": "Missing agent"})
                    return
                count = mgr.consolidate(agent)
                self._send_json(200, {"consolidated": count})
                return

            # Decay
            if path == "/api/memory/decay":
                rate = float(body.get("rate", 0.01))
                count = mgr.decay_all(rate)
                self._send_json(200, {"decayed": count})
                return

            self._send_json(404, {"error": "Not found"})

        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            mgr = get_manager()

            if path.startswith("/api/memory/forget/"):
                mem_id = path.split("/api/memory/forget/")[1]
                deleted = mgr.forget(mem_id)
                self._send_json(200, {"deleted": deleted})
                return

            self._send_json(404, {"error": "Not found"})

        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def log_message(self, format, *args):
        # Suppress default log messages
        pass


def run_server():
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("", port), MemoryAPIHandler)
    print(f"ABS Memory API server running on http://localhost:{port}")
    print(f"Database: {os.environ.get('ABS_MEMORY_DB', '/data/abs_memory.db')}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()