from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_tenant
from app.api.schemas import (
    DocumentListItem,
    DocumentListResponse,
    HealthResponse,
    IngestCreateResponse,
    IngestStatusResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.models.entities import DocType, Document, IngestStatus
from app.services.ingest import process_document
from app.services.redis_queue import enqueue_ingest
from app.services.retrieve import retrieve

router = APIRouter()


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


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health():
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, env=settings.app_env)


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
    upload_root = Path(settings.upload_dir) / tenant_id
    upload_root.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    safe_name = Path(file.filename or "upload.bin").name
    dest = upload_root / f"{doc_id}_{safe_name}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

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
        return IngestCreateResponse(document_id=doc_id, status="processing_done", message="sync ingest finished")

    enqueue_ingest({"document_id": doc_id, "tenant_id": tenant_id})
    background_tasks.add_task(_bg_process, doc_id)
    return IngestCreateResponse(document_id=doc_id, status="pending", message="ingest job queued")


def _bg_process(document_id: str) -> None:
    from app.core.db import SessionLocal

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
