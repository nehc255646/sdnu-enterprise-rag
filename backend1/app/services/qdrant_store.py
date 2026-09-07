"""Qdrant collection helpers with mandatory tenant_id payload filter."""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import Settings, get_settings


@lru_cache
def get_qdrant() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_path:
        return QdrantClient(path=settings.qdrant_path)
    url = (settings.qdrant_url or "").strip()
    if not url:
        raise RuntimeError("Set QDRANT_URL or QDRANT_PATH")
    return QdrantClient(url=url, api_key=settings.qdrant_api_key or None)


def ensure_collection(vector_size: int, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    client = get_qdrant()
    name = settings.qdrant_collection
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )
    # payload indexes matter on server Qdrant; local mode warns and ignores
    for field in ("tenant_id", "document_id", "doc_type"):
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


def upsert_chunks(
    *,
    vectors: list[list[float]],
    texts: list[str],
    tenant_id: str,
    document_id: str,
    doc_type: str,
    filename: str,
    settings: Settings | None = None,
) -> list[str]:
    settings = settings or get_settings()
    client = get_qdrant()
    if not vectors:
        return []
    ensure_collection(len(vectors[0]), settings)
    point_ids: list[str] = []
    points: list[qm.PointStruct] = []
    for i, (vec, text) in enumerate(zip(vectors, texts, strict=True)):
        pid = str(uuid.uuid4())
        point_ids.append(pid)
        points.append(
            qm.PointStruct(
                id=pid,
                vector=vec,
                payload={
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "doc_type": doc_type,
                    "chunk_index": i,
                    "filename": filename,
                    "text": text,
                },
            )
        )
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return point_ids


def search(
    *,
    query_vector: list[float],
    tenant_id: str,
    top_k: int = 5,
    doc_type: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    client = get_qdrant()
    must = [qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=tenant_id))]
    if doc_type:
        must.append(qm.FieldCondition(key="doc_type", match=qm.MatchValue(value=doc_type)))
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=qm.Filter(must=must),
        limit=top_k,
        with_payload=True,
    )
    results: list[dict[str, Any]] = []
    for h in response.points:
        payload = h.payload or {}
        results.append(
            {
                "score": float(h.score or 0.0),
                "point_id": str(h.id),
                "text": payload.get("text", ""),
                "document_id": payload.get("document_id"),
                "doc_type": payload.get("doc_type"),
                "chunk_index": payload.get("chunk_index"),
                "filename": payload.get("filename"),
                "tenant_id": payload.get("tenant_id"),
            }
        )
    return results


def delete_by_document(document_id: str, tenant_id: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    client = get_qdrant()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qm.FilterSelector(
            filter=qm.Filter(
                must=[
                    qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=tenant_id)),
                    qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id)),
                ]
            )
        ),
    )
