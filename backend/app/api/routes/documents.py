import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentType,
    TopicResponse,
    TopicCreate,
)
from app.services.document_service import DocumentService
from app.services.s3_service import S3Service

router = APIRouter(prefix="/api/documents", tags=["Documents & Topics"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    year: Optional[int] = Query(None, description="Filter by past paper year"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    grade: Optional[int] = Query(None, description="Filter by grade (10, 11)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve all registered documents."""
    service = DocumentService(db)
    return service.list_documents(
        year=year,
        doc_type=doc_type,
        grade=grade,
        skip=skip,
        limit=limit,
    )

@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(...),
    grade: Optional[int] = Form(None),
    year: Optional[int] = Form(None),
    subject_id: Optional[uuid.UUID] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a PDF to S3 and register its metadata in PostgreSQL."""

    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    filename = Path(file.filename).name

    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    # Validate PDF content and file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 20 MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if file.file.read(5) != b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        )

    file.file.seek(0)

    service = DocumentService(db)

    # Prevent duplicate filenames
    existing = service.doc_repo.get_by_filename(filename)

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A document with this filename already exists.",
        )

    s3_service = S3Service()
    s3_key = None

    try:
        # Upload PDF to S3
        s3_key = s3_service.upload_file(
            file_obj=file.file,
            filename=filename,
            content_type="application/pdf",
        )

        # Save document metadata in PostgreSQL
        document = service.doc_repo.create(
            filename=filename,
            file_path=s3_key,
            year=year,
            subject_id=subject_id,
            doc_type=doc_type.value,
            grade=grade,
        )

        return DocumentResponse.model_validate(document)

    except Exception:
        db.rollback()

        # Remove S3 file if database registration fails
        if s3_key:
            try:
                s3_service.delete_file(s3_key)
            except Exception:
                pass

        raise HTTPException(
            status_code=500,
            detail="Failed to upload and register the document.",
        )

    finally:
        file.file.close()

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def register_document(doc_in: DocumentCreate, db: Session = Depends(get_db)):
    """Register document metadata in PostgreSQL."""
    service = DocumentService(db)
    return service.register_document(doc_in)

@router.get("/topics", response_model=List[TopicResponse])
def list_topics(
    subject_area: Optional[str] = Query(None, description="Filter by subject area"),
    grade: Optional[int] = Query(None, description="Filter by grade (10, 11)"),
    db: Session = Depends(get_db),
):
    service = DocumentService(db)
    return service.list_topics(subject_area=subject_area, grade=grade)

@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(topic_in: TopicCreate, db: Session = Depends(get_db)):
    service = DocumentService(db)
    topic = service.get_or_create_topic(
        name=topic_in.name,
        subject_area=topic_in.subject_area,
        grade=topic_in.grade,
        description=topic_in.description,
    )
    return TopicResponse.model_validate(topic)
