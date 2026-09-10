import type { SimilarQuestion } from '../types/api'

type SimilarQuestionsProps = {
  questions: SimilarQuestion[]
}

function formatQuestionType(questionType: string | null): string {
  if (!questionType) return 'Unknown type'
  return questionType
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function SimilarQuestions({ questions }: SimilarQuestionsProps) {
  if (questions.length === 0) return null

  return (
    <section className="similar-questions" aria-labelledby="similar-questions-title">
      <h2 id="similar-questions-title">Similar Questions</h2>
      <div className="similar-question-list">
        {questions.map((item, index) => (
          <article className="similar-question" key={`${item.year}-${item.question_number}-${index}`}>
            <div className="similar-question-meta">
              <strong>{item.year ?? 'Unknown year'}</strong>
              {item.question_number !== null && <span>Q{item.question_number}</span>}
              <span>{formatQuestionType(item.question_type)}</span>
            </div>
            <p>{item.question}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
