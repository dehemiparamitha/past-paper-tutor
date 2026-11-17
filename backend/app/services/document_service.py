import os
import uuid
import logging
import tempfile
from datetime import datetime
from typing import Optional, List, Dict, Any

import pymupdf
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument

from app.database.session import SessionLocal
from app.models.document import Document
from app.models.topic import Topic
from app.repositories.document_repository import DocumentRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    DocumentDownloadResponse,
    TopicResponse,
)
from app.services.s3_service import S3Service
from app.rag.vectorstore import get_vectorstore
from app.rag.loader import load_pdf
from app.rag.chunker import split_questions, chunks_to_langchain_documents
from app.rag.textbook_loader import chunk_textbook, textbook_chunks_to_documents

logger = logging.getLogger(__name__)


def process_document_background(document_id: uuid.UUID) -> None:
    """
    Background worker entry point. Creates a fresh database session
    and runs the document ingestion pipeline.
    """
    db = SessionLocal()
    try:
        service = DocumentService(db)
        service.process_document_pipeline(document_id)
    except Exception as e:
        logger.error("Unhandled error processing document %s in background: %s", document_id, e)
    finally:
        db.close()


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.topic_repo = TopicRepository(db)
        self.question_repo = QuestionRepository(db)
        self.s3_service = S3Service()

    def list_documents(
        self,
        search: Optional[str] = None,
        year: Optional[int] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        processing_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DocumentResponse]:
        docs = self.doc_repo.list_documents(
            search=search,
            year=year,
            doc_type=doc_type,
            grade=grade,
            processing_status=processing_status,
            skip=skip,
            limit=limit,
        )
        return [DocumentResponse.model_validate(d) for d in docs]

    def list_documents_paginated(
        self,
        search: Optional[str] = None,
        year: Optional[int] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        processing_status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> DocumentListResponse:
        skip = (page - 1) * limit
        items = self.doc_repo.list_documents(
            search=search,
            year=year,
            doc_type=doc_type,
            grade=grade,
            processing_status=processing_status,
            skip=skip,
            limit=limit,
        )
        total = self.doc_repo.count_documents(
            search=search,
            year=year,
            doc_type=doc_type,
            grade=grade,
            processing_status=processing_status,
        )
        return DocumentListResponse(
            total=total,
            items=[DocumentResponse.model_validate(d) for d in items],
            page=page,
            limit=limit,
        )

    def get_document(self, document_id: uuid.UUID) -> Optional[DocumentResponse]:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            return None
        return DocumentResponse.model_validate(doc)

    def register_document(self, doc_in: DocumentCreate) -> DocumentResponse:
        existing = self.doc_repo.get_by_filename(doc_in.filename)
        if existing:
            return DocumentResponse.model_validate(existing)

        doc = self.doc_repo.create(
            filename=doc_in.filename,
            file_path=doc_in.file_path,
            year=doc_in.year,
            subject_id=doc_in.subject_id,
            doc_type=doc_in.doc_type,
            grade=doc_in.grade,
            total_pages=doc_in.total_pages,
            processing_status="UPLOADED",
        )
        return DocumentResponse.model_validate(doc)

    def generate_download_url(
        self,
        document_id: uuid.UUID,
        expires_in: int = 3600,
    ) -> DocumentDownloadResponse:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise ValueError("Document not found.")
        if not doc.file_path:
            raise ValueError("Document does not have a valid storage key.")

        url = self.s3_service.generate_download_url(doc.file_path, expires_in=expires_in)
        return DocumentDownloadResponse(
            download_url=url,
            filename=doc.filename,
            expires_in=expires_in,
        )

    def _delete_vectors_for_document(self, document_id: uuid.UUID, filename: str) -> None:
        """Remove all ChromaDB vectors associated with a document. Errors are logged but not re-raised."""
        try:
            vectorstore = get_vectorstore()
            vectorstore._collection.delete(where={"document_id": str(document_id)})
            logger.info("Deleted ChromaDB vectors for document %s", document_id)
        except Exception as e:
            logger.warning("Could not delete vectors from ChromaDB for %s: %s", document_id, e)

        # Also fallback clean-up by source filename
        try:
            vectorstore = get_vectorstore()
            vectorstore._collection.delete(where={"source": filename})
        except Exception:
            pass

    def delete_document(self, document_id: uuid.UUID) -> bool:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            return False

        # 1. Delete associated vectors from ChromaDB
        self._delete_vectors_for_document(document_id, doc.filename)

        # 2. Delete file from S3
        if doc.file_path:
            try:
                self.s3_service.delete_file(doc.file_path)
                logger.info("Deleted S3 object %s for document %s", doc.file_path, document_id)
            except Exception as e:
                logger.error("Failed to delete S3 file %s for document %s: %s", doc.file_path, document_id, e)

        # 3. Delete document record in PostgreSQL (cascades to related questions)
        return self.doc_repo.delete(document_id)

    def process_document_pipeline(self, document_id: uuid.UUID) -> None:
        """
        Executes the complete document ingestion pipeline:
        1. Downloads the PDF from S3 to a temporary file.
        2. Extracts text using PyMuPDF / existing loaders.
        3. Chunks text based on doc_type (past_paper, textbook, marking_scheme).
        4. Enriches chunk metadata with document_id, filename, grade, year.
        5. Generates embeddings and stores in ChromaDB.
        6. Updates PostgreSQL document status to COMPLETED (or FAILED on error).
        7. Cleans up the temporary local file.
        """
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            logger.error("Cannot process document %s: not found in database", document_id)
            return

        if not doc.file_path:
            error_msg = "Document has no file_path stored for S3 retrieval."
            self.doc_repo.update_status(document_id, status="FAILED", error=error_msg)
            return

        # Mark status as PROCESSING
        self.doc_repo.update_status(document_id, status="PROCESSING", error=None)
        logger.info("Starting processing for document %s (%s)", document_id, doc.filename)

        temp_dir = tempfile.mkdtemp(prefix="paperwise_ingest_")
        temp_file_path = os.path.join(temp_dir, f"{doc.id}_{doc.filename}")

        try:
            # 1. Download file from S3 to temp location
            self.s3_service.download_file(doc.file_path, temp_file_path)

            # 2. Inspect PDF using PyMuPDF for page count
            pdf_doc = pymupdf.open(temp_file_path)
            total_pages = len(pdf_doc)
            pdf_doc.close()

            # 3. Purge existing vectors for this document_id if previously ingested
            try:
                vectorstore = get_vectorstore()
                vectorstore._collection.delete(where={"document_id": str(doc.id)})
            except Exception:
                pass

            vectorstore = get_vectorstore()
            total_chunks_added = 0

            # 4. Processing based on doc_type
            if doc.doc_type == "past_paper":
                text = load_pdf(temp_file_path)
                if not text.strip():
                    raise ValueError(f"No text could be extracted from PDF {doc.filename}")

                chunks = split_questions(text, paper_year=doc.year, file_path=temp_file_path)
                if not chunks:
                    raise ValueError(f"No questions could be parsed from past paper {doc.filename}")

                # Enrich metadata on all chunks
                for c in chunks:
                    c["metadata"]["doc_type"] = "past_paper"
                    c["metadata"]["document_id"] = str(doc.id)
                    c["metadata"]["filename"] = doc.filename
                    if doc.grade is not None:
                        c["metadata"]["grade"] = doc.grade
                    if doc.year is not None:
                        c["metadata"]["year"] = doc.year
                        c["metadata"]["paper_year"] = doc.year

                # Attempt automatic topic classification if LLM is accessible
                try:
                    from app.rag.topic_extractor import enrich_chunks_with_topics
                    chunks = enrich_chunks_with_topics(chunks)
                except Exception as ex:
                    logger.warning("Topic enrichment skipped for %s: %s", doc.filename, ex)

                docs = chunks_to_langchain_documents(chunks)
                doc_ids = [
                    f"paper_{doc.id}_q{c.get('question_number', idx)}_{c.get('question_type', 'item')}"
                    for idx, c in enumerate(chunks)
                ]
                vectorstore.add_documents(docs, ids=doc_ids)
                total_chunks_added = len(docs)

            elif doc.doc_type == "textbook":
                chunks = chunk_textbook(temp_file_path)
                if not chunks:
                    raise ValueError(f"No text chunks could be generated from textbook {doc.filename}")

                for c in chunks:
                    c["metadata"]["doc_type"] = "textbook"
                    c["metadata"]["document_id"] = str(doc.id)
                    c["metadata"]["filename"] = doc.filename
                    if doc.grade is not None:
                        c["metadata"]["grade"] = doc.grade
                    c["metadata"]["source"] = doc.filename

                docs = textbook_chunks_to_documents(chunks)
                doc_ids = [f"textbook_{doc.id}_c{idx}" for idx in range(len(chunks))]
                vectorstore.add_documents(docs, ids=doc_ids)
                total_chunks_added = len(docs)

            elif doc.doc_type == "marking_scheme":
                # Extract text page by page with PyMuPDF
                doc_pdf = pymupdf.open(temp_file_path)
                extracted_pages = []
                for p_idx, page in enumerate(doc_pdf, start=1):
                    p_text = page.get_text().strip()
                    if p_text:
                        extracted_pages.append((p_idx, p_text))
                doc_pdf.close()

                if not extracted_pages:
                    raise ValueError(f"No text could be extracted from marking scheme {doc.filename}")

                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=150,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )

                lc_docs = []
                doc_ids = []
                c_idx = 0
                for p_num, p_text in extracted_pages:
                    splits = splitter.split_text(p_text)
                    for split in splits:
                        c_idx += 1
                        lc_docs.append(LCDocument(
                            page_content=split,
                            metadata={
                                "doc_type": "marking_scheme",
                                "document_id": str(doc.id),
                                "filename": doc.filename,
                                "year": doc.year,
                                "grade": doc.grade,
                                "page_number": p_num,
                                "source": doc.filename,
                            }
                        ))
                        doc_ids.append(f"ms_{doc.id}_c{c_idx}")

                vectorstore.add_documents(lc_docs, ids=doc_ids)
                total_chunks_added = len(lc_docs)

            else:
                raise ValueError(f"Unsupported document type: {doc.doc_type}")

            # 5. Success: update document in database
            self.doc_repo.update_status(
                document_id=doc.id,
                status="COMPLETED",
                error=None,
                total_pages=total_pages,
                processed_at=datetime.utcnow(),
            )
            logger.info(
                "Document %s (%s) processed successfully: %d pages, %d chunks added to ChromaDB",
                doc.id, doc.filename, total_pages, total_chunks_added,
            )

        except Exception as e:
            error_message = str(e)
            logger.error("Processing failed for document %s: %s", document_id, error_message, exc_info=True)
            # Update status to FAILED in DB (original PDF remains safely in S3)
            self.doc_repo.update_status(
                document_id=document_id,
                status="FAILED",
                error=error_message[:1000],  # store up to 1000 chars of error
            )

        finally:
            # 6. Cleanup temporary file and directory
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as clean_err:
                logger.warning("Error cleaning temporary ingestion files: %s", clean_err)

    def list_topics(
        self,
        subject_area: Optional[str] = None,
        grade: Optional[int] = None,
    ) -> List[TopicResponse]:
        topics = self.topic_repo.list_topics(subject_area=subject_area, grade=grade)
        return [TopicResponse.model_validate(t) for t in topics]

    def get_or_create_topic(
        self,
        name: str,
        subject_area: str = "general",
        grade: int = 10,
        description: Optional[str] = None,
    ) -> Topic:
        return self.topic_repo.get_or_create(
            name=name,
            subject_area=subject_area,
            grade=grade,
            description=description,
        )
