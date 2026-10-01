import { useState, type FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import './ProfileSetup.css'

interface ProfileSetupProps {
  onComplete: () => void
}

const SRI_LANKAN_DISTRICTS = [
  'Colombo',
  'Gampaha',
  'Kalutara',
  'Kandy',
  'Matale',
  'Nuwara Eliya',
  'Galle',
  'Matara',
  'Hambantota',
  'Jaffna',
  'Kilinochchi',
  'Mannar',
  'Vavuniya',
  'Mullaittivu',
  'Batticaloa',
  'Ampara',
  'Trincomalee',
  'Kurunegala',
  'Puttalam',
  'Anuradhapura',
  'Polonnaruwa',
  'Badulla',
  'Monaragala',
  'Ratnapura',
  'Kegalle',
]

const AIM_OPTIONS = [
  'Finals prep',
  'Top grades & A pass',
  'Foundational boost',
  'Past paper mastery',
]

const WEEKLY_TIME_OPTIONS = [
  '3 hours a week',
  '5 hours a week',
  '7 hours a week',
  '10+ hours a week',
]

const NUDGE_OPTIONS = [
  'Weekdays at 7 PM',
  'Every evening at 6 PM',
  'Weekend mornings',
  'No reminders',
]

const FEELING_OPTIONS = [
  'Finding my footing',
  'Confident & ready',
  'Need steady support',
  'Exam stress',
]

const REMAINING_SUBJECTS = [
  'Mathematics',
  'Sinhala',
  'English',
  'History',
  'Religion',
  'Optional 1',
  'Optional 2',
  'Optional 3',
]

export function ProfileSetup({ onComplete }: ProfileSetupProps) {
  const { user, completeOnboarding } = useAuth()

  // Current active step (1 to 6)
  const [currentStep, setCurrentStep] = useState<number>(1)

  // Step 1: Basics
  const [fullName, setFullName] = useState(user?.full_name || 'Nethmi Perera')
  const [district, setDistrict] = useState(user?.district || 'Colombo')
  const [school, setSchool] = useState(user?.school || '')

  // Step 2: Exam
  const [targetExam, setTargetExam] = useState<string>(user?.target_exam || 'GCE O/L')

  // Step 3: Grade
  const [grade, setGrade] = useState<number>(user?.grade || 11)

  // Step 4: Focus Subject
  const [focusSubject] = useState<string>('Science')

  // Step 5: Preferences
  const [studyGoal, setStudyGoal] = useState<string>(user?.study_goal || 'Finals prep')
  const [weeklyHours, setWeeklyHours] = useState<string>(user?.weekly_hours || '5 hours a week')
  const [studyTime, setStudyTime] = useState<string>(user?.study_time || 'Weekdays at 7 PM')
  const [confidenceLevel, setConfidenceLevel] = useState<string>(user?.confidence_level || 'Finding my footing')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFinalSubmit = async () => {
    setSaving(true)
    setError(null)
    try {
      await completeOnboarding({
        full_name: fullName.trim() || undefined,
        district,
        school: school.trim() || undefined,
        target_exam: targetExam,
        grade,
        study_goal: studyGoal,
        weekly_hours: weeklyHours,
        study_time: studyTime,
        confidence_level: confidenceLevel,
        onboarding_completed: true,
      })
      onComplete()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to finalize setup. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveAndContinueLater = async () => {
    setSaving(true)
    try {
      await completeOnboarding({
        full_name: fullName.trim() || undefined,
        district,
        school: school.trim() || undefined,
        target_exam: targetExam,
        grade,
        study_goal: studyGoal,
        weekly_hours: weeklyHours,
        study_time: studyTime,
        confidence_level: confidenceLevel,
        onboarding_completed: false,
      })
    } catch {
      // Allow proceeding
    } finally {
      setSaving(false)
      onComplete()
    }
  }

  const handleNext = (e?: FormEvent) => {
    e?.preventDefault()
    if (currentStep < 6) {
      setCurrentStep((prev) => prev + 1)
    } else {
      void handleFinalSubmit()
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1)
    }
  }

  return (
    <div className={`setup-screen step-${currentStep}`}>
      {/* Background ambient glow */}
      <div className="setup-screen-glow" aria-hidden="true" />

      <div className="setup-modal-container">
        {/* Top Header */}
        <div className="setup-top-header">
          <div className="setup-brand">
            <span className="setup-brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00df82" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </span>
            <span className="setup-brand-name">Paperwise</span>
          </div>
          <button
            type="button"
            className="setup-save-later-btn"
            onClick={handleSaveAndContinueLater}
            disabled={saving}
          >
            Save & continue later
          </button>
        </div>

        {/* 6-segment Progress Bar */}
        <div className="setup-progress-wrapper">
          <div className="setup-progress-meta">
            <span className="setup-category-tag">
              {currentStep === 1 ? 'BASICS' : currentStep <= 4 ? 'PROFILE SETUP' : currentStep === 5 ? 'PREFERENCES' : 'REVIEW'}
            </span>
            <span className="setup-step-counter">Step {currentStep} of 6</span>
          </div>
          <div className="setup-progress-track">
            {[1, 2, 3, 4, 5, 6].map((stepNum) => (
              <div
                key={stepNum}
                className={`setup-progress-segment ${stepNum <= currentStep ? 'active' : ''}`}
              />
            ))}
          </div>
        </div>

        {error && <div className="setup-error-banner">{error}</div>}

        {/* SCREEN 1: Profile Basics */}
        {currentStep === 1 && (
          <form className="setup-body" onSubmit={handleNext}>
            <div className="setup-heading-group">
              <h2 className="setup-main-title">Tell us a bit about you</h2>
              <p className="setup-main-subtitle">A few quick details help us personalize your study experience.</p>
            </div>

            <div className="setup-simple-fields">
              <div className="setup-grid-fields">
                <div className="setup-field-block">
                  <label className="setup-field-label">Name</label>
                  <div className="setup-input-container">
                    <input
                      type="text"
                      className="setup-text-input"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g. Nethmi Perera"
                      required
                    />
                  </div>
                </div>

                <div className="setup-field-block">
                  <label className="setup-field-label">District</label>
                  <div className="setup-input-container">
                    <select
                      className="setup-select-input"
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                    >
                      {SRI_LANKAN_DISTRICTS.map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                    <span className="setup-select-chevron">▾</span>
                  </div>
                </div>
              </div>

              <div className="setup-field-block">
                <label className="setup-field-label">
                  <span>School</span>
                  <span className="setup-field-optional">Optional</span>
                </label>
                <div className="setup-input-container">
                  <input
                    type="text"
                    className="setup-text-input"
                    value={school}
                    onChange={(e) => setSchool(e.target.value)}
                    placeholder="Enter your school name"
                  />
                </div>
              </div>
            </div>

            <div className="setup-footer">
              <button
                type="button"
                className="setup-back-btn"
                onClick={handleSaveAndContinueLater}
              >
                Skip for now
              </button>
              <button type="submit" className="setup-continue-btn">
                Continue →
              </button>
            </div>
          </form>
        )}

        {/* SCREEN 2: Exam Selection */}
        {currentStep === 2 && (
          <div className="setup-body">
            <div className="setup-heading-group">
              <h2 className="setup-main-title">Choose your exam</h2>
              <p className="setup-main-subtitle">Pick the examination curriculum you are preparing for.</p>
            </div>

            <div className="setup-cards-row">
              {/* GCE O/L Card */}
              <div
                className={`setup-select-card ${targetExam === 'GCE O/L' ? 'selected' : ''}`}
                onClick={() => setTargetExam('GCE O/L')}
              >
                <div className="setup-card-top">
                  <span className="setup-card-title">GCE O/L</span>
                  <span className="setup-pill-badge green">Ready Now</span>
                </div>
                <p className="setup-card-desc">Start studying with verified Ordinary Level past papers and questions.</p>
              </div>

              {/* GCE A/L Card */}
              <div className="setup-select-card disabled" title="Coming Soon">
                <div className="setup-card-top">
                  <span className="setup-card-title">GCE A/L</span>
                  <span className="setup-pill-badge gray">Coming Soon</span>
                </div>
                <p className="setup-card-desc">Advanced Level syllabus questions and analytics are currently in preparation.</p>
              </div>
            </div>

            <div className="setup-footer">
              <button type="button" className="setup-back-btn" onClick={handleBack}>
                ← Back
              </button>
              <button type="button" className="setup-continue-btn" onClick={handleNext}>
                Continue →
              </button>
            </div>
          </div>
        )}

        {/* SCREEN 3: Grade Selection */}
        {currentStep === 3 && (
          <div className="setup-body">
            <div className="setup-heading-group">
              <h2 className="setup-main-title">Which grade are you studying?</h2>
              <p className="setup-main-subtitle">Select your grade level to tune explanations and question difficulty.</p>
            </div>

            <div className="setup-cards-row">
              {/* Grade 10 */}
              <div
                className={`setup-select-card ${grade === 10 ? 'selected' : ''}`}
                onClick={() => setGrade(10)}
              >
                <div className="setup-card-top">
                  <span className="setup-card-title">Grade 10</span>
                  {grade === 10 && <span className="setup-pill-badge green">Selected</span>}
                </div>
                <p className="setup-card-desc">Build fundamentals and prepare syllabus topics early.</p>
              </div>

              {/* Grade 11 */}
              <div
                className={`setup-select-card ${grade === 11 ? 'selected' : ''}`}
                onClick={() => setGrade(11)}
              >
                <div className="setup-card-top">
                  <span className="setup-card-title">Grade 11</span>
                  {grade === 11 && <span className="setup-pill-badge green">Selected</span>}
                </div>
                <p className="setup-card-desc">Focus on exam technique, speed, and past-paper revision.</p>
              </div>
            </div>

            <div className="setup-footer">
              <button type="button" className="setup-back-btn" onClick={handleBack}>
                ← Back
              </button>
              <button type="button" className="setup-continue-btn" onClick={handleNext}>
                Continue →
              </button>
            </div>
          </div>
        )}

        {/* SCREEN 4: Subject Setup */}
        {currentStep === 4 && (
          <div className="setup-body">
            <div className="setup-heading-group">
              <h2 className="setup-main-title">Set up your subjects</h2>
              <p className="setup-main-subtitle">Science is active right now. Other subjects are being loaded.</p>
            </div>

            <div className="setup-subject-focus-card">
              <div className="setup-subject-focus-info">
                <div className="setup-subject-focus-title-row">
                  <span className="setup-subject-focus-title">Science</span>
                  <span className="setup-pill-badge green">Active Focus</span>
                </div>
                <p className="setup-card-desc">Get instant step-by-step past paper explanations and smart practice.</p>
              </div>
            </div>

            <div className="setup-remaining-box">
              <span className="setup-section-label">Other subjects coming soon:</span>
              <div className="setup-chips-cloud">
                {REMAINING_SUBJECTS.map((subj) => (
                  <span key={subj} className="setup-subject-chip">
                    {subj}
                  </span>
                ))}
              </div>
            </div>

            <div className="setup-footer">
              <button type="button" className="setup-back-btn" onClick={handleBack}>
                ← Back
              </button>
              <button type="button" className="setup-continue-btn" onClick={handleNext}>
                Continue →
              </button>
            </div>
          </div>
        )}

        {/* SCREEN 5: Learning Preferences */}
        {currentStep === 5 && (
          <div className="setup-body">
            <div className="setup-heading-group">
              <h2 className="setup-main-title">Learning preferences</h2>
              <p className="setup-main-subtitle">Choose a comfortable pace and study goal for your tutor.</p>
            </div>

            <div className="setup-pref-grid">
              {/* 1. Goal */}
              <div className="setup-pref-card">
                <label className="setup-pref-label">Aiming For</label>
                <select
                  className="setup-pref-select"
                  value={studyGoal}
                  onChange={(e) => setStudyGoal(e.target.value)}
                >
                  {AIM_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>

              {/* 2. Weekly Time */}
              <div className="setup-pref-card">
                <label className="setup-pref-label">Weekly Practice</label>
                <select
                  className="setup-pref-select"
                  value={weeklyHours}
                  onChange={(e) => setWeeklyHours(e.target.value)}
                >
                  {WEEKLY_TIME_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>

              {/* 3. Study Time */}
              <div className="setup-pref-card">
                <label className="setup-pref-label">Study Reminders</label>
                <select
                  className="setup-pref-select"
                  value={studyTime}
                  onChange={(e) => setStudyTime(e.target.value)}
                >
                  {NUDGE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>

              {/* 4. Confidence */}
              <div className="setup-pref-card">
                <label className="setup-pref-label">Current Confidence</label>
                <select
                  className="setup-pref-select"
                  value={confidenceLevel}
                  onChange={(e) => setConfidenceLevel(e.target.value)}
                >
                  {FEELING_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="setup-footer">
              <button type="button" className="setup-back-btn" onClick={handleBack}>
                ← Back
              </button>
              <button type="button" className="setup-continue-btn" onClick={handleNext}>
                Continue →
              </button>
            </div>
          </div>
        )}

        {/* SCREEN 6: Review & Confirmation */}
        {currentStep === 6 && (
          <div className="setup-body">
            <div className="setup-heading-group">
              <h2 className="setup-main-title">Review your setup</h2>
              <p className="setup-main-subtitle">You're ready to explore Paperwise. Everything can be adjusted anytime.</p>
            </div>

            <div className="setup-review-simple-card">
              <div className="setup-review-row">
                <span className="setup-review-key">Student Name</span>
                <span className="setup-review-val">{fullName.trim() || 'Student'}</span>
              </div>
              <div className="setup-review-row">
                <span className="setup-review-key">District</span>
                <span className="setup-review-val">{district}</span>
              </div>
              <div className="setup-review-row">
                <span className="setup-review-key">Curriculum</span>
                <span className="setup-review-val">{targetExam} (Grade {grade})</span>
              </div>
              <div className="setup-review-row">
                <span className="setup-review-key">Active Subject</span>
                <span className="setup-review-val" style={{ color: '#00df82' }}>{focusSubject}</span>
              </div>
              <div className="setup-review-row">
                <span className="setup-review-key">Study Goal</span>
                <span className="setup-review-val">{studyGoal}</span>
              </div>
            </div>

            <div className="setup-footer">
              <button
                type="button"
                className="setup-back-btn"
                onClick={handleBack}
                disabled={saving}
              >
                ← Back
              </button>
              <button
                type="button"
                className="setup-continue-btn"
                onClick={handleFinalSubmit}
                disabled={saving}
              >
                {saving ? 'Creating your plan…' : 'Start Learning →'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
