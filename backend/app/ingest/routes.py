from pathlib import Path
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db, get_session_factory
from app.core.deps import require_tenant
from app.ingest.pipeline import ALLOWED_UPLOAD_SUFFIXES, process_document
from app.ingest.redis_queue import enqueue_ingest
from app.ingest.retrieve import retrieve
from app.ingest.schemas import (
    DocumentListItem,
    DocumentListResponse,
    IngestCreateResponse,
    IngestStatusResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
)
from app.models import DocType, Document, IngestStatus

router = APIRouter()

_READ_CHUNK = 1024 * 64


def _tenant_upload_dir(upload_dir: str, tenant_id: str) -> Path:
    root = Path(upload_dir).resolve()
    dest_dir = (root / tenant_id).resolve()
    if dest_dir != root and root not in dest_dir.parents:
        raise HTTPException(status_code=400, detail="invalid upload path")
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir


def _write_upload(file: UploadFile, dest: Path, max_bytes: int) -> int:
    written = 0
    with dest.open("wb") as out:
        while True:
            chunk = file.file.read(_READ_CHUNK)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"file exceeds {max_bytes} bytes")
            out.write(chunk)
    if written <= 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="empty file")
    return written


def _doc_to_status(doc: Document) -> IngestStatusResponse:
    return IngestStatusResponse(
        document_id=doc.id,
        tenant_id=doc.tenant_id,
        filename=doc.filename,
        doc_type=doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type),
        status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/documents", response_model=DocumentListResponse, tags=["documents"])
def list_documents(
    status: IngestStatus | None = Query(default=None),
    doc_type: DocType | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    q = db.query(Document).filter(Document.tenant_id == tenant_id)
    if status is not None:
        q = q.filter(Document.status == status)
    if doc_type is not None:
        q = q.filter(Document.doc_type == doc_type)
    total = q.count()
    rows = q.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    items = [
        DocumentListItem(
            document_id=d.id,
            tenant_id=d.tenant_id,
            filename=d.filename,
            doc_type=d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type),
            status=d.status.value if hasattr(d.status, "value") else str(d.status),
            chunk_count=d.chunk_count,
            error_message=d.error_message,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in rows
    ]
    return DocumentListResponse(tenant_id=tenant_id, total=total, items=items)


@router.post("/ingest", response_model=IngestCreateResponse, tags=["ingest"])
async def create_ingest(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: DocType = Form(DocType.kb),
    sync: bool = Form(False),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    safe_name = Path(file.filename or "upload.bin").name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file type {suffix or '(none)'}; allowed: {sorted(ALLOWED_UPLOAD_SUFFIXES)}",
        )
    upload_root = _tenant_upload_dir(settings.upload_dir, tenant_id)
    doc_id = str(uuid.uuid4())
    dest = upload_root / f"{doc_id}_{safe_name}"
    _write_upload(file, dest, settings.max_upload_bytes)

    doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        filename=safe_name,
        doc_type=doc_type,
        storage_path=str(dest),
        status=IngestStatus.pending,
    )
    db.add(doc)
    db.commit()

    if sync:
        process_document(db, doc_id)
        doc = db.get(Document, doc_id)
        if doc is None or doc.status == IngestStatus.failed:
            raise HTTPException(
                status_code=422,
                detail=(doc.error_message if doc else None) or "ingest failed",
            )
        return IngestCreateResponse(
            document_id=doc_id,
            status=doc.status.value,
            message="sync ingest finished",
        )

    if settings.ingest_use_worker:
        try:
            enqueue_ingest({"document_id": doc_id, "tenant_id": tenant_id})
        except Exception as exc:
            raise HTTPException(status_code=503, detail="ingest queue unavailable") from exc
    else:
        background_tasks.add_task(_bg_process, doc_id)
    return IngestCreateResponse(document_id=doc_id, status="pending", message="ingest job queued")


def _bg_process(document_id: str) -> None:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        process_document(db, document_id)
    finally:
        db.close()


@router.get("/ingest/{document_id}", response_model=IngestStatusResponse, tags=["ingest"])
def get_ingest_status(
    document_id: str,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="document not found")
    return _doc_to_status(doc)


@router.post("/retrieve", response_model=RetrieveResponse, tags=["retrieve"])
def retrieve_endpoint(
    body: RetrieveRequest,
    tenant_id: str = Depends(require_tenant),
):
    hits = retrieve(query=body.query, tenant_id=tenant_id, top_k=body.top_k, doc_type=body.doc_type)
    return RetrieveResponse(
        tenant_id=tenant_id,
        query=body.query,
        hits=[RetrieveHit(**h) for h in hits],
    )
