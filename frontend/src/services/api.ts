import type {
  SimilarQuestion,
  SimilarQuestionsResponse,
  TopicFrequency,
  TopicFrequenciesResponse,
  TopicTrend,
  TopicTrendsResponse,
  ImportantTopic,
  ImportantTopicsResponse,
  PracticeTopic,
  PracticeTopicsResponse,
  PracticeGenerateRequest,
  PracticeGenerateResponse,
  PracticeEvaluateRequest,
  PracticeEvaluateResponse,
  UserProfile,
  OnboardingData,
  AuthTokenResponse,
  TokenRefreshResponse,
  DocumentItem,
  DocumentListResponse,
  DocumentDownloadResponse,
  DocumentFilterParams,
} from '../types/api'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const apiBase = `${apiUrl}/api`

// --- Token Storage Helpers ---

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

export function setAuthTokens(tokens: { access_token: string; refresh_token?: string | null }) {
  localStorage.setItem('access_token', tokens.access_token)
  if (tokens.refresh_token) {
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }
}

export function clearAuthTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

// --- Authenticated Fetch with Silent Refresh Interceptor ---

export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken()
  const headers = new Headers(options.headers || {})
  
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let response = await fetch(url, { ...options, headers })

  // If access token expired (401), attempt silent token refresh
  if (response.status === 401) {
    const refreshToken = getRefreshToken()
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${apiBase}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })

        if (refreshRes.ok) {
          const refreshData = (await refreshRes.json()) as TokenRefreshResponse
          setAuthTokens({
            access_token: refreshData.access_token,
            refresh_token: refreshData.refresh_token || refreshToken,
          })

          // Retry original request with fresh access token
          headers.set('Authorization', `Bearer ${refreshData.access_token}`)
          response = await fetch(url, { ...options, headers })
        } else {
          // Refresh token invalid or expired -> clear tokens
          clearAuthTokens()
        }
      } catch {
        clearAuthTokens()
      }
    }
  }

  return response
}

function getAnswer(payload: unknown): string {
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) {
    return payload
      .map((item) => getAnswer(item))
      .filter(Boolean)
      .join('\n\n')
  }
  if (!payload || typeof payload !== 'object') return ''

  const data = payload as Record<string, unknown>
  const answer = data.answer ?? data.content ?? data.response ?? data.result ?? data.output ?? data.text
  if (typeof answer === 'object') return getAnswer(answer)
  return typeof answer === 'string' ? answer : ''
}

async function getJson(response: Response): Promise<unknown> {
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`
    try {
      const errJson = await response.json()
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail)
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail)
  }
  return response.json()
}

// --- Authentication API Methods ---

export async function loginWithGoogle(
  idToken: string,
  grade: number = 11,
  targetExam: string = 'GCE O/L',
): Promise<AuthTokenResponse> {
  const response = await fetch(`${apiBase}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id_token: idToken,
      grade: grade,
      target_exam: targetExam,
    }),
  })
  const data = (await getJson(response)) as AuthTokenResponse
  setAuthTokens(data)
  return data
}

export async function loginWithEmail(email: string, password: string): Promise<AuthTokenResponse> {
  const response = await fetch(`${apiBase}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = (await getJson(response)) as AuthTokenResponse
  setAuthTokens(data)
  return data
}

export async function registerWithEmail(params: {
  email: string
  password: string
  full_name?: string
  grade?: number
  target_exam?: string
}): Promise<AuthTokenResponse> {
  const response = await fetch(`${apiBase}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: params.email,
      password: params.password,
      full_name: params.full_name || '',
      grade: params.grade || 11,
      target_exam: params.target_exam || 'GCE O/L',
    }),
  })
  const data = (await getJson(response)) as AuthTokenResponse
  setAuthTokens(data)
  return data
}

export async function logoutUser(): Promise<void> {
  const refreshToken = getRefreshToken()
  if (refreshToken) {
    try {
      await fetch(`${apiBase}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
    } catch {
      // ignore
    }
  }
  clearAuthTokens()
}

export async function fetchCurrentUserProfile(): Promise<UserProfile | null> {
  const token = getAccessToken()
  if (!token) return null

  try {
    const response = await authFetch(`${apiBase}/auth/me`)
    if (!response.ok) {
      clearAuthTokens()
      return null
    }
    return (await response.json()) as UserProfile
  } catch {
    return null
  }
}

export async function submitOnboarding(data: OnboardingData): Promise<UserProfile> {
  const response = await authFetch(`${apiBase}/auth/onboarding`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return (await getJson(response)) as UserProfile
}

export async function updateUserProfile(data: Partial<OnboardingData>): Promise<UserProfile> {
  const response = await authFetch(`${apiBase}/auth/profile`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return (await getJson(response)) as UserProfile
}

// --- RAG & Chat API ---

export async function askTutor(question: string): Promise<string> {
  const response = await authFetch(`${apiBase}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  const result = await getJson(response)
  const answer = getAnswer(result)
  if (!answer) throw new Error('The API returned no answer text.')
  return answer
}

export async function findSimilarQuestions(question: string): Promise<SimilarQuestion[]> {
  const response = await authFetch(
    `${apiBase}/questions/similar?query=${encodeURIComponent(question)}`,
  )
  const payload = (await getJson(response)) as SimilarQuestionsResponse
  return payload.results ?? []
}

// --- Topic Analytics API ---

export async function fetchTopicFrequencies(params?: {
  year?: number
  start_year?: number
  end_year?: number
}): Promise<TopicFrequency[]> {
  const query = new URLSearchParams()
  if (params?.year) query.set('year', params.year.toString())
  if (params?.start_year) query.set('start_year', params.start_year.toString())
  if (params?.end_year) query.set('end_year', params.end_year.toString())

  const queryStr = query.toString() ? `?${query.toString()}` : ''
  const response = await authFetch(`${apiBase}/topics/frequency${queryStr}`)
  const payload = (await getJson(response)) as TopicFrequenciesResponse
  return payload.frequencies ?? []
}

export async function fetchTopicTrends(topic?: string): Promise<TopicTrend[]> {
  const queryStr = topic ? `?topic=${encodeURIComponent(topic)}` : ''
  const response = await authFetch(`${apiBase}/topics/trends${queryStr}`)
  const payload = (await getJson(response)) as TopicTrendsResponse
  return payload.trends ?? []
}

export async function fetchImportantTopics(): Promise<ImportantTopic[]> {
  const response = await authFetch(`${apiBase}/topics/important`)
  const payload = (await getJson(response)) as ImportantTopicsResponse
  return payload.topics ?? []
}

// --- Practice Questions & Evaluation API ---

export async function fetchPracticeTopics(): Promise<PracticeTopic[]> {
  const response = await authFetch(`${apiBase}/practice/topics`)
  const payload = (await getJson(response)) as PracticeTopicsResponse
  return payload.topics ?? []
}

export async function generatePracticeQuestions(
  request: PracticeGenerateRequest,
): Promise<PracticeGenerateResponse> {
  const response = await authFetch(`${apiBase}/practice/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const payload = (await getJson(response)) as PracticeGenerateResponse
  return payload
}

export async function evaluatePracticeAnswer(
  request: PracticeEvaluateRequest,
): Promise<PracticeEvaluateResponse> {
  const response = await authFetch(`${apiBase}/practice/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const payload = (await getJson(response)) as PracticeEvaluateResponse
  return payload
}

// --- Document Management API (Admin) ---

export async function fetchDocuments(
  params?: DocumentFilterParams,
): Promise<DocumentListResponse> {
  const query = new URLSearchParams()
  if (params?.search) query.set('search', params.search)
  if (params?.doc_type) query.set('doc_type', params.doc_type)
  if (params?.grade !== undefined && params.grade !== null) query.set('grade', params.grade.toString())
  if (params?.year !== undefined && params.year !== null) query.set('year', params.year.toString())
  if (params?.processing_status) query.set('processing_status', params.processing_status)
  if (params?.page) query.set('page', params.page.toString())
  if (params?.limit) query.set('limit', params.limit.toString())

  const queryStr = query.toString() ? `?${query.toString()}` : ''
  const response = await authFetch(`${apiBase}/documents${queryStr}`)
  return (await getJson(response)) as DocumentListResponse
}

export async function fetchDocumentDetails(id: string): Promise<DocumentItem> {
  const response = await authFetch(`${apiBase}/documents/${id}`)
  return (await getJson(response)) as DocumentItem
}

export async function uploadDocument(
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<DocumentItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const token = getAccessToken()

    xhr.open('POST', `${apiBase}/documents/upload`)
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100)
          onProgress(percent)
        }
      }
    }

    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText)
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data as DocumentItem)
        } else {
          const detail = data?.detail || `Upload failed with status ${xhr.status}`
          reject(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
        }
      } catch {
        reject(new Error(`Upload failed with status ${xhr.status}`))
      }
    }

    xhr.onerror = () => {
      reject(new Error('Network error occurred during document upload.'))
    }

    xhr.send(formData)
  })
}

export async function downloadDocument(id: string): Promise<DocumentDownloadResponse> {
  const response = await authFetch(`${apiBase}/documents/${id}/download`)
  return (await getJson(response)) as DocumentDownloadResponse
}

export async function deleteDocument(id: string): Promise<{ success: boolean; message: string }> {
  const response = await authFetch(`${apiBase}/documents/${id}`, {
    method: 'DELETE',
  })
  return (await getJson(response)) as { success: boolean; message: string }
}

export async function retryDocumentProcessing(id: string): Promise<DocumentItem> {
  const response = await authFetch(`${apiBase}/documents/${id}/process`, {
    method: 'POST',
  })
  return (await getJson(response)) as DocumentItem
}
