import React, { useState, useEffect, useRef, useCallback } from 'react'
import type { DocumentItem, DocumentType } from '../types/api'
import {
  fetchDocuments,
  uploadDocument,
  downloadDocument,
  deleteDocument,
  retryDocumentProcessing,
} from '../services/api'
import './AdminDocuments.css'

const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}

export function AdminDocuments() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState<string>('')
  const [docTypeFilter, setDocTypeFilter] = useState<string>('all')
  const [gradeFilter, setGradeFilter] = useState<string>('all')
  const [yearFilter, setYearFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState<number>(1)
  const pageSize = 20

  // Upload Modal State
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadDocType, setUploadDocType] = useState<DocumentType>('past_paper')
  const [uploadGrade, setUploadGrade] = useState<string>('11')
  const [uploadYear, setUploadYear] = useState<string>(new Date().getFullYear().toString())
  const [isUploading, setIsUploading] = useState<boolean>(false)
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState<boolean>(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Delete Confirmation State
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null)
  const [isDeleting, setIsDeleting] = useState<boolean>(false)

  // Action status state
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetchDocuments({
        search: search.trim() || undefined,
        doc_type: docTypeFilter !== 'all' ? docTypeFilter : undefined,
        grade: gradeFilter !== 'all' ? parseInt(gradeFilter, 10) : undefined,
        year: yearFilter !== 'all' ? parseInt(yearFilter, 10) : undefined,
        processing_status: statusFilter !== 'all' ? statusFilter : undefined,
        page: currentPage,
        limit: pageSize,
      })
      setDocuments(res.items)
      setTotalCount(res.total)
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch document registry from backend.')
    } finally {
      setIsLoading(false)
    }
  }, [search, docTypeFilter, gradeFilter, yearFilter, statusFilter, currentPage])

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadDocuments()
    }, 250)
    return () => clearTimeout(timer)
  }, [loadDocuments])

  // Periodic poll if any documents are currently in PROCESSING status
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.processing_status === 'PROCESSING' || d.processing_status === 'UPLOADED')
    if (!hasProcessing) return

    const interval = setInterval(() => {
      void loadDocuments()
    }, 4000)

    return () => clearInterval(interval)
  }, [documents, loadDocuments])

  // Stats calculation
  const completedCount = documents.filter((d) => d.processing_status === 'COMPLETED').length
  const processingCount = documents.filter((d) => d.processing_status === 'PROCESSING' || d.processing_status === 'UPLOADED').length
  const failedCount = documents.filter((d) => d.processing_status === 'FAILED').length

  const handleDownload = async (doc: DocumentItem) => {
    setActionInProgressId(doc.id)
    try {
      const res = await downloadDocument(doc.id)
      window.open(res.download_url, '_blank', 'noopener,noreferrer')
    } catch (err: any) {
      alert(`Download failed: ${err?.message || 'Could not generate download URL.'}`)
    } finally {
      setActionInProgressId(null)
    }
  }

  const handleRetry = async (doc: DocumentItem) => {
    setActionInProgressId(doc.id)
    try {
      await retryDocumentProcessing(doc.id)
      setSuccessMessage(`Processing re-triggered for "${doc.filename}".`)
      await loadDocuments()
    } catch (err: any) {
      alert(`Retry failed: ${err?.message || 'Unable to re-trigger document processing.'}`)
    } finally {
      setActionInProgressId(null)
    }
  }

  const confirmDelete = async () => {
    if (!docToDelete) return
    setIsDeleting(true)
    try {
      await deleteDocument(docToDelete.id)
      setSuccessMessage(`Document "${docToDelete.filename}" and its vector embeddings were removed.`)
      setDocToDelete(null)
      await loadDocuments()
    } catch (err: any) {
      alert(`Delete failed: ${err?.message || 'Failed to delete document.'}`)
    } finally {
      setIsDeleting(false)
    }
  }

  // Upload handlers
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelectFile(e.dataTransfer.files[0])
    }
  }

  const validateAndSelectFile = (file: File) => {
    setUploadError(null)
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only PDF documents are supported.')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      setUploadError(`File exceeds maximum allowed size of 20 MB (${formatFileSize(file.size)}).`)
      return
    }
    if (file.size === 0) {
      setUploadError('The selected file is empty.')
      return
    }
    setSelectedFile(file)
  }

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setUploadError('Please select a PDF file to upload.')
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setUploadError(null)

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('doc_type', uploadDocType)
    if (uploadGrade) formData.append('grade', uploadGrade)
    if (uploadYear) formData.append('year', uploadYear)

    try {
      await uploadDocument(formData, (percent) => {
        setUploadProgress(percent)
      })
      setSuccessMessage(`"${selectedFile.name}" successfully uploaded to S3. Ingestion pipeline scheduled.`)
      setIsUploadOpen(false)
      setSelectedFile(null)
      setUploadProgress(0)
      await loadDocuments()
    } catch (err: any) {
      setUploadError(err?.message || 'Upload failed. Please check your network and permissions.')
    } finally {
      setIsUploading(false)
    }
  }

  const resetFilters = () => {
    setSearch('')
    setDocTypeFilter('all')
    setGradeFilter('all')
    setYearFilter('all')
    setStatusFilter('all')
    setCurrentPage(1)
  }

  const totalPages = Math.ceil(totalCount / pageSize) || 1

  return (
    <div className="admin-docs-container">
      {/* Header */}
      <div className="admin-docs-header">
        <div className="admin-header-titles">
          <h1>
            Document Management
            <span className="admin-badge">Admin Workspace</span>
          </h1>
          <p>
            Upload official GCE O/L Science past papers, textbooks, and marking schemes.
            Original PDFs are stored in Amazon S3 and automatically indexed into the Paperwise RAG semantic vectorstore.
          </p>
        </div>
        <div className="admin-header-actions">
          <button
            type="button"
            className="admin-btn admin-btn-secondary"
            onClick={() => void loadDocuments()}
            disabled={isLoading}
            title="Refresh document list"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Refresh
          </button>
          <button
            type="button"
            className="admin-btn admin-btn-primary"
            onClick={() => {
              setUploadError(null)
              setSelectedFile(null)
              setIsUploadOpen(true)
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Upload Document
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="admin-alert success" role="alert">
          <span>✓ {successMessage}</span>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      )}
      {error && (
        <div className="admin-alert error" role="alert">
          <span>⚠️ {error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="admin-stats-grid">
        <div className="admin-stat-card">
          <span className="admin-stat-label">Total Documents</span>
          <span className="admin-stat-value">{totalCount}</span>
        </div>
        <div className="admin-stat-card">
          <span className="admin-stat-label">Indexed & Ready (ChromaDB)</span>
          <span className="admin-stat-value success">{completedCount}</span>
        </div>
        <div className="admin-stat-card">
          <span className="admin-stat-label">In Pipeline</span>
          <span className="admin-stat-value warning">{processingCount}</span>
        </div>
        <div className="admin-stat-card">
          <span className="admin-stat-label">Failed Ingestion</span>
          <span className="admin-stat-value danger">{failedCount}</span>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="admin-filters-bar">
        <div className="admin-search-wrap">
          <svg className="admin-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="admin-search-input"
            placeholder="Search by filename..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setCurrentPage(1)
            }}
          />
        </div>

        <select
          className="admin-select"
          value={docTypeFilter}
          onChange={(e) => {
            setDocTypeFilter(e.target.value)
            setCurrentPage(1)
          }}
          aria-label="Filter by document type"
        >
          <option value="all">All Types</option>
          <option value="past_paper">Past Paper</option>
          <option value="textbook">Textbook</option>
          <option value="marking_scheme">Marking Scheme</option>
        </select>

        <select
          className="admin-select"
          value={gradeFilter}
          onChange={(e) => {
            setGradeFilter(e.target.value)
            setCurrentPage(1)
          }}
          aria-label="Filter by grade"
        >
          <option value="all">All Grades</option>
          <option value="10">Grade 10</option>
          <option value="11">Grade 11</option>
        </select>

        <select
          className="admin-select"
          value={yearFilter}
          onChange={(e) => {
            setYearFilter(e.target.value)
            setCurrentPage(1)
          }}
          aria-label="Filter by examination year"
        >
          <option value="all">All Years</option>
          {Array.from({ length: 12 }, (_, i) => 2026 - i).map((yr) => (
            <option key={yr} value={yr.toString()}>
              {yr}
            </option>
          ))}
        </select>

        <select
          className="admin-select"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setCurrentPage(1)
          }}
          aria-label="Filter by status"
        >
          <option value="all">All Statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="PROCESSING">Processing</option>
          <option value="UPLOADED">Uploaded</option>
          <option value="FAILED">Failed</option>
        </select>

        {(search || docTypeFilter !== 'all' || gradeFilter !== 'all' || yearFilter !== 'all' || statusFilter !== 'all') && (
          <button type="button" className="admin-reset-btn" onClick={resetFilters}>
            Clear filters
          </button>
        )}
      </div>

      {/* Documents Table */}
      <div className="admin-table-card">
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Type</th>
                <th>Grade</th>
                <th>Year</th>
                <th>Uploaded</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && documents.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <div className="auth-spinner" style={{ width: 28, height: 28 }} />
                      <span>Loading documents registry...</span>
                    </div>
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4 }}>
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span className="empty-state-title">No documents found</span>
                      <p style={{ margin: 0, fontSize: 13, color: 'var(--app-text-dim)' }}>
                        {search || docTypeFilter !== 'all' || gradeFilter !== 'all' || yearFilter !== 'all' || statusFilter !== 'all'
                          ? 'Try clearing the search query or adjusting your filters.'
                          : 'Get started by uploading your first PDF document to Amazon S3.'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                documents.map((doc) => {
                  const isBusy = actionInProgressId === doc.id
                  return (
                    <tr key={doc.id}>
                      <td>
                        <div className="doc-name-cell">
                          <div className="doc-pdf-icon" aria-hidden="true">PDF</div>
                          <div>
                            <div className="doc-filename" title={doc.filename}>{doc.filename}</div>
                            <div className="doc-meta-sub">
                              {doc.total_pages ? `${doc.total_pages} page${doc.total_pages > 1 ? 's' : ''}` : 'Pending page scan'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="type-tag">
                          {doc.doc_type === 'past_paper' && 'Past Paper'}
                          {doc.doc_type === 'textbook' && 'Textbook'}
                          {doc.doc_type === 'marking_scheme' && 'Marking Scheme'}
                        </span>
                      </td>
                      <td>{doc.grade ? `Grade ${doc.grade}` : '—'}</td>
                      <td>{doc.year || '—'}</td>
                      <td style={{ color: 'var(--app-text-muted)', fontSize: 13 }}>
                        {formatDate(doc.uploaded_at)}
                      </td>
                      <td>
                        {doc.processing_status === 'COMPLETED' && (
                          <span className="status-pill completed">
                            <span>✓</span> Indexed
                          </span>
                        )}
                        {doc.processing_status === 'PROCESSING' && (
                          <span className="status-pill processing">
                            <span className="auth-spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} />
                            Processing...
                          </span>
                        )}
                        {doc.processing_status === 'UPLOADED' && (
                          <span className="status-pill uploaded">
                            <span>•</span> Queued
                          </span>
                        )}
                        {doc.processing_status === 'FAILED' && (
                          <span
                            className="status-pill failed"
                            title={doc.processing_error || 'Processing encountered an error.'}
                          >
                            <span>✕</span> Failed
                          </span>
                        )}
                      </td>
                      <td>
                        <div className="table-actions" style={{ justifyContent: 'flex-end' }}>
                          {doc.processing_status === 'FAILED' && (
                            <button
                              type="button"
                              className="action-icon-btn retry"
                              title="Retry processing and ChromaDB embedding"
                              onClick={() => void handleRetry(doc)}
                              disabled={isBusy}
                            >
                              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                              </svg>
                            </button>
                          )}
                          <button
                            type="button"
                            className="action-icon-btn"
                            title="Download original PDF from Amazon S3"
                            onClick={() => void handleDownload(doc)}
                            disabled={isBusy}
                          >
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                              <polyline points="7 10 12 15 17 10" />
                              <line x1="12" y1="15" x2="12" y2="3" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            className="action-icon-btn danger"
                            title="Delete document and vector embeddings"
                            onClick={() => setDocToDelete(doc)}
                            disabled={isBusy}
                          >
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {totalCount > pageSize && (
          <div className="admin-pagination">
            <span>
              Showing {Math.min((currentPage - 1) * pageSize + 1, totalCount)}–
              {Math.min(currentPage * pageSize, totalCount)} of {totalCount} documents
            </span>
            <div className="pagination-controls">
              <button
                type="button"
                className="page-btn"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1 || isLoading}
              >
                Previous
              </button>
              <button
                type="button"
                className="page-btn"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages || isLoading}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Document Modal */}
      {isUploadOpen && (
        <div className="modal-overlay" onClick={() => !isUploading && setIsUploadOpen(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Upload Syllabus Document</h2>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => !isUploading && setIsUploadOpen(false)}
                disabled={isUploading}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit}>
              <div className="modal-body">
                {uploadError && (
                  <div className="admin-alert error" role="alert">
                    <span>⚠️ {uploadError}</span>
                  </div>
                )}

                {/* Dropzone */}
                {!selectedFile ? (
                  <div
                    className={`dropzone ${isDragging ? 'active' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setIsDragging(true)
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleFileDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/pdf"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          validateAndSelectFile(e.target.files[0])
                        }
                      }}
                    />
                    <div className="dropzone-icon" aria-hidden="true">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    </div>
                    <span className="dropzone-text">Click or drag PDF file here</span>
                    <span className="dropzone-hint">Supports O/L Science past papers, textbooks, marking schemes (Max 20 MB)</span>
                  </div>
                ) : (
                  <div className="selected-file-card">
                    <div className="selected-file-info">
                      <div className="doc-pdf-icon" aria-hidden="true">PDF</div>
                      <div>
                        <div className="selected-file-name" title={selectedFile.name}>{selectedFile.name}</div>
                        <div className="selected-file-size">{formatFileSize(selectedFile.size)}</div>
                      </div>
                    </div>
                    {!isUploading && (
                      <button
                        type="button"
                        className="action-icon-btn danger"
                        onClick={() => setSelectedFile(null)}
                        title="Remove file"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                )}

                {/* Metadata Fields */}
                <div className="form-grid">
                  <div className="form-group full-width">
                    <label htmlFor="doc-type-select">
                      Document Type <span className="required">*</span>
                    </label>
                    <select
                      id="doc-type-select"
                      className="form-control"
                      value={uploadDocType}
                      onChange={(e) => setUploadDocType(e.target.value as DocumentType)}
                      disabled={isUploading}
                      required
                    >
                      <option value="past_paper">Past Paper</option>
                      <option value="textbook">Textbook</option>
                      <option value="marking_scheme">Marking Scheme</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="doc-grade-select">Target Grade</label>
                    <select
                      id="doc-grade-select"
                      className="form-control"
                      value={uploadGrade}
                      onChange={(e) => setUploadGrade(e.target.value)}
                      disabled={isUploading}
                    >
                      <option value="11">Grade 11</option>
                      <option value="10">Grade 10</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="doc-year-input">Exam / Edition Year</label>
                    <input
                      id="doc-year-input"
                      type="number"
                      className="form-control"
                      placeholder="e.g. 2023"
                      min={2000}
                      max={2030}
                      value={uploadYear}
                      onChange={(e) => setUploadYear(e.target.value)}
                      disabled={isUploading}
                    />
                  </div>
                </div>

                {/* Upload Progress Bar */}
                {isUploading && (
                  <div className="progress-container">
                    <div className="progress-header">
                      <span>{uploadProgress < 100 ? 'Uploading to Amazon S3...' : 'Registering & queuing ingestion...'}</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                    </div>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="admin-btn admin-btn-secondary"
                  onClick={() => setIsUploadOpen(false)}
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="admin-btn admin-btn-primary"
                  disabled={!selectedFile || isUploading}
                >
                  {isUploading ? (
                    <>
                      <div className="auth-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                      Uploading...
                    </>
                  ) : (
                    'Upload & Ingest'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {docToDelete && (
        <div className="modal-overlay" onClick={() => !isDeleting && setDocToDelete(null)}>
          <div className="modal-dialog" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Confirm Deletion</h2>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => !isDeleting && setDocToDelete(null)}
                disabled={isDeleting}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--app-text-main)' }}>
                Are you sure you want to delete <strong>{docToDelete.filename}</strong>?
              </p>
              <div className="admin-alert error" style={{ fontSize: 13 }}>
                <span>
                  This action permanently removes the PDF from the private Amazon S3 bucket,
                  purges all associated vector embeddings from ChromaDB, and removes database records.
                </span>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="admin-btn admin-btn-secondary"
                onClick={() => setDocToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="admin-btn"
                style={{ background: '#ef4444', color: '#fff' }}
                onClick={() => void confirmDelete()}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
