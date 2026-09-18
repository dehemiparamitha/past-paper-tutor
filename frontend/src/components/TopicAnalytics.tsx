import { useState, useEffect } from 'react'
import type { ImportantTopic, TopicTrend } from '../types/api'
import { fetchImportantTopics, fetchTopicTrends } from '../services/api'

interface TopicAnalyticsProps {
  onPracticeTopic: (topicName: string) => void
}

function formatTopicName(name: string): string {
  if (!name) return ''
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function TopicAnalytics({ onPracticeTopic }: TopicAnalyticsProps) {
  const [topics, setTopics] = useState<ImportantTopic[]>([])
  const [trends, setTrends] = useState<TopicTrend[]>([])
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'grade10' | 'grade11' | 'high' | 'rising'>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      setIsLoading(true)
      setError(null)
      try {
        const [importantRes, trendsRes] = await Promise.all([
          fetchImportantTopics(),
          fetchTopicTrends(),
        ])
        setTopics(importantRes)
        setTrends(trendsRes)
      } catch {
        setError('Could not connect to backend. Please check if the server is running.')
      } finally {
        setIsLoading(false)
      }
    }
    void loadData()
  }, [])

  const trendsMap = new Map(trends.map((t) => [t.topic.toLowerCase(), t]))

  const highCount = topics.filter((t) => t.tier === 'High').length
  const risingCount = trends.filter((t) => t.trend === 'rising').length
  const grade10Count = topics.filter((t) => (t.grade ?? 10) === 10).length
  const grade11Count = topics.filter((t) => t.grade === 11).length

  const filteredTopics = topics.filter((t) => {
    const trend = trendsMap.get(t.topic.toLowerCase())
    if (filter === 'grade10' && (t.grade ?? 10) !== 10) return false
    if (filter === 'grade11' && t.grade !== 11) return false
    if (filter === 'high' && t.tier !== 'High') return false
    if (filter === 'rising' && trend?.trend !== 'rising') return false
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      if (!t.topic.toLowerCase().includes(q) && !t.subject_area.toLowerCase().includes(q)) return false
    }
    return true
  })

  const toggleExpand = (topicKey: string) => {
    setExpandedTopic((prev) => (prev === topicKey ? null : topicKey))
  }

  return (
    <div className="topic-analytics-page">
      {/* Header */}
      <div className="analytics-hero">
        <h1>Topic Analytics</h1>
        <p className="analytics-intro">
          Official G.C.E. O/L Science syllabus topics ranked by frequency, recency, and exam weight.
        </p>
      </div>

      {/* Controls */}
      <div className="analytics-bar">
        <div className="search-field">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m20 20-4.5-4.5m2-5.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" />
          </svg>
          <input
            type="text"
            placeholder="Search topics or subjects…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button type="button" className="clear-search-btn" onClick={() => setSearchQuery('')}>
              ×
            </button>
          )}
        </div>

        <div className="filter-options">
          <button
            type="button"
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All ({topics.length})
          </button>
          <button
            type="button"
            className={filter === 'grade10' ? 'active' : ''}
            onClick={() => setFilter('grade10')}
          >
            Grade 10 ({grade10Count})
          </button>
          <button
            type="button"
            className={filter === 'grade11' ? 'active' : ''}
            onClick={() => setFilter('grade11')}
          >
            Grade 11 ({grade11Count})
          </button>
          <button
            type="button"
            className={filter === 'high' ? 'active' : ''}
            onClick={() => setFilter('high')}
          >
            High Priority ({highCount})
          </button>
          <button
            type="button"
            className={filter === 'rising' ? 'active' : ''}
            onClick={() => setFilter('rising')}
          >
            Trending ({risingCount})
          </button>
        </div>
      </div>

      {error && <div className="analytics-error-message">{error}</div>}

      {isLoading ? (
        <div className="analytics-loading-wrap">
          <p>Loading topics…</p>
        </div>
      ) : filteredTopics.length === 0 ? (
        <div className="analytics-empty-wrap">
          <p>No topics found{searchQuery ? ` for "${searchQuery}"` : ''}.</p>
          {(searchQuery || filter !== 'all') && (
            <button
              type="button"
              className="topic-practice-button"
              style={{ marginTop: 12 }}
              onClick={() => { setSearchQuery(''); setFilter('all') }}
            >
              Show all topics
            </button>
          )}
        </div>
      ) : (
        <div className="topic-list">
          {filteredTopics.map((item) => {
            const trend = trendsMap.get(item.topic.toLowerCase())
            const name = formatTopicName(item.topic)
            const isExpanded = expandedTopic === item.topic
            const itemGrade = item.grade ?? (trend?.grade ?? 10)
            const subjArea = item.subject_area || trend?.subject_area || 'general'

            const trendLabel =
              trend?.trend === 'rising'
                ? '↑ Trending up'
                : trend?.trend === 'declining'
                  ? '↓ Declining'
                  : '→ Stable'

            const trendClass =
              trend?.trend === 'rising' ? 'rising' : trend?.trend === 'declining' ? 'declining' : 'stable'

            const priorityLabel =
              item.tier === 'High' ? 'High priority' : item.tier === 'Moderate' ? 'Medium' : 'Standard'

            // Year breakdown from trend data
            const yearBreakdown = trend?.yearly_breakdown
              ? Object.entries(trend.yearly_breakdown).sort(([a], [b]) => Number(b) - Number(a))
              : null

            return (
              <div key={item.topic} className={`topic-item ${isExpanded ? 'expanded' : ''}`}>
                {/* Collapsed row — always visible */}
                <button
                  type="button"
                  className="topic-row-btn"
                  onClick={() => toggleExpand(item.topic)}
                  aria-expanded={isExpanded}
                >
                  <div className="topic-row-left">
                    <span className="topic-name">{name}</span>
                    <span className="grade-chip">Gr {itemGrade}</span>
                    <span className={`subject-chip ${subjArea.toLowerCase()}`}>
                      {formatTopicName(subjArea)}
                    </span>
                    <span className={`priority-chip ${item.tier.toLowerCase()}`}>{priorityLabel}</span>
                  </div>
                  <div className="topic-row-right">
                    <span className="topic-count-label">{item.total_questions} q's</span>
                    <span className={`trend-chip ${trendClass}`}>{trendLabel}</span>
                    <span className="expand-chevron">{isExpanded ? '▴' : '▾'}</span>
                  </div>
                </button>

                {/* Expanded detail — only when open */}
                {isExpanded && (
                  <div className="topic-detail-panel">
                    <div className="topic-detail-grid">
                      <div className="detail-cell">
                        <span className="detail-label">Grade</span>
                        <span className="detail-value">Grade {itemGrade}</span>
                      </div>
                      <div className="detail-cell">
                        <span className="detail-label">Subject area</span>
                        <span className="detail-value">{formatTopicName(subjArea)}</span>
                      </div>
                      <div className="detail-cell">
                        <span className="detail-label">Questions</span>
                        <span className="detail-value">{item.total_questions}</span>
                      </div>
                      <div className="detail-cell">
                        <span className="detail-label">Years appeared</span>
                        <span className="detail-value">{item.years_appeared} of {item.total_years_evaluated}</span>
                      </div>
                      <div className="detail-cell">
                        <span className="detail-label">Importance score</span>
                        <span className="detail-value">{item.importance_score.toFixed(1)}</span>
                      </div>
                    </div>

                    {yearBreakdown && yearBreakdown.length > 0 && (
                      <div className="year-breakdown">
                        <span className="detail-label">By year</span>
                        <div className="year-chips">
                          {yearBreakdown.map(([year, count]) => (
                            <span key={year} className="year-chip">
                              {year} <strong>{count}</strong>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="topic-detail-actions">
                      <button
                        type="button"
                        className="topic-practice-button"
                        onClick={() => onPracticeTopic(name)}
                      >
                        Practice questions on {name} →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
