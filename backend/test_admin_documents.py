import io
import sys
import os
import uuid
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Block HuggingFace / sentence-transformers from initialising and hitting the
# network.  These mocks must be installed in sys.modules BEFORE any app module
# is imported, otherwise importing `langchain_huggingface` will start loading
# model weights from the HuggingFace Hub and hang in environments without
# network access.
# ---------------------------------------------------------------------------
_mock_st = MagicMock()
_mock_lhf = MagicMock()

# sentence_transformers package tree
sys.modules["sentence_transformers"] = _mock_st
sys.modules["sentence_transformers.SentenceTransformer"] = _mock_st

# langchain_huggingface — the main import used in app/rag/embeddings.py
_fake_hf_embeddings = MagicMock()
_fake_hf_embeddings.embed_documents = lambda texts: [[0.0] * 384 for _ in texts]
_fake_hf_embeddings.embed_query = lambda text: [0.0] * 384
_mock_lhf.HuggingFaceEmbeddings = MagicMock(return_value=_fake_hf_embeddings)
sys.modules["langchain_huggingface"] = _mock_lhf
sys.modules["langchain_huggingface.embeddings"] = _mock_lhf
sys.modules["langchain_huggingface.embeddings.huggingface"] = _mock_lhf

# chromadb / langchain_chroma — block these so the vectorstore doesn't attempt
# to open a real Chroma database or connect to anything during test import.
_mock_chromadb = MagicMock()
_mock_lc_chroma = MagicMock()
_mock_chroma_cls = MagicMock()
_mock_chroma_cls.return_value = MagicMock()
_mock_lc_chroma.Chroma = _mock_chroma_cls
sys.modules["chromadb"] = _mock_chromadb
sys.modules["chromadb.config"] = _mock_chromadb
sys.modules["chromadb.api"] = _mock_chromadb
sys.modules["chromadb.db"] = _mock_chromadb
sys.modules["langchain_chroma"] = _mock_lc_chroma

# langchain_google_genai — topic_extractor.py creates a ChatGoogleGenerativeAI
# instance at module level, which requires a network call for auth.
_mock_lg = MagicMock()
_mock_lg.ChatGoogleGenerativeAI = MagicMock(return_value=MagicMock())
sys.modules["langchain_google_genai"] = _mock_lg

# Globally mock vectorstore and embeddings so tests never require downloading sentence-transformer weights
mock_vectorstore = MagicMock()
mock_chroma_collection = MagicMock()
mock_vectorstore._collection = mock_chroma_collection
mock_vectorstore.add_documents = MagicMock()

patch("app.rag.embeddings.get_embeddings", return_value=MagicMock()).start()
patch("app.rag.vectorstore.get_vectorstore", return_value=mock_vectorstore).start()
patch("app.services.document_service.get_vectorstore", return_value=mock_vectorstore).start()
patch("app.rag.topic_extractor.enrich_chunks_with_topics", side_effect=lambda chunks: chunks).start()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, Depends, HTTPException, UploadFile, BackgroundTasks

from app.models.document import Document
from app.models.user import User
from app.database.session import get_db
from app.api.deps import get_current_admin, get_current_user
from app.services.s3_service import S3Service, sanitize_filename
from app.services.document_service import DocumentService
from app.api.routes.documents import (
    router as documents_router,
    upload_document,
    list_documents,
    get_document,
    download_document,
    delete_document,
    retry_document_processing,
)
from app.schemas.document import DocumentType

# Directly override vectorstore on document_service module
import app.services.document_service
app.services.document_service.get_vectorstore = lambda: mock_vectorstore


# In-memory SQLite database setup for test suite
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

# Create only Document and User tables for unit testing
Document.__table__.create(engine)
User.__table__.create(engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create fake admin user
admin_user = User(
    id=uuid.uuid4(),
    email="admin@paperwise.lk",
    hashed_password="mocked_password",
    full_name="Paperwise Admin",
    is_admin=True,
    is_active=True,
)

# Create fake non-admin user
regular_user = User(
    id=uuid.uuid4(),
    email="student@paperwise.lk",
    hashed_password="mocked_password",
    full_name="O/L Student",
    is_admin=False,
    is_active=True,
)


class TestS3Service(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("2023 Science Paper.pdf"), "2023_Science_Paper.pdf")
        self.assertEqual(sanitize_filename("../../etc/passwd.pdf"), "passwd.pdf")
        self.assertEqual(sanitize_filename("valid-name_12.pdf"), "valid-name_12.pdf")
        self.assertEqual(sanitize_filename("..."), "document.pdf")

    def test_s3_upload_file(self):
        s3 = S3Service(bucket_name="test-bucket", region_name="ap-southeast-2", prefix="documents/")
        mock_s3 = MagicMock()
        s3.s3_client = mock_s3

        stream = io.BytesIO(b"%PDF-1.4 test content")
        key = s3.upload_file(stream, "science_2023.pdf")

        self.assertTrue(key.startswith("documents/"))
        self.assertTrue(key.endswith("science_2023.pdf"))
        mock_s3.upload_fileobj.assert_called_once()

    def test_s3_delete_file(self):
        s3 = S3Service(bucket_name="test-bucket")
        mock_s3 = MagicMock()
        s3.s3_client = mock_s3

        result = s3.delete_file("documents/test.pdf")
        self.assertTrue(result)
        mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="documents/test.pdf")

    def test_s3_generate_download_url(self):
        s3 = S3Service(bucket_name="test-bucket")
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/doc.pdf?signature=xyz"
        s3.s3_client = mock_s3

        url = s3.generate_download_url("documents/doc.pdf", expires_in=1800)
        self.assertIn("https://s3.amazonaws.com", url)
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "documents/doc.pdf"},
            ExpiresIn=1800,
        )


class TestDocumentAPIEndpoints(unittest.TestCase):
    def setUp(self):
        # Clear database between tests
        self.db = TestingSessionLocal()
        self.db.query(Document).delete()
        self.db.commit()
        mock_chroma_collection.reset_mock()

    def tearDown(self):
        self.db.close()

    def test_unauthorized_access(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(authorization=None, db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Authentication required", ctx.exception.detail)

    def test_forbidden_non_admin_access(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_admin(current_user=regular_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access restricted to administrators only", ctx.exception.detail)

    @patch("app.api.routes.documents.process_document_background")
    @patch.object(S3Service, "upload_file")
    def test_valid_pdf_upload(self, mock_upload, mock_bg_task):
        mock_upload.return_value = "documents/test_uuid_science_2024.pdf"
        bg_tasks = BackgroundTasks()

        pdf_bytes = b"%PDF-1.5 Sample past paper binary text content"
        upload_file = UploadFile(file=io.BytesIO(pdf_bytes), filename="science_2024.pdf")

        res = upload_document(
            background_tasks=bg_tasks,
            file=upload_file,
            doc_type=DocumentType.PAST_PAPER,
            grade=11,
            year=2024,
            subject_id=None,
            current_admin=admin_user,
            db=self.db,
        )
        self.assertEqual(res.filename, "science_2024.pdf")
        self.assertEqual(res.doc_type, "past_paper")
        self.assertEqual(res.grade, 11)
        self.assertEqual(res.year, 2024)
        self.assertEqual(res.processing_status, "UPLOADED")
        self.assertEqual(res.file_path, "documents/test_uuid_science_2024.pdf")
        self.assertEqual(len(bg_tasks.tasks), 1)

    def test_invalid_file_extension(self):
        bg_tasks = BackgroundTasks()
        upload_file = UploadFile(file=io.BytesIO(b"%PDF- dummy"), filename="notes.docx")

        with self.assertRaises(HTTPException) as ctx:
            upload_document(
                background_tasks=bg_tasks,
                file=upload_file,
                doc_type=DocumentType.PAST_PAPER,
                current_admin=admin_user,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Only PDF files are allowed", ctx.exception.detail)

    def test_invalid_pdf_signature(self):
        bg_tasks = BackgroundTasks()
        upload_file = UploadFile(file=io.BytesIO(b"This is not a real PDF file header"), filename="fake.pdf")

        with self.assertRaises(HTTPException) as ctx:
            upload_document(
                background_tasks=bg_tasks,
                file=upload_file,
                doc_type=DocumentType.PAST_PAPER,
                current_admin=admin_user,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("The file header does not match a valid PDF", ctx.exception.detail)

    def test_empty_file_upload(self):
        bg_tasks = BackgroundTasks()
        upload_file = UploadFile(file=io.BytesIO(b""), filename="empty.pdf")

        with self.assertRaises(HTTPException) as ctx:
            upload_document(
                background_tasks=bg_tasks,
                file=upload_file,
                doc_type=DocumentType.PAST_PAPER,
                current_admin=admin_user,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("The uploaded file is empty", ctx.exception.detail)

    @patch("app.api.routes.documents.process_document_background")
    @patch.object(S3Service, "upload_file")
    def test_duplicate_filename_rejection(self, mock_upload, mock_bg_task):
        mock_upload.return_value = "documents/dup.pdf"
        pdf_bytes = b"%PDF-1.4 file data"

        # First upload succeeds
        bg_tasks1 = BackgroundTasks()
        upload_file1 = UploadFile(file=io.BytesIO(pdf_bytes), filename="duplicate_test.pdf")
        res1 = upload_document(
            background_tasks=bg_tasks1,
            file=upload_file1,
            doc_type=DocumentType.PAST_PAPER,
            grade=10,
            current_admin=admin_user,
            db=self.db,
        )
        self.assertEqual(res1.filename, "duplicate_test.pdf")

        # Second upload with same filename should raise 409 Conflict
        bg_tasks2 = BackgroundTasks()
        upload_file2 = UploadFile(file=io.BytesIO(pdf_bytes), filename="duplicate_test.pdf")
        with self.assertRaises(HTTPException) as ctx:
            upload_document(
                background_tasks=bg_tasks2,
                file=upload_file2,
                doc_type=DocumentType.PAST_PAPER,
                grade=10,
                current_admin=admin_user,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("already exists", ctx.exception.detail)

    def test_list_and_filter_documents(self):
        doc1 = Document(
            filename="2021_science.pdf",
            file_path="documents/2021.pdf",
            doc_type="past_paper",
            grade=11,
            year=2021,
            processing_status="COMPLETED",
        )
        doc2 = Document(
            filename="grade10_textbook.pdf",
            file_path="documents/book.pdf",
            doc_type="textbook",
            grade=10,
            year=2020,
            processing_status="COMPLETED",
        )
        self.db.add_all([doc1, doc2])
        self.db.commit()

        # List all
        res = list_documents(
            search=None,
            year=None,
            doc_type=None,
            grade=None,
            processing_status=None,
            page=1,
            limit=50,
            current_admin=admin_user,
            db=self.db,
        )
        self.assertEqual(res.total, 2)

        # Filter by doc_type=textbook
        res_filter = list_documents(
            search=None,
            year=None,
            doc_type="textbook",
            grade=None,
            processing_status=None,
            page=1,
            limit=50,
            current_admin=admin_user,
            db=self.db,
        )
        self.assertEqual(res_filter.total, 1)
        self.assertEqual(res_filter.items[0].filename, "grade10_textbook.pdf")

        # Filter by search=2021
        res_search = list_documents(
            search="2021",
            year=None,
            doc_type=None,
            grade=None,
            processing_status=None,
            page=1,
            limit=50,
            current_admin=admin_user,
            db=self.db,
        )
        self.assertEqual(res_search.total, 1)
        self.assertEqual(res_search.items[0].filename, "2021_science.pdf")

    @patch.object(S3Service, "generate_download_url")
    def test_document_download_url(self, mock_gen_url):
        mock_gen_url.return_value = "https://s3.amazonaws.com/paperwise-documents/presigned-url"

        doc = Document(
            filename="download_test.pdf",
            file_path="documents/download_test.pdf",
            doc_type="past_paper",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        res = download_document(document_id=doc.id, current_admin=admin_user, db=self.db)
        self.assertEqual(res.download_url, "https://s3.amazonaws.com/paperwise-documents/presigned-url")
        self.assertEqual(res.filename, "download_test.pdf")

    @patch.object(S3Service, "delete_file")
    @patch("app.services.document_service.DocumentService._delete_vectors_for_document")
    def test_document_deletion(self, mock_delete_vectors, mock_delete_s3):
        mock_delete_s3.return_value = True
        mock_delete_vectors.return_value = None

        doc = Document(
            filename="delete_me.pdf",
            file_path="documents/delete_me.pdf",
            doc_type="past_paper",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        doc_id = doc.id

        res = delete_document(document_id=doc_id, current_admin=admin_user, db=self.db)
        self.assertTrue(res["success"])

        # Verify S3 deletion and ChromaDB vector cleanup were called
        mock_delete_s3.assert_called_once_with("documents/delete_me.pdf")
        mock_delete_vectors.assert_called_once()

        # Verify deletion from DB
        deleted_doc = self.db.query(Document).filter_by(id=doc_id).first()
        self.assertIsNone(deleted_doc)

    def test_retry_processing_endpoint(self):
        doc = Document(
            filename="failed_doc.pdf",
            file_path="documents/failed_doc.pdf",
            doc_type="past_paper",
            processing_status="FAILED",
            processing_error="Simulated network error",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        bg_tasks = BackgroundTasks()
        with patch("app.api.routes.documents.process_document_background"):
            res = retry_document_processing(
                document_id=doc.id,
                background_tasks=bg_tasks,
                current_admin=admin_user,
                db=self.db,
            )
            self.assertEqual(res.processing_status, "UPLOADED")
            self.assertEqual(len(bg_tasks.tasks), 1)


class TestDocumentProcessingPipeline(unittest.TestCase):
    @patch.object(S3Service, "download_file")
    @patch("pymupdf.open")
    def test_processing_failure_updates_db_status(self, mock_pymupdf, mock_download):
        # Simulate PDF corrupt or missing
        mock_pymupdf.side_effect = Exception("Corrupt PDF stream")
        mock_download.return_value = None

        db = TestingSessionLocal()
        doc = Document(
            filename="corrupt.pdf",
            file_path="documents/corrupt.pdf",
            doc_type="past_paper",
            processing_status="UPLOADED",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id

        service = DocumentService(db)
        service.process_document_pipeline(doc_id)

        # Refresh document and check status
        db.refresh(doc)
        self.assertEqual(doc.processing_status, "FAILED")
        self.assertIn("Corrupt PDF stream", doc.processing_error)
        db.close()

    @patch.object(S3Service, "download_file")
    @patch("app.services.document_service.load_pdf")
    @patch("app.services.document_service.split_questions")
    @patch("pymupdf.open")
    def test_successful_past_paper_processing(self, mock_pymupdf, mock_split, mock_load, mock_download):
        mock_pdf_doc = MagicMock()
        mock_pdf_doc.__len__.return_value = 5
        mock_pymupdf.return_value = mock_pdf_doc
        mock_load.return_value = "Page 1 Content\n1. Question 1"
        mock_split.return_value = [
            {
                "question_number": 1,
                "question_type": "mcq",
                "full_text": "1. What is the unit of force?",
                "metadata": {"question_number": 1, "question_type": "mcq"},
            }
        ]

        db = TestingSessionLocal()
        doc = Document(
            filename="science_2023.pdf",
            file_path="documents/science_2023.pdf",
            doc_type="past_paper",
            grade=11,
            year=2023,
            processing_status="UPLOADED",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id

        service = DocumentService(db)
        service.process_document_pipeline(doc_id)

        db.refresh(doc)
        self.assertEqual(doc.processing_status, "COMPLETED")
        self.assertEqual(doc.total_pages, 5)
        self.assertIsNone(doc.processing_error)
        self.assertIsNotNone(doc.processed_at)

        # Verify ChromaDB add_documents was called
        mock_vectorstore.add_documents.assert_called()
        call_args = mock_vectorstore.add_documents.call_args
        added_docs, added_ids = call_args[0][0], call_args[1]["ids"]
        self.assertEqual(len(added_docs), 1)
        self.assertEqual(added_docs[0].metadata["document_id"], str(doc.id))
        self.assertEqual(added_docs[0].metadata["filename"], "science_2023.pdf")
        self.assertEqual(added_docs[0].metadata["grade"], 11)
        self.assertEqual(added_docs[0].metadata["year"], 2023)
        self.assertTrue(added_ids[0].startswith(f"paper_{doc.id}"))
        db.close()


if __name__ == "__main__":
    unittest.main()
