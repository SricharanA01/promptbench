'use client'
import { useState } from 'react'

const MODELS = [
  { id: 'gpt-4o', label: 'GPT-4o', provider: 'OpenAI', color: '#1a73e8', score: 8.4, coding: 9.1, reasoning: 8.6, math: 8.8, latency: 1840, cost: 0.00231 },
  { id: 'gemini', label: 'Gemini 2.5', provider: 'Google', color: '#34a853', score: 7.8, coding: 7.9, reasoning: 8.1, math: 8.3, latency: 1620, cost: 0.00089 },
  { id: 'mistral', label: 'Mistral Large', provider: 'Mistral AI', color: '#7c3aed', score: 7.3, coding: 7.4, reasoning: 7.1, math: 7.8, latency: 980, cost: 0.00078 },
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini', provider: 'OpenAI', color: '#059669', score: 6.9, coding: 7.2, reasoning: 6.8, math: 7.1, latency: 720, cost: 0.000042 },
]

type TopResult = {
  strategy: string
  model: string
  prompt: string
  score: number
  score_reasoning: string
  latency_ms: number
  cost_usd: number
}

type ModelStat = {
  avg_score: number
  best_score: number
}

type OptResult = {
  total_combinations_tested: number
  top_results: TopResult[]
  model_stats: Record<string, ModelStat>
}

export default function Home() {
  const [view, setView] = useState<'leaderboard' | 'optimizer'>('leaderboard')
  const [goal, setGoal] = useState('')
  const [num, setNum] = useState(10)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<OptResult | null>(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState<number | null>(null)
  const [cat, setCat] = useState('overall')

  const getScore = (m: typeof MODELS[0]) => {
    if (cat === 'coding') return m.coding
    if (cat === 'reasoning') return m.reasoning
    if (cat === 'math') return m.math
    return m.score
  }

  const sorted = [...MODELS].sort((a, b) => getScore(b) - getScore(a))

  const run = async () => {
    if (!goal.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await fetch('http://localhost:8000/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, num_variations: num, models: ['gemini', 'mistral'], top_k: 3 })
      })
      setResult(await r.json())
    } catch {
      setError('Cannot connect to backend. Make sure uvicorn is running on port 8000.')
    }
    setLoading(false)
  }

  const copy = (p: string, i: number) => {
    navigator.clipboard.writeText(p)
    setCopied(i)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div style={{ minHeight: '100vh', background: '#fff', color: '#202124', fontFamily: 'Roboto, -apple-system, sans-serif' }}>

      <div style={{ height: 4, background: 'linear-gradient(90deg, #4285f4 25%, #ea4335 50%, #fbbc05 75%, #34a853 100%)' }} />

      <nav style={{ display: 'flex', alignItems: 'center', padding: '0 24px', height: 64, borderBottom: '1px solid #e8eaed', position: 'sticky', top: 0, background: '#fff', zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 32 }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: '#1a73e8', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 15, fontWeight: 700 }}>P</div>
          <span style={{ fontSize: 18, fontWeight: 500, letterSpacing: -0.3 }}>PromptBench</span>
        </div>
        <div style={{ display: 'flex', height: '100%' }}>
          {[{ id: 'leaderboard', label: 'Leaderboard' }, { id: 'optimizer', label: 'Prompt Optimizer' }].map(t => (
            <button key={t.id} onClick={() => setView(t.id as 'leaderboard' | 'optimizer')}
              style={{ height: '100%', padding: '0 20px', border: 'none', borderBottom: view === t.id ? '3px solid #1a73e8' : '3px solid transparent', background: 'none', color: view === t.id ? '#1a73e8' : '#5f6368', fontSize: 14, fontWeight: view === t.id ? 500 : 400, fontFamily: 'inherit', cursor: 'pointer' }}>
              {t.label}
            </button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#34a853' }} />
          <span style={{ fontSize: 12, color: '#5f6368' }}>auto-updates weekly</span>
        </div>
      </nav>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px' }}>

        {view === 'leaderboard' && (
          <div>
            <div style={{ padding: '48px 0 36px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#e8f0fe', borderRadius: 20, padding: '4px 14px', marginBottom: 20 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#1a73e8' }} />
                <span style={{ fontSize: 13, color: '#1967d2', fontWeight: 500 }}>Updated every Sunday · Fully automated</span>
              </div>
              <h1 style={{ fontSize: 44, fontWeight: 700, letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>
                Which LLM wins<br />
                <span style={{ color: '#1a73e8' }}>this week?</span>
              </h1>
              <p style={{ fontSize: 16, color: '#5f6368', maxWidth: 520, lineHeight: 1.7, marginBottom: 36 }}>
                50 production-relevant tasks tested weekly across major models. Scored on accuracy, latency, and cost.
              </p>
              <div style={{ display: 'flex', borderTop: '1px solid #e8eaed', paddingTop: 24 }}>
                {[['12', 'Benchmark runs'], ['3,000', 'API calls made'], ['5', 'Models tracked'], ['50', 'Tasks per run']].map(([val, label], i) => (
                  <div key={label} style={{ paddingRight: 32, marginRight: 32, borderRight: i < 3 ? '1px solid #e8eaed' : 'none' }}>
                    <div style={{ fontSize: 28, fontWeight: 700 }}>{val}</div>
                    <div style={{ fontSize: 13, color: '#5f6368', marginTop: 2 }}>{label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
              {['overall', 'coding', 'reasoning', 'math'].map(c => (
                <button key={c} onClick={() => setCat(c)}
                  style={{ padding: '6px 16px', borderRadius: 20, border: cat === c ? '1px solid #1a73e8' : '1px solid #dadce0', background: cat === c ? '#e8f0fe' : '#fff', color: cat === c ? '#1967d2' : '#5f6368', fontSize: 13, fontFamily: 'inherit', cursor: 'pointer', textTransform: 'capitalize' }}>
                  {c}
                </button>
              ))}
            </div>

            <div style={{ border: '1px solid #e8eaed', borderRadius: 12, overflow: 'hidden', marginBottom: 40, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa' }}>
                    {['Rank', 'Model', 'Score', 'Coding', 'Reasoning', 'Math', 'Latency', 'Cost/task'].map(h => (
                      <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 12, fontWeight: 500, color: '#5f6368', borderBottom: '1px solid #e8eaed', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((m, i) => (
                    <tr key={m.id} style={{ borderBottom: '1px solid #f1f3f4' }}>
                      <td style={{ padding: '16px', fontSize: 14 }}>{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}</td>
                      <td style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ width: 32, height: 32, borderRadius: 8, background: m.color + '22', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, color: m.color }}>{m.label[0]}</div>
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 500 }}>{m.label}</div>
                            <div style={{ fontSize: 12, color: '#5f6368' }}>{m.provider}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '16px', minWidth: 160 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ flex: 1, height: 6, background: '#f1f3f4', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${getScore(m) * 10}%`, height: '100%', background: m.color, borderRadius: 3 }} />
                          </div>
                          <span style={{ fontSize: 13, fontWeight: 500, minWidth: 28 }}>{getScore(m)}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px', fontSize: 13 }}>{m.coding}</td>
                      <td style={{ padding: '16px', fontSize: 13 }}>{m.reasoning}</td>
                      <td style={{ padding: '16px', fontSize: 13 }}>{m.math}</td>
                      <td style={{ padding: '16px', fontSize: 13, color: '#5f6368' }}>{m.latency}ms</td>
                      <td style={{ padding: '16px', fontSize: 13, color: '#5f6368' }}>${m.cost.toFixed(5)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {view === 'optimizer' && (
          <div>
            <div style={{ padding: '48px 0 36px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#fce8e6', borderRadius: 20, padding: '4px 14px', marginBottom: 20 }}>
                <span style={{ fontSize: 13, color: '#c5221f', fontWeight: 500 }}>Powered by Gemini + Mistral</span>
              </div>
              <h1 style={{ fontSize: 44, fontWeight: 700, letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>
                Find the perfect prompt<br />
                <span style={{ color: '#1a73e8' }}>for any goal</span>
              </h1>
              <p style={{ fontSize: 16, color: '#5f6368', maxWidth: 520, lineHeight: 1.7 }}>
                Describe what you want. We test dozens of prompt variations and return the best ones.
              </p>
            </div>

            <div style={{ border: '1px solid #e8eaed', borderRadius: 16, padding: 28, marginBottom: 24, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
              <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 8 }}>What do you want to achieve?</label>
              <textarea value={goal} onChange={e => setGoal(e.target.value)}
                placeholder="e.g. summarize a legal contract and highlight the key risks"
                rows={3}
                style={{ width: '100%', border: '1px solid #dadce0', borderRadius: 8, padding: '12px 16px', fontSize: 15, color: '#202124', fontFamily: 'inherit', resize: 'vertical', lineHeight: 1.6 }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, flexWrap: 'wrap', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 13, color: '#5f6368' }}>Variations:</span>
                  {[5, 10, 20].map(n => (
                    <button key={n} onClick={() => setNum(n)}
                      style={{ padding: '5px 14px', borderRadius: 20, border: num === n ? '1px solid #1a73e8' : '1px solid #dadce0', background: num === n ? '#e8f0fe' : '#fff', color: num === n ? '#1967d2' : '#5f6368', fontSize: 13, fontFamily: 'inherit', cursor: 'pointer' }}>
                      {n}
                    </button>
                  ))}
                </div>
                <button onClick={run} disabled={loading || !goal.trim()}
                  style={{ padding: '10px 28px', borderRadius: 8, border: 'none', background: loading || !goal.trim() ? '#f1f3f4' : '#1a73e8', color: loading || !goal.trim() ? '#9aa0a6' : '#fff', fontSize: 14, fontWeight: 500, fontFamily: 'inherit', cursor: 'pointer' }}>
                  {loading ? 'Optimizing...' : 'Find best prompts'}
                </button>
              </div>
            </div>

            {loading && (
              <div style={{ textAlign: 'center', padding: '64px 0', border: '1px solid #e8eaed', borderRadius: 16 }}>
                <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>Testing {num} prompt variations...</div>
                <div style={{ fontSize: 13, color: '#5f6368' }}>Usually 30 to 60 seconds</div>
              </div>
            )}

            {error && (
              <div style={{ padding: '14px 18px', background: '#fce8e6', border: '1px solid #f5c6c6', borderRadius: 10, color: '#c5221f', fontSize: 14, marginBottom: 24 }}>{error}</div>
            )}

            {result && !loading && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                  <div>
                    <h2 style={{ fontSize: 22, fontWeight: 600 }}>Results</h2>
                    <div style={{ fontSize: 13, color: '#5f6368', marginTop: 2 }}>{result.total_combinations_tested} combinations tested</div>
                  </div>
                  <button onClick={() => setResult(null)} style={{ padding: '6px 14px', border: '1px solid #dadce0', borderRadius: 6, background: '#fff', color: '#5f6368', fontSize: 13, fontFamily: 'inherit', cursor: 'pointer' }}>Try another</button>
                </div>

                {Object.keys(result.model_stats || {}).length > 0 && (
                  <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
                    {Object.entries(result.model_stats).map(([model, stats]) => (
                      <div key={model} style={{ flex: 1, minWidth: 160, padding: '16px 20px', border: '1px solid #e8eaed', borderRadius: 12 }}>
                        <div style={{ fontSize: 12, color: '#5f6368', marginBottom: 6, textTransform: 'capitalize' }}>{model}</div>
                        <div style={{ fontSize: 26, fontWeight: 700 }}>{stats.avg_score}<span style={{ fontSize: 14, fontWeight: 400, color: '#5f6368' }}>/10</span></div>
                        <div style={{ fontSize: 12, color: '#5f6368', marginTop: 2 }}>best: {stats.best_score}/10</div>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {result.top_results.map((r, i) => (
                    <div key={i} style={{ border: i === 0 ? '1px solid #1a73e8' : '1px solid #e8eaed', borderRadius: 14, overflow: 'hidden', boxShadow: i === 0 ? '0 2px 8px rgba(26,115,232,.12)' : 'none' }}>
                      <div style={{ padding: '14px 20px', borderBottom: '1px solid #f1f3f4', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: i === 0 ? '#f8fbff' : '#fafafa', flexWrap: 'wrap', gap: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          {i === 0 && <span style={{ background: '#e8f0fe', color: '#1967d2', fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 12 }}>BEST MATCH</span>}
                          <span style={{ fontSize: 13, color: '#5f6368' }}>#{i + 1} · {r.strategy} · {r.model}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                          <span style={{ fontSize: 18, fontWeight: 700, color: i === 0 ? '#1a73e8' : '#202124' }}>{r.score}/10</span>
                          <span style={{ fontSize: 12, color: '#9aa0a6' }}>{r.latency_ms}ms</span>
                        </div>
                      </div>
                      <div style={{ padding: 20 }}>
                        <div style={{ position: 'relative' }}>
                          <div style={{ background: '#f8f9fa', borderRadius: 8, padding: '14px 16px', paddingRight: 80, fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{r.prompt}</div>
                          <button onClick={() => copy(r.prompt, i)}
                            style={{ position: 'absolute', top: 10, right: 10, padding: '5px 12px', border: '1px solid #dadce0', borderRadius: 6, background: copied === i ? '#e6f4ea' : '#fff', color: copied === i ? '#137333' : '#5f6368', fontSize: 12, fontFamily: 'inherit', cursor: 'pointer' }}>
                            {copied === i ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        {r.score_reasoning && (
                          <div style={{ marginTop: 10, fontSize: 12, color: '#5f6368' }}>
                            <span style={{ fontWeight: 500 }}>Why: </span>{r.score_reasoning}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <footer style={{ borderTop: '1px solid #e8eaed', padding: '24px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 80, flexWrap: 'wrap', gap: 12 }}>
        <span style={{ fontSize: 13, color: '#5f6368' }}>Built by Sricharan Adarasupally </span>
        <div style={{ display: 'flex', gap: 20 }}>
          <a href="https://github.com/SricharanA01/promptbench" style={{ fontSize: 13, color: '#1a73e8', textDecoration: 'none' }}>GitHub</a>
          <a href="https://linkedin.com/in/sricharan-adarasupally" style={{ fontSize: 13, color: '#1a73e8', textDecoration: 'none' }}>LinkedIn</a>
        </div>
      </footer>
    </div>
  )
}