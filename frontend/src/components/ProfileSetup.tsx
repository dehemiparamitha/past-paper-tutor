import { useState, type FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import './ProfileSetup.css'

interface ProfileSetupProps {
  onComplete: () => void
}

const GRADES = [
  { grade: 10, exam: 'GCE O/L', label: 'Grade 10' },
  { grade: 11, exam: 'GCE O/L', label: 'Grade 11' },
  { grade: 12, exam: 'GCE A/L', label: 'Grade 12' },
  { grade: 13, exam: 'GCE A/L', label: 'Grade 13' },
]

const MEDIUMS = ['English', 'Sinhala', 'Tamil']

export function ProfileSetup({ onComplete }: ProfileSetupProps) {
  const { user, completeOnboarding } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [grade, setGrade] = useState<number>(user?.grade || 11)
  const [targetExam, setTargetExam] = useState<string>(user?.target_exam || 'GCE O/L')
  const [language, setLanguage] = useState<string>(user?.language || 'English')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSelectGrade = (g: number, exam: string) => {
    setGrade(g)
    setTargetExam(exam)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await completeOnboarding({
        full_name: fullName.trim() || undefined,
        grade,
        target_exam: targetExam,
        language,
        onboarding_completed: true,
      })
      onComplete()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleSkip = async () => {
    setSaving(true)
    try {
      await completeOnboarding({
        grade,
        target_exam: targetExam,
        language,
        onboarding_completed: false,
      })
    } catch {
      // Proceed without blocking
    } finally {
      setSaving(false)
      onComplete()
    }
  }

  return (
    <div className="setup-screen">
      <div className="setup-ambient" />

      <div className="setup-modal">
        {/* Header */}
        <div className="setup-head">
          <div className="setup-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
            </svg>
          </div>
          <h2 className="setup-title">Welcome to Paperwise</h2>
          <p className="setup-subtitle">Quickly set your syllabus level to get personalized past paper explanations.</p>
        </div>

        {error && <div className="setup-err">{error}</div>}

        {/* Form */}
        <form className="setup-form" onSubmit={handleSubmit}>
          <div className="setup-field">
            <label className="setup-label">Your Name</label>
            <input
              type="text"
              className="setup-text-input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Kasun Perera"
            />
          </div>

          <div className="setup-field">
            <label className="setup-label">Grade</label>
            <div className="setup-segments">
              {GRADES.map((g) => {
                const isActive = grade === g.grade && targetExam === g.exam
                return (
                  <button
                    key={g.label}
                    type="button"
                    className={`setup-segment-btn ${isActive ? 'active' : ''}`}
                    onClick={() => handleSelectGrade(g.grade, g.exam)}
                  >
                    {g.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="setup-field">
            <label className="setup-label">Language Medium</label>
            <div className="setup-medium-row">
              {MEDIUMS.map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`setup-medium-btn ${language === m ? 'active' : ''}`}
                  onClick={() => setLanguage(m)}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <button type="submit" className="setup-submit-btn" disabled={saving}>
            {saving ? 'Setting up…' : 'Continue to Tutor →'}
          </button>

          <button type="button" className="setup-skip-link" onClick={handleSkip} disabled={saving}>
            Skip for now
          </button>
        </form>
      </div>
    </div>
  )
}
