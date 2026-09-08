from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constants import DESIGN_DOCS, INDEX_VERSION, RERANKER_VERSION, ROOT
from .utils import sha256_file, sha256_text, stable_json, utc_now, write_json


class ContextManager:
    def __init__(self, factory_root: Path = ROOT, *, sources: tuple[str, ...] = DESIGN_DOCS) -> None:
        self.factory_root = factory_root
        self.sources = sources

    def source_manifest(self) -> list[dict[str, Any]]:
        manifest = []
        for index, rel_path in enumerate(self.sources, start=1):
            from .storage import safe_path
            path = safe_path(self.factory_root, rel_path)
            if path.exists():
                manifest.append(
                    {
                        "source_id": f"SRC-DOC-{index:03d}",
                        "type": "doc",
                        "path": rel_path,
                        "authorized": True,
                        "hash": sha256_file(path),
                        "trust": "trusted",
                    }
                )
        return manifest

    def chunk_sources(self) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        for source in self.source_manifest():
            text = (self.factory_root / source["path"]).read_text(encoding="utf-8")
            parts = re.split(r"(?m)^##\s+", text)
            for idx, part in enumerate(parts):
                content = part.strip()
                if not content:
                    continue
                chunk_id = f"{source['source_id']}.chunk.{idx:03d}"
                chunks.append(
                    {
                        "source_id": source["source_id"],
                        "chunk_id": chunk_id,
                        "path": source["path"],
                        "hash": sha256_text(content[:2400]),
                        "score": 0.0,
                        "rerank_score": 0.0,
                        "reason_included": "TBD",
                        "content": content[:2400],
                    }
                )
        return chunks

    def retrieve(self, query: str, *, limit: int = 10, threshold: float = 0.08) -> dict[str, Any]:
        terms = {term for term in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(term) > 2}
        ranked: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for chunk in self.chunk_sources():
            content = chunk["content"].lower()
            hits = sum(1 for term in terms if term in content)
            score = hits / max(len(terms), 1)
            rerank_score = round(score + (0.001 if "arnes" in content or "harness" in content else 0), 6)
            candidate = {**chunk, "score": round(score, 6), "rerank_score": rerank_score}
            if score >= threshold:
                candidate["reason_included"] = "coincidencia keyword deterministica con query y policy"
                ranked.append(candidate)
            else:
                excluded.append({"source_id": chunk["source_id"], "chunk_id": chunk["chunk_id"], "reason": "low_score"})

        ranked.sort(key=lambda item: (-item["rerank_score"], item["source_id"], item["chunk_id"]))
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in ranked:
            key = (item["source_id"], item["hash"])
            if key in seen:
                excluded.append({"source_id": item["source_id"], "chunk_id": item["chunk_id"], "reason": "duplicate"})
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= limit:
                break

        if not deduped:
            fallback = self.chunk_sources()[: min(limit, 7)]
            deduped = [{**item, "score": 0.08, "rerank_score": 0.08, "reason_included": "fallback minimo de documentos autorizados"} for item in fallback]

        corpus_hash = sha256_text(stable_json([(item["source_id"], item["hash"]) for item in self.source_manifest()]))
        query_hash = sha256_text(query)
        return {
            "context_pack_id": "CP-" + query_hash.split(":", 1)[1][:16],
            "query_hash": query_hash,
            "created_at": utc_now(),
            "index_version": INDEX_VERSION,
            "corpus_hash": corpus_hash,
            "reranker_version": RERANKER_VERSION,
            "score_threshold": threshold,
            "chunks": deduped,
            "excluded": excluded[:50],
        }

    def write_context_pack(self, run_dir: Path, query: str) -> dict[str, Any]:
        # Callers allocate a new cycle directory. Never rebind earlier evidence IDs.
        if (run_dir / "context-pack.json").exists() or (run_dir / "evidence-register.json").exists():
            raise ValueError("Context snapshot already exists; use a new cycle directory")
        context_pack = self.retrieve(query)
        write_json(run_dir / "context-pack.json", context_pack)
        evidence = []
        for index, chunk in enumerate(context_pack["chunks"], start=1):
            evidence.append(
                {
                    "evidence_id": f"EV-{index:03d}",
                    "source_id": chunk["source_id"],
                    "chunk_id": chunk["chunk_id"],
                    "path": chunk["path"],
                    "hash": chunk["hash"],
                    "claim_supported": chunk["reason_included"],
                    "trust": "trusted",
                }
            )
        write_json(run_dir / "evidence-register.json", {"records": evidence})
        return context_pack
