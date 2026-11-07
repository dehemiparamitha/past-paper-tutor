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
    BackgroundTasks,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    DocumentDownloadResponse,
    DocumentType,
    TopicResponse,
    TopicCreate,
)
from app.services.document_service import (
    DocumentService,
    process_document_background,
)
from app.services.s3_service import S3Service, sanitize_filename

router = APIRouter(prefix="/api/documents", tags=["Documents & Topics"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# --- Topics Endpoints (must be declared BEFORE /{document_id} to avoid route shadowing) ---

@router.get("/topics", response_model=List[TopicResponse])
def list_topics(
    subject_area: Optional[str] = Query(None, description="Filter by subject area"),
    grade: Optional[int] = Query(None, description="Filter by grade (10, 11)"),
    db: Session = Depends(get_db),
):
    service = DocumentService(db)
    return service.list_topics(subject_area=subject_area, grade=grade)


@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_in: TopicCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    service = DocumentService(db)
    topic = service.get_or_create_topic(
        name=topic_in.name,
        subject_area=topic_in.subject_area,
        grade=topic_in.grade,
        description=topic_in.description,
    )
    return TopicResponse.model_validate(topic)


# ---------------------------------------------------------------------------

@router.get("", response_model=DocumentListResponse)
def list_documents(
    search: Optional[str] = Query(None, description="Search by filename"),
    year: Optional[int] = Query(None, description="Filter by past paper year"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    grade: Optional[int] = Query(None, description="Filter by grade (10, 11)"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve registered documents with filtering, search, and pagination. Admin only."""
    service = DocumentService(db)
    return service.list_documents_paginated(
        search=search,
        year=year,
        doc_type=doc_type,
        grade=grade,
        processing_status=processing_status,
        page=page,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve metadata for a specific document by its ID. Admin only."""
    service = DocumentService(db)
    doc = service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return doc


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(...),
    grade: Optional[int] = Form(None),
    year: Optional[int] = Form(None),
    subject_id: Optional[uuid.UUID] = Form(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF to Amazon S3, register metadata in PostgreSQL,
    and trigger the RAG document processing pipeline in the background. Admin only.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    # 1. Validate file extension
    raw_filename = Path(file.filename).name
    if Path(raw_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # 2. Sanitize filename
    sanitized_name = sanitize_filename(raw_filename)

    # 3. Validate file size and signature
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    header = file.file.read(5)
    file.file.seek(0)
    if header != b"%PDF-":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file format. The file header does not match a valid PDF.",
        )

    service = DocumentService(db)

    # 4. Check for duplicate filename
    existing = service.doc_repo.get_by_filename(sanitized_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A document with filename '{sanitized_name}' already exists.",
        )

    s3_service = S3Service()
    s3_key = None

    # Normalize Form defaults if called directly in unit tests
    clean_grade = None if hasattr(grade, "default") else grade
    clean_year = None if hasattr(year, "default") else year
    clean_subject_id = None if hasattr(subject_id, "default") else subject_id

    try:
        # 5. Upload original PDF to private S3 bucket
        s3_key = s3_service.upload_file(
            file_obj=file.file,
            filename=sanitized_name,
            content_type="application/pdf",
        )

        # 6. Save document metadata in PostgreSQL with status 'UPLOADED'
        document = service.doc_repo.create(
            filename=sanitized_name,
            file_path=s3_key,
            year=clean_year,
            subject_id=clean_subject_id,
            doc_type=doc_type.value if hasattr(doc_type, "value") else str(doc_type),
            grade=clean_grade,
            processing_status="UPLOADED",
        )

        # 7. Queue background processing for PyMuPDF text extraction & ChromaDB embeddings
        background_tasks.add_task(process_document_background, document.id)

        return DocumentResponse.model_validate(document)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Clean up S3 object if database registration failed
        if s3_key:
            try:
                s3_service.delete_file(s3_key)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload and register the document: {str(e)}",
        )
    finally:
        file.file.close()


@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
def download_document(
    document_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Generate a temporary presigned download URL for an original PDF stored in private S3.
    Admin only.
    """
    service = DocumentService(db)
    try:
        return service.generate_download_url(document_id, expires_in=3600)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}",
        )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a document:
    1. Removes all associated vector embeddings from ChromaDB.
    2. Deletes the original PDF object from private S3.
    3. Deletes document record from PostgreSQL (cascading related child rows).
    Admin only.
    """
    service = DocumentService(db)
    success = service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return {"success": True, "message": "Document and associated vectors deleted successfully."}


@router.post("/{document_id}/process", response_model=DocumentResponse)
def retry_document_processing(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Retry or re-trigger processing of an uploaded document.
    Admin only.
    """
    service = DocumentService(db)
    doc = service.doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.processing_status == "PROCESSING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is currently being processed.",
        )

    # Reset status to UPLOADED and schedule background processing
    updated_doc = service.doc_repo.update_status(
        document_id=document_id,
        status="UPLOADED",
        error=None,
    )
    background_tasks.add_task(process_document_background, document_id)
    return DocumentResponse.model_validate(updated_doc)

