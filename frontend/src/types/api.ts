export type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
  similarQuestions?: SimilarQuestion[]
  createdAt?: number
}

export type ChatSession = {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
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

export type TopicFrequency = {
  topic: string
  count: number
}

export type TopicFrequenciesResponse = {
  total_topics: number
  frequencies: TopicFrequency[]
}

export type TopicTrend = {
  topic: string
  subject_area: string
  total_questions: number
  yearly_breakdown: Record<string, number>
  trend: 'rising' | 'declining' | 'stable'
}

export type TopicTrendsResponse = {
  total_topics: number
  trends: TopicTrend[]
}

export type ImportantTopicScoreBreakdown = {
  frequency_score: number
  recency_score: number
  consistency_score: number
  marks_score: number
}

export type ImportantTopic = {
  topic: string
  subject_area: string
  importance_score: number
  tier: 'High' | 'Moderate' | 'Low'
  badge: string
  breakdown: ImportantTopicScoreBreakdown
  total_questions: number
  years_appeared: number
  total_years_evaluated: number
}

export type ImportantTopicsResponse = {
  total_analyzed: number
  high_priority_count: number
  topics: ImportantTopic[]
}
