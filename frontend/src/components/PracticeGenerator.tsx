import { useState, useEffect } from 'react'
import type {
  PracticeTopic,
  PracticeQuestion,
  PracticeEvaluateResponse,
} from '../types/api'
import {
  fetchPracticeTopics,
  generatePracticeQuestions,
  evaluatePracticeAnswer,
} from '../services/api'

interface PracticeGeneratorProps {
  initialTopic?: string
  initialGrade?: number
  onBackToAnalytics?: () => void
}

function formatName(name: string): string {
  if (!name) return ''
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function PracticeGenerator({
  initialTopic,
  initialGrade,
  onBackToAnalytics,
}: PracticeGeneratorProps) {
  const [topics, setTopics] = useState<PracticeTopic[]>([])
  const [selectedTopic, setSelectedTopic] = useState<string>(initialTopic || '')
  const [gradeFilter, setGradeFilter] = useState<'all' | '10' | '11'>(
    initialGrade ? (String(initialGrade) as '10' | '11') : 'all',
  )
  const [subjectFilter, setSubjectFilter] = useState<'all' | 'physics' | 'chemistry' | 'biology'>('all')
  const [questionType, setQuestionType] = useState<'mcq' | 'structured_essay' | 'essay'>('mcq')
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [count, setCount] = useState<number>(3)

  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isTopicsLoading, setIsTopicsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Generated state
  const [generatedQuestions, setGeneratedQuestions] = useState<PracticeQuestion[]>([])
  const [generatedMeta, setGeneratedMeta] = useState<{
    topic: string
    grade: number
    subject_area: string
    question_type: string
    difficulty: string
    sources?: { textbook_chunks_used: number; past_paper_exemplars_used: number }
  } | null>(null)

  // MCQ state
  const [userAnswers, setUserAnswers] = useState<Record<string | number, string>>({})
  const [checkedQuestions, setCheckedQuestions] = useState<Record<string | number, boolean>>({})
  const [showHints, setShowHints] = useState<Record<string | number, boolean>>({})

  // Essay state
  const [essayInputs, setEssayInputs] = useState<Record<string | number, string>>({})
  const [essayEvaluations, setEssayEvaluations] = useState<Record<string | number, PracticeEvaluateResponse>>({})
  const [isEvaluating, setIsEvaluating] = useState<Record<string | number, boolean>>({})
  const [revealedSolutions, setRevealedSolutions] = useState<Record<string | number, boolean>>({})

  useEffect(() => {
    async function loadTopics() {
      setIsTopicsLoading(true)
      try {
        const list = await fetchPracticeTopics()
        setTopics(list)
        if (!selectedTopic && list.length > 0) {
          const matched = initialTopic
            ? list.find(
                (t) =>
                  t.key.toLowerCase() === initialTopic.toLowerCase() ||
                  t.display_name.toLowerCase() === initialTopic.toLowerCase(),
              )
            : null
          setSelectedTopic(matched ? matched.key : list[0].key)
        }
      } catch {
        setError('Could not load topics list. Check if backend is running.')
      } finally {
        setIsTopicsLoading(false)
      }
    }
    void loadTopics()
  }, [initialTopic])

  // Filter topics based on grade & subject
  const filteredTopics = topics.filter((t) => {
    if (gradeFilter !== 'all' && String(t.grade) !== gradeFilter) return false
    if (subjectFilter !== 'all' && t.subject_area.toLowerCase() !== subjectFilter) return false
    return true
  })

  // Ensure selectedTopic stays valid when filter changes
  useEffect(() => {
    if (filteredTopics.length > 0 && !filteredTopics.some((t) => t.key === selectedTopic)) {
      setSelectedTopic(filteredTopics[0].key)
    }
  }, [gradeFilter, subjectFilter, filteredTopics, selectedTopic])

  const handleGenerate = async () => {
    if (!selectedTopic) return
    setIsLoading(true)
    setError(null)
    setGeneratedQuestions([])
    setUserAnswers({})
    setCheckedQuestions({})
    setShowHints({})
    setEssayInputs({})
    setEssayEvaluations({})
    setRevealedSolutions({})

    const topicObj = topics.find((t) => t.key === selectedTopic)

    try {
      const res = await generatePracticeQuestions({
        topic: selectedTopic,
        grade: topicObj?.grade || (gradeFilter !== 'all' ? Number(gradeFilter) : 10),
        subject_area: topicObj?.subject_area || (subjectFilter !== 'all' ? subjectFilter : undefined),
        question_type: questionType,
        difficulty: difficulty,
        count: count,
      })

      if (res.success && res.questions?.length > 0) {
        setGeneratedQuestions(res.questions)
        setGeneratedMeta({
          topic: res.topic,
          grade: res.grade,
          subject_area: res.subject_area,
          question_type: res.question_type,
          difficulty: res.difficulty,
          sources: res.source_references,
        })
      } else {
        setError(res.error || 'Could not generate questions. Please try again.')
      }
    } catch {
      setError('Failed to generate practice questions. Check that the backend server is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleOptionSelect = (qId: string | number, option: string) => {
    if (checkedQuestions[qId]) return
    setUserAnswers((prev) => ({ ...prev, [qId]: option }))
  }

  const handleCheckMCQ = (qId: string | number) => {
    setCheckedQuestions((prev) => ({ ...prev, [qId]: true }))
  }

  const handleEvaluateEssay = async (q: PracticeQuestion) => {
    const studentText = essayInputs[q.id]?.trim()
    if (!studentText) return

    setIsEvaluating((prev) => ({ ...prev, [q.id]: true }))
    try {
      const evalRes = await evaluatePracticeAnswer({
        question: q.question,
        student_answer: studentText,
        model_answer: q.model_answer,
        question_type: q.question_type,
        marking_scheme: q.marking_scheme,
        total_marks: q.total_marks || 5,
      })
      setEssayEvaluations((prev) => ({ ...prev, [q.id]: evalRes }))
    } catch {
      alert('Evaluation failed. Backend server error.')
    } finally {
      setIsEvaluating((prev) => ({ ...prev, [q.id]: false }))
    }
  }

  const handleReset = () => {
    setGeneratedQuestions([])
    setGeneratedMeta(null)
    setUserAnswers({})
    setCheckedQuestions({})
    setShowHints({})
    setEssayInputs({})
    setEssayEvaluations({})
    setRevealedSolutions({})
  }

  return (
    <div className="practice-container">
      {/* 1. Header */}
      <section className="practice-header">
        {onBackToAnalytics && (
          <button type="button" className="practice-back-link" onClick={onBackToAnalytics}>
            ← Back to Analytics
          </button>
        )}
        <h1>Practice</h1>
        <p className="practice-subtitle">
          Generate questions to test your knowledge from past papers and study materials.
        </p>
      </section>

      {/* 2. Minimalist Generator Control Box */}
      {generatedQuestions.length === 0 ? (
        <div className="practice-generator-box">
          {/* Row 1: Compact dropdowns: Grade, Subject, Topic */}
          <div className="practice-filters-row">
            <select
              className="practice-select"
              value={gradeFilter}
              onChange={(e) => setGradeFilter(e.target.value as 'all' | '10' | '11')}
              aria-label="Filter Grade"
            >
              <option value="all">All Grades</option>
              <option value="10">Grade 10</option>
              <option value="11">Grade 11</option>
            </select>

            <select
              className="practice-select"
              value={subjectFilter}
              onChange={(e) => setSubjectFilter(e.target.value as 'all' | 'physics' | 'chemistry' | 'biology')}
              aria-label="Filter Subject"
            >
              <option value="all">All Subjects</option>
              <option value="physics">Physics</option>
              <option value="chemistry">Chemistry</option>
              <option value="biology">Biology</option>
            </select>

            <select
              className="practice-select practice-topic-select"
              value={selectedTopic}
              disabled={isTopicsLoading || filteredTopics.length === 0}
              onChange={(e) => setSelectedTopic(e.target.value)}
              aria-label="Select Topic"
            >
              {isTopicsLoading ? (
                <option value="">Loading topics...</option>
              ) : filteredTopics.length === 0 ? (
                <option value="">No matching topics</option>
              ) : (
                filteredTopics.map((t) => (
                  <option key={t.key} value={t.key}>
                    {t.display_name}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Row 2: Question Type Segmented Control */}
          <div className="practice-segmented-control" role="group" aria-label="Question Type">
            <button
              type="button"
              className={`segment-btn ${questionType === 'mcq' ? 'active' : ''}`}
              onClick={() => setQuestionType('mcq')}
            >
              MCQ
            </button>
            <button
              type="button"
              className={`segment-btn ${questionType === 'structured_essay' ? 'active' : ''}`}
              onClick={() => setQuestionType('structured_essay')}
            >
              Structured
            </button>
            <button
              type="button"
              className={`segment-btn ${questionType === 'essay' ? 'active' : ''}`}
              onClick={() => setQuestionType('essay')}
            >
              Essay
            </button>
          </div>

          {/* Row 3: Difficulty and Number of Questions */}
          <div className="practice-meta-row">
            <select
              className="practice-select small"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
              aria-label="Difficulty"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>

            <select
              className="practice-select small"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              aria-label="Questions Count"
            >
              <option value={1}>1 Question</option>
              <option value={2}>2 Questions</option>
              <option value={3}>3 Questions</option>
              <option value={5}>5 Questions</option>
            </select>
          </div>

          {/* Row 4: Generate Button */}
          <button
            type="button"
            className="practice-generate-button"
            disabled={isLoading || !selectedTopic}
            onClick={handleGenerate}
          >
            {isLoading ? (
              <span className="btn-loading-content">
                <span className="practice-spinner" /> Generating Questions...
              </span>
            ) : (
              <span>✨ Generate Practice</span>
            )}
          </button>

          <p className="practice-footnote">
            Questions are generated from past papers and textbook materials
          </p>
        </div>
      ) : null}

      {error && <div className="practice-error">{error}</div>}

      {/* 3. Generated Questions Section (Matching Chat Interface Style) */}
      {generatedQuestions.length > 0 && generatedMeta && (
        <div className="practice-results-container">
          {/* Subtle Top Status Bar */}
          <div className="practice-results-header">
            <div className="results-header-text">
              <span className="results-topic">{generatedMeta.topic}</span>
              <span className="results-subtext">
                Grade {generatedMeta.grade} • {formatName(generatedMeta.subject_area)} • {generatedMeta.question_type.replace('_', ' ').toUpperCase()} • {generatedMeta.difficulty}
              </span>
            </div>
            <button type="button" className="practice-new-btn" onClick={handleReset}>
              + New Practice
            </button>
          </div>

          <div className="practice-grounding-subtle">
            Verified with textbook materials and past paper formats
          </div>

          {/* Question Cards */}
          <div className="practice-questions-stream">
            {generatedQuestions.map((q, idx) => {
              const qId = q.id || idx + 1
              const isMCQ = q.question_type === 'mcq'
              const isChecked = checkedQuestions[qId]
              const userOpt = userAnswers[qId]
              const correctOpt = q.correct_answer || ''
              const isCorrect =
                userOpt === correctOpt ||
                (userOpt && correctOpt && (userOpt.startsWith(correctOpt[0]) || correctOpt.includes(userOpt)))
              const hintOpen = showHints[qId]
              const solutionOpen = revealedSolutions[qId]
              const evalRes = essayEvaluations[qId]
              const evaluating = isEvaluating[qId]

              return (
                <div key={qId} className="practice-question-item">
                  <div className="practice-q-header">
                    <span className="practice-q-num">Question {idx + 1}</span>
                    {q.total_marks ? (
                      <span className="practice-marks">({q.total_marks} Marks)</span>
                    ) : null}
                  </div>

                  {/* Question Prompt */}
                  <div className="practice-q-text">
                    <pre className="practice-pre">{q.question}</pre>
                  </div>

                  {/* MCQ Options */}
                  {isMCQ && q.options && q.options.length > 0 && (
                    <div className="practice-options-list">
                      {q.options.map((opt, optIdx) => {
                        const isSelected = userOpt === opt
                        let optState = 'option-neutral'

                        if (isChecked) {
                          const isThisCorrect =
                            opt === correctOpt ||
                            (correctOpt && (opt.startsWith(correctOpt[0]) || correctOpt.includes(opt)))
                          if (isThisCorrect) {
                            optState = 'option-correct'
                          } else if (isSelected && !isThisCorrect) {
                            optState = 'option-wrong'
                          }
                        } else if (isSelected) {
                          optState = 'option-selected'
                        }

                        return (
                          <button
                            key={optIdx}
                            type="button"
                            className={`practice-opt-button ${optState}`}
                            onClick={() => handleOptionSelect(qId, opt)}
                            disabled={isChecked}
                          >
                            <span className="opt-letter">{String.fromCharCode(65 + optIdx)}</span>
                            <span className="opt-text">{opt}</span>
                          </button>
                        )
                      })}
                    </div>
                  )}

                  {/* MCQ Action */}
                  {isMCQ && (
                    <div className="practice-q-actions">
                      {!isChecked ? (
                        <button
                          type="button"
                          className="practice-check-btn"
                          disabled={!userOpt}
                          onClick={() => handleCheckMCQ(qId)}
                        >
                          Check Answer
                        </button>
                      ) : (
                        <span className={`practice-check-feedback ${isCorrect ? 'text-correct' : 'text-wrong'}`}>
                          {isCorrect ? '✓ Correct' : `✗ Incorrect — Correct answer: ${correctOpt}`}
                        </span>
                      )}

                      {q.hints && q.hints.length > 0 && (
                        <button
                          type="button"
                          className="practice-hint-btn"
                          onClick={() => setShowHints((prev) => ({ ...prev, [qId]: !prev[qId] }))}
                        >
                          {hintOpen ? 'Hide Hint' : 'Hint'}
                        </button>
                      )}
                    </div>
                  )}

                  {/* Hint */}
                  {hintOpen && q.hints && (
                    <div className="practice-hint-drawer">
                      <strong>Hint:</strong> {q.hints.join(' ')}
                    </div>
                  )}

                  {/* Explanation for MCQ */}
                  {isMCQ && isChecked && q.explanation && (
                    <div className="practice-explanation-drawer">
                      <strong>Explanation:</strong> {q.explanation}
                    </div>
                  )}

                  {/* Structured / Essay Textarea & Evaluation */}
                  {!isMCQ && (
                    <div className="practice-essay-area">
                      <textarea
                        className="practice-essay-input"
                        rows={4}
                        placeholder="Type your answer or steps here..."
                        value={essayInputs[qId] || ''}
                        onChange={(e) =>
                          setEssayInputs((prev) => ({ ...prev, [qId]: e.target.value }))
                        }
                      />

                      <div className="practice-essay-actions">
                        <button
                          type="button"
                          className="practice-grade-btn"
                          disabled={evaluating || !essayInputs[qId]?.trim()}
                          onClick={() => void handleEvaluateEssay(q)}
                        >
                          {evaluating ? 'Evaluating...' : 'Grade with AI'}
                        </button>

                        <button
                          type="button"
                          className="practice-toggle-scheme"
                          onClick={() =>
                            setRevealedSolutions((prev) => ({ ...prev, [qId]: !prev[qId] }))
                          }
                        >
                          {solutionOpen ? 'Hide Scheme' : 'View Model Answer & Scheme'}
                        </button>
                      </div>

                      {evalRes && (
                        <div className="practice-eval-box">
                          <div className="practice-eval-header">
                            <span className="practice-eval-score">
                              Awarded {evalRes.marks_awarded} / {evalRes.total_possible_marks} Marks
                            </span>
                            <span className="practice-eval-pct">({Math.round(evalRes.percentage)}%)</span>
                          </div>
                          <p className="practice-eval-p">{evalRes.feedback}</p>
                        </div>
                      )}

                      {solutionOpen && (
                        <div className="practice-solution-box">
                          <div className="solution-block">
                            <strong>Model Answer:</strong>
                            <pre className="practice-pre">{q.model_answer}</pre>
                          </div>
                          {q.marking_scheme && (
                            <div className="solution-block">
                              <strong>Marking Scheme:</strong>
                              <ul>
                                {q.marking_scheme.map((pt, pIdx) => (
                                  <li key={pIdx}>
                                    {pt.point} — <em>[{pt.marks} mark{pt.marks > 1 ? 's' : ''}]</em>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
