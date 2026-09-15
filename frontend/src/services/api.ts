import type { SimilarQuestion, SimilarQuestionsResponse } from '../types/api'

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
