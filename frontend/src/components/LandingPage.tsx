import { useState } from 'react'
import './LandingPage.css'

interface LandingPageProps {
  onGetStarted: () => void
  onLogin: () => void
}

function BookBrandIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  )
}

function DocumentIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  )
}

function PlayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function GithubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
    </svg>
  )
}

function TwitterIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z" />
    </svg>
  )
}

function GlobeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  )
}

export function LandingPage({ onGetStarted, onLogin }: LandingPageProps) {
  const [demoInput, setDemoInput] = useState('')
  const [demoMessages, setDemoMessages] = useState<Array<{ sender: 'user' | 'ai'; text: string; rubric?: string[] }>>([
    {
      sender: 'user',
      text: 'Can you explain why we use friction force instead of gravitational component here?',
    },
    {
      sender: 'ai',
      text: 'Excellent question. Since the block remains "stationary" (in static equilibrium), the static friction force exactly balances the component of gravitational force pulling the block down the incline. Thus, F_f = m*g*sin(θ). Here is the step-by-step breakdown according to the 2023 AP Rubric:',
      rubric: [
        '1. Draw free-body diagram mapping Normal (N) and Gravitational (mg).',
        '2. Solve for μ_s where max static friction balances slope gravity.',
      ],
    },
  ])

  const handleDemoSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const query = demoInput.trim()
    if (!query) return

    setDemoMessages((prev) => [
      ...prev,
      { sender: 'user', text: query },
      {
        sender: 'ai',
        text: `According to marking scheme criteria: Relevant formula applied F_net = 0. Substituting static equilibrium parameters yields μ_s = tan(θ). Full points awarded for identifying normal force component N = m*g*cos(θ).`,
      },
    ])
    setDemoInput('')
  }

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <div className="landing-wrapper">
      <div className="landing-mesh-bg" />

      {/* ================= HEADER / NAVIGATION ================= */}
      <header className="landing-container">
        <nav className="landing-navbar" aria-label="Main Navigation">
          <a href="#" className="landing-brand">
            <span className="landing-brand-icon">
              <BookBrandIcon />
            </span>
            <span>Paperwise</span>
          </a>

          <ul className="landing-nav-links">
            <li>
              <a href="#features" onClick={(e) => { e.preventDefault(); scrollToSection('features') }}>
                Features
              </a>
            </li>
            <li>
              <a href="#how-it-works" onClick={(e) => { e.preventDefault(); scrollToSection('how-it-works') }}>
                How it Works
              </a>
            </li>
            <li>
              <a href="#pricing" onClick={(e) => { e.preventDefault(); scrollToSection('pricing') }}>
                Pricing
              </a>
            </li>
          </ul>

          <div className="landing-nav-actions">
            <button type="button" className="landing-btn-ghost" onClick={onLogin}>
              Sign In
            </button>
            <button type="button" className="landing-btn-white-pill" onClick={onGetStarted}>
              Get Started Free
            </button>
          </div>
        </nav>
      </header>

      {/* ================= HERO SECTION ================= */}
      <main>
        <section className="landing-container landing-hero">
          <div className="landing-announcement-badge">
            <span>INTRODUCING PAPERWISE 2.0</span>
          </div>

          <h1 className="landing-hero-title">
            Study Smarter. Dominate Your<br className="hero-title-break" />
            Past Papers with AI.
          </h1>

          <p className="landing-hero-desc">
            The RAG-powered AI past paper tutor. Upload past exams, query topics instantly, map trends, and get precise, marking-scheme-focused answers.
          </p>

          <div className="landing-hero-actions">
            <button type="button" className="landing-btn-primary" onClick={onGetStarted}>
              Start Studying Free
            </button>
            <button
              type="button"
              className="landing-btn-outline"
              onClick={() => scrollToSection('workspace-demo')}
            >
              <PlayIcon />
              <span>Watch Live Demo</span>
            </button>
          </div>

          {/* Key Metrics Bar */}
          <div className="landing-stats-bar">
            <div className="landing-stat-item">
              <span className="landing-stat-number">1.2M+</span>
              <span className="landing-stat-label">Papers Analyzed</span>
            </div>
            <div className="landing-stat-item">
              <span className="landing-stat-number">15M+</span>
              <span className="landing-stat-label">Questions Answered</span>
            </div>
            <div className="landing-stat-item">
              <span className="landing-stat-number">450k+</span>
              <span className="landing-stat-label">Global Students</span>
            </div>
            <div className="landing-stat-item">
              <span className="landing-stat-number">94.6%</span>
              <span className="landing-stat-label">Accuracy Score</span>
            </div>
          </div>
        </section>

        {/* ================= CORE CAPABILITIES (BENTO GRID) ================= */}
        <section id="features" className="landing-container landing-section">
          <span className="landing-section-tag">CORE CAPABILITIES</span>
          <h2 className="landing-section-title">Powering Smarter Preparation</h2>

          <div className="capabilities-grid">
            <div className="capabilities-card">
              <span className="capabilities-tag">01 / ASK AI</span>
              <h3 className="capabilities-title">Query Any Past Paper</h3>
              <p className="capabilities-desc">
                Ask natural language questions directly about exam sheets. AI instantly points you to relevant chapters, formulas, and exact marking criteria.
              </p>
            </div>

            <div className="capabilities-card">
              <span className="capabilities-tag">02 / VECTOR MATCH</span>
              <h3 className="capabilities-title">Find Similar Questions</h3>
              <p className="capabilities-desc">
                Uncover parallel questions across historical exams. Master specific problem patterns through automated semantic matching engines.
              </p>
            </div>

            <div className="capabilities-card">
              <span className="capabilities-tag">03 / TREND MATRIX</span>
              <h3 className="capabilities-title">Topic Frequency Analysis</h3>
              <p className="capabilities-desc">
                View historical heatmaps mapping out how frequently specific modules occur. Never get surprised by unexpected recurring questions.
              </p>
            </div>
          </div>

          <div className="capabilities-grid-row-2">
            <div className="capabilities-card">
              <span className="capabilities-tag">04 / VALUE WEIGHT</span>
              <h3 className="capabilities-title">Topic Importance Ranking</h3>
              <p className="capabilities-desc">
                Algorithmic ranking systems mapping the mark value density per page. Dedicate your limited revision time to high-yield sections first.
              </p>
            </div>

            <div className="capabilities-card">
              <span className="capabilities-tag">05 / GENERATIVE EXAMS</span>
              <h3 className="capabilities-title">Similar Practice Problems</h3>
              <p className="capabilities-desc">
                Generate custom AI practice papers mathematically mapped to the structural weight, difficulty, and phrasing of the target syllabus.
              </p>
            </div>
          </div>
        </section>

        {/* ================= SIMULATED RAG CHAT WORKSPACE ================= */}
        <section id="workspace-demo" className="landing-container landing-section">
          <span className="landing-section-tag center">THE CORE ENGINE</span>
          <h2 className="landing-section-title center">Simulated RAG Chat Workspace</h2>

          <div className="workspace-mockup-wrapper">
            {/* Left: Document & Retrieved Sources */}
            <div className="workspace-doc-pane">
              <div className="workspace-doc-header">
                <div className="workspace-doc-title">
                  <DocumentIcon />
                  <span>AP_Physics_C_2023.pdf</span>
                </div>
                <span className="workspace-doc-page">PAGE 4 OF 22</span>
              </div>

              <div className="workspace-question-box">
                <div className="workspace-question-num">QUESTION 3 (15 POINTS)</div>
                <p className="workspace-question-text">
                  A block of mass m is placed on a rough plane inclined at an angle θ. If the block remains stationary, derive the expression for the minimum coefficient of static friction μ_s.
                </p>
              </div>

              <div className="workspace-sources-wrap">
                <span className="workspace-sources-label">RETRIEVED CONTEXT SOURCES</span>

                <div className="workspace-source-row">
                  <span className="workspace-source-name">AP Marking Scheme 2021</span>
                  <span className="workspace-source-badge">90% Similarity Match</span>
                </div>

                <div className="workspace-source-row">
                  <span className="workspace-source-name">MIT Mech-Eng Lesson 4</span>
                  <span className="workspace-source-badge">84% Topic Overlap</span>
                </div>
              </div>
            </div>

            {/* Right: Conversational AI Tutor Chat */}
            <div className="workspace-chat-pane">
              <div className="workspace-chat-messages">
                {demoMessages.map((msg, idx) => (
                  <div key={idx} className="workspace-msg">
                    <div className={`workspace-avatar ${msg.sender === 'user' ? 'user' : 'ai'}`}>
                      {msg.sender === 'user' ? 'U' : 'P'}
                    </div>
                    <div className="workspace-msg-content">
                      <span className="workspace-msg-sender">
                        {msg.sender === 'user' ? 'Student Query' : 'Paperwise AI Tutor'}
                      </span>
                      <p className="workspace-msg-text">{msg.text}</p>
                      {msg.rubric && (
                        <ul className="workspace-msg-list">
                          {msg.rubric.map((item, rIdx) => (
                            <li key={rIdx}>{item}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <form className="workspace-chat-input-bar" onSubmit={handleDemoSubmit}>
                <input
                  type="text"
                  placeholder="Ask a follow-up, or click on a section of the marking scheme..."
                  value={demoInput}
                  onChange={(e) => setDemoInput(e.target.value)}
                />
                <button type="submit" className="workspace-chat-submit-btn">
                  Ask AI
                </button>
              </form>
            </div>
          </div>
        </section>

        {/* ================= STUDY WORKFLOW SECTION ================= */}
        <section id="how-it-works" className="landing-container landing-section">
          <span className="landing-section-tag center">STRESS-FREE STUDY WORKFLOW</span>
          <h2 className="landing-section-title center">How Paperwise Transforms Study Sessions</h2>

          <div className="workflow-grid">
            <div className="workflow-card">
              <div className="workflow-number">01</div>
              <h3 className="workflow-title">Upload Past Papers</h3>
              <p className="workflow-desc">
                Drag and drop standard exam PDFs. Paperwise automatically parses the text, diagrams, and structures.
              </p>
            </div>

            <div className="workflow-card">
              <div className="workflow-number">02</div>
              <h3 className="workflow-title">Target & Analyze</h3>
              <p className="workflow-desc">
                Isolate specific topics or select our AI syllabus mapping. Our engine calculates topic trends instantly.
              </p>
            </div>

            <div className="workflow-card">
              <div className="workflow-number">03</div>
              <h3 className="workflow-title">Execute Focused Drills</h3>
              <p className="workflow-desc">
                Engage in RAG conversational chat or execute mock-up drills based directly on the actual marking scheme.
              </p>
            </div>
          </div>
        </section>

        {/* ================= TESTIMONIALS SECTION ================= */}
        <section className="landing-container landing-section">
          <span className="landing-section-tag">STUDENT SUCCESS STORIES</span>
          <h2 className="landing-section-title">Loved by ambitious scholars worldwide</h2>

          <div className="testimonials-grid">
            <div className="testimonial-card">
              <p className="testimonial-quote">
                "Paperwise literally cut my revision time in half. Instead of flipping through 10 years of paper folders, I just query the specific equations."
              </p>
              <div>
                <span className="testimonial-author-name">Sophia Martinez</span>
                <span className="testimonial-author-cred">A-LEVEL PHYSICS / 4A* ACHIEVER</span>
              </div>
            </div>

            <div className="testimonial-card">
              <p className="testimonial-quote">
                "The generative mock exam feature matched the real AP Chemistry syllabus format exactly. I scored a 5 with absolute confidence."
              </p>
              <div>
                <span className="testimonial-author-name">Liam Henderson</span>
                <span className="testimonial-author-cred">AP CHEMISTRY STUDENT</span>
              </div>
            </div>

            <div className="testimonial-card">
              <p className="testimonial-quote">
                "The marking scheme breakdown is brilliant. It teaches you how to answer specifically for the points, rather than writing paragraphs."
              </p>
              <div>
                <span className="testimonial-author-name">Nikhil Sharma</span>
                <span className="testimonial-author-cred">IB MATHEMATICS HL CANDIDATE</span>
              </div>
            </div>
          </div>
        </section>

        {/* ================= PRICING SECTION ================= */}
        <section id="pricing" className="landing-container landing-section">
          <span className="landing-section-tag center">SIMPLE PLANS</span>
          <h2 className="landing-section-title center">Investment in Academic Performance</h2>

          <div className="pricing-grid">
            {/* Free Tier */}
            <div className="pricing-card">
              <h3 className="pricing-plan-title">Free Tier</h3>
              <p className="pricing-plan-subtitle">
                Perfect for casual study prep and evaluating core features.
              </p>
              <div className="pricing-price-wrap">
                <span className="pricing-amount">$0</span>
                <span className="pricing-period">/ forever</span>
              </div>
              <button type="button" className="pricing-cta-btn outline" onClick={onGetStarted}>
                Get Started Free
              </button>

              <div className="pricing-features-heading">WHAT'S INCLUDED</div>
              <ul className="pricing-features-list">
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Upload up to 3 past papers</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>50 AI queries per month</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Basic RAG context matching</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Topic frequency matrices</span>
                </li>
              </ul>
            </div>

            {/* Pro Scholar */}
            <div className="pricing-card featured">
              <div className="pricing-featured-badge">MOST POPULAR</div>
              <h3 className="pricing-plan-title">Pro Scholar</h3>
              <p className="pricing-plan-subtitle">
                Complete suite of analysis and unlimited RAG queries.
              </p>
              <div className="pricing-price-wrap">
                <span className="pricing-amount">$12</span>
                <span className="pricing-period">/ month</span>
              </div>
              <button type="button" className="pricing-cta-btn primary" onClick={onGetStarted}>
                Upgrade to Pro Scholar
              </button>

              <div className="pricing-features-heading">WHAT'S INCLUDED</div>
              <ul className="pricing-features-list">
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Unlimited past paper uploads</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Unlimited AI questions & explanations</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Advanced generative practice exams</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Step-by-step marking scheme analysis</span>
                </li>
                <li>
                  <span className="pricing-check"><CheckIcon /></span>
                  <span>Priority GPU speed priority</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* ================= FINAL CTA SECTION ================= */}
        <section className="landing-container landing-final-cta">
          <div className="final-cta-card">
            <h2 className="final-cta-title">Take the Stress Out of Past Paper Prep Today</h2>
            <p className="final-cta-desc">
              Join thousands of students who have replaced traditional memorization directories with deep, syllabus-focused semantic engines.
            </p>
            <button type="button" className="landing-btn-cta-green" onClick={onGetStarted}>
              Get Started Free Now
            </button>
          </div>
        </section>
      </main>

      {/* ================= FOOTER ================= */}
      <footer className="landing-container landing-footer">
        <div className="landing-footer-grid">
          <div className="footer-brand-wrap">
            <a href="#" className="landing-brand">
              <span className="landing-brand-icon">
                <BookBrandIcon />
              </span>
              <span>Paperwise</span>
            </a>
            <p className="footer-desc">
              Providing modern, accessible semantic research systems designed to raise academic success across schools.
            </p>
          </div>

          <div className="footer-nav-col">
            <span className="footer-col-title">PRODUCT</span>
            <a href="#features" onClick={(e) => { e.preventDefault(); scrollToSection('features') }}>Features</a>
            <a href="#pricing" onClick={(e) => { e.preventDefault(); scrollToSection('pricing') }}>Pricing</a>
            <a href="#workspace-demo" onClick={(e) => { e.preventDefault(); scrollToSection('workspace-demo') }}>Demo Video</a>
            <a href="#">Security</a>
          </div>

          <div className="footer-nav-col">
            <span className="footer-col-title">RESOURCES</span>
            <a href="#">Syllabus Map</a>
            <a href="#">Documentation</a>
            <a href="#">FAQ</a>
            <a href="#">Blog</a>
          </div>

          <div className="footer-nav-col">
            <span className="footer-col-title">LEGAL</span>
            <a href="#">Terms of Use</a>
            <a href="#">Privacy Policy</a>
            <a href="#">SLA</a>
            <a href="#">Responsible AI</a>
          </div>
        </div>

        <div className="landing-footer-bottom">
          <p className="footer-copyright">© 2026 Paperwise Inc. All rights reserved.</p>
          <div className="footer-socials">
            <a href="https://github.com" target="_blank" rel="noreferrer" className="footer-social-link" aria-label="GitHub">
              <GithubIcon />
            </a>
            <a href="https://twitter.com" target="_blank" rel="noreferrer" className="footer-social-link" aria-label="Twitter">
              <TwitterIcon />
            </a>
            <a href="#" className="footer-social-link" aria-label="Website">
              <GlobeIcon />
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
