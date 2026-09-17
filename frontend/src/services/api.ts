import type {
  SimilarQuestion,
  SimilarQuestionsResponse,
  TopicFrequency,
  TopicFrequenciesResponse,
  TopicTrend,
  TopicTrendsResponse,
  ImportantTopic,
  ImportantTopicsResponse,
} from '../types/api'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
  return response.json()
}

export async function askTutor(question: string): Promise<string> {
  const response = await fetch(`${apiUrl}/chat`, {
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
  const response = await fetch(
    `${apiUrl}/api/questions/similar?query=${encodeURIComponent(question)}`,
  )
  const payload = (await getJson(response)) as SimilarQuestionsResponse
  return payload.results ?? []
}

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
  const response = await fetch(`${apiUrl}/api/topics/frequency${queryStr}`)
  const payload = (await getJson(response)) as TopicFrequenciesResponse
  return payload.frequencies ?? []
}

export async function fetchTopicTrends(topic?: string): Promise<TopicTrend[]> {
  const queryStr = topic ? `?topic=${encodeURIComponent(topic)}` : ''
  const response = await fetch(`${apiUrl}/api/topics/trends${queryStr}`)
  const payload = (await getJson(response)) as TopicTrendsResponse
  return payload.trends ?? []
}

export async function fetchImportantTopics(): Promise<ImportantTopic[]> {
  const response = await fetch(`${apiUrl}/api/topics/important`)
  const payload = (await getJson(response)) as ImportantTopicsResponse
  return payload.topics ?? []
}
