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
  grade?: number
  subject_area?: string
  count: number
}

export type TopicFrequenciesResponse = {
  total_topics: number
  frequencies: TopicFrequency[]
}

export type TopicTrend = {
  topic: string
  grade?: number
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
  grade?: number
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

export type PracticeTopic = {
  key: string
  display_name: string
  grade: number
  subject_area: string
}

export type PracticeTopicsResponse = {
  total_topics: number
  topics: PracticeTopic[]
}

export type PracticeMarkingPoint = {
  point: string
  marks: number
}

export type PracticeQuestion = {
  id: number | string
  question: string
  question_type: 'mcq' | 'structured_essay' | 'essay'
  options?: string[]
  correct_answer?: string
  model_answer: string
  marking_scheme: PracticeMarkingPoint[]
  total_marks: number
  explanation: string
  hints?: string[]
  relevant_textbook_concept?: string
}

export type PracticeGenerateRequest = {
  topic: string
  grade?: number
  subject_area?: string
  question_type?: 'mcq' | 'structured_essay' | 'essay'
  difficulty?: 'easy' | 'medium' | 'hard'
  count?: number
}

export type PracticeGenerateResponse = {
  success: boolean
  topic: string
  grade: number
  subject_area: string
  question_type: string
  difficulty: string
  total_generated: number
  questions: PracticeQuestion[]
  source_references?: {
    textbook_chunks_used: number
    past_paper_exemplars_used: number
  }
  error?: string
}

export type EvaluationPointBreakdown = {
  point: string
  marks_allocated: number
  marks_awarded: number
  student_performance: string
}

export type PracticeEvaluateRequest = {
  question: string
  student_answer: string
  model_answer: string
  question_type: string
  marking_scheme?: PracticeMarkingPoint[]
  total_marks: number
}

export type PracticeEvaluateResponse = {
  success: boolean
  marks_awarded: number
  total_possible_marks: number
  percentage: number
  is_fully_correct: boolean
  feedback: string
  point_breakdown?: EvaluationPointBreakdown[]
  key_improvements?: string[]
  error?: string
}
