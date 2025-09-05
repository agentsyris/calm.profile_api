import React, { useState } from 'react'
import { submitLead } from '../services/api'

export default function ResultsSection({ results, onRestart }) {
  const { archetype, scores, metrics, recommendations, assessment_id, tagline } = results
  const rows = ['architect', 'conductor', 'curator', 'craftsperson']
  const mix = archetype?.mix || {}
  
  return (
    <section className="results-section active">
      <h1>assessment complete<span className="dot">.</span></h1>
      <div style={{
        margin: '8px 0 6px', 
        fontFamily: "'JetBrains Mono'", 
        fontSize: 12, 
        letterSpacing: '0.14em', 
        textTransform: 'uppercase', 
        color: 'var(--gray-400)'
      }}>
        your archetype
      </div>
      <div className="profile-type">the {archetype.primary}</div>
      <p className="profile-tagline">{tagline || ''}</p>
      
      {archetype?.mix && (
        <div className="detail-section">
          <h3 className="detail-title">archetype blend</h3>
          <div>
            {rows.map((k) => (
              <div key={k} style={{
                display: 'grid', 
                gridTemplateColumns: '110px 1fr 40px', 
                alignItems: 'center', 
                gap: 8, 
                margin: '6px 0'
              }}>
                <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>{k}</div>
                <div style={{
                  height: 6, 
                  background: 'var(--gray-100)', 
                  borderRadius: 4, 
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${mix[k] || 0}%`, 
                    height: '100%', 
                    background: 'var(--black)'
                  }}/>
                </div>
                <div style={{
                  fontFamily: "'JetBrains Mono'", 
                  fontSize: 12, 
                  textAlign: 'right'
                }}>
                  {mix[k] || 0}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div className="metrics-grid">
        <div className="metric">
          <div className="metric-value">{Math.round(scores.overhead_index)}%</div>
          <div className="metric-label">overhead</div>
        </div>
        <div className="metric">
          <div className="metric-value">{metrics.hours_lost_ppw}</div>
          <div className="metric-label">hrs/week</div>
        </div>
        <div className="metric">
          <div className="metric-value">${Math.round(metrics.annual_cost / 1000)}k</div>
          <div className="metric-label">cost/year</div>
        </div>
      </div>
      
      <div className="detail-section">
        <h3 className="detail-title">operational strengths</h3>
        <div>
          {recommendations.strengths.map((s, i) => (
            <div key={i} className="detail-item">{s}</div>
          ))}
        </div>
      </div>
      
      <div className="detail-section">
        <h3 className="detail-title">preview quick win</h3>
        <div>
          <div className="detail-item">{recommendations.quick_wins?.[0]}</div>
        </div>
      </div>
      
      <div className="detail-section">
        <h3 className="detail-title">technology stack</h3>
        <div style={{ 
          fontFamily: "'JetBrains Mono'", 
          fontSize: 12, 
          color: 'var(--gray-600)' 
        }}>
          {Array.isArray(recommendations.tool_stack) 
            ? recommendations.tool_stack.join(' · ') 
            : null}
        </div>
      </div>
      
      <div className="detail-section">
        <h3 className="detail-title">get your full diagnostic ($495)</h3>
        <EmailCapture assessmentId={assessment_id} />
      </div>
      
      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <button 
          className="btn btn-secondary" 
          onClick={onRestart} 
          style={{ fontSize: 11 }}
        >
          retake assessment
        </button>
      </div>
    </section>
  )
}

function EmailCapture({ assessmentId }) {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState(null)
  
  const handleSubmit = async () => {
    try {
      setSubmitting(true)
      setError(null)
      
      const response = await submitLead(email, assessmentId)
      
      if (response.success) {
        setSubmitted(true)
      } else {
        throw new Error(response.error || 'Submission failed')
      }
    } catch (e) {
      setError(e.message || 'Failed to submit')
    } finally {
      setSubmitting(false)
    }
  }
  
  if (submitted) {
    return (
      <div style={{
        padding: '20px',
        background: 'var(--gray-50)',
        borderRadius: '4px',
        textAlign: 'center'
      }}>
        <div style={{
          fontSize: '16px',
          marginBottom: '8px',
          color: 'var(--primary)'
        }}>
          ✓ Check your email
        </div>
        <div style={{
          fontSize: '12px',
          color: 'var(--gray-600)'
        }}>
          We've sent your assessment results and information about the full report to {email}
        </div>
      </div>
    )
  }
  
  return (
    <>
      <input 
        type="email" 
        placeholder="work email" 
        value={email} 
        onChange={(e) => setEmail(e.target.value)} 
        style={{
          width: '100%',
          padding: '10px 12px',
          border: '1px solid var(--gray-200)',
          borderRadius: 4,
          marginBottom: 12,
          fontSize: '14px'
        }}
        disabled={submitting}
      />
      
      <button 
        className="btn" 
        disabled={!email || submitting} 
        onClick={handleSubmit}
        style={{
          width: '100%',
          opacity: (!email || submitting) ? 0.5 : 1,
          cursor: (!email || submitting) ? 'not-allowed' : 'pointer'
        }}
      >
        {submitting ? 'submitting...' : 'get the report →'}
      </button>
      
      {error && (
        <div style={{
          marginTop: 12,
          color: 'red',
          fontSize: '12px'
        }}>
          {error}
        </div>
      )}
      
      <div style={{
        marginTop: 8,
        fontSize: 12,
        color: 'var(--gray-400)'
      }}>
        you'll receive a preview of your results via email with a link to purchase the full report
      </div>
    </>
  )
}