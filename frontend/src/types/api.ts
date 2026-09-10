export type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
}

export type SimilarQuestion = {
  year: number | null
  question_number: number | null
  question_type: string | null
  question: string
  similarity: number
}

export type SimilarQuestionsResponse = {
  results?: SimilarQuestion[]
}
