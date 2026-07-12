import { useEffect, useMemo, useState } from 'react';
import { fetchDashboard, fetchSkills, postResearch } from '../services/api';

const SKILLS = [
  { id: 'elite-ipo', label: 'Elite IPO & Equity Research' },
  { id: 'market-analysis', label: 'Market Analysis' },
  { id: 'future-prediction', label: 'Future Prediction' },
  { id: 'hidden-gem-finder', label: 'Hidden Gem Finder' },
  { id: 'ai-investment-thesis', label: 'AI Investment Thesis' },
  { id: 'geopolitics-risk', label: 'Geopolitics & Risk' },
  { id: 'commodity-insights', label: 'Commodity Insights' },
  { id: 'retail-consumer-growth', label: 'Retail & Consumer Growth' },
  { id: 'portfolio-resilience', label: 'Portfolio Resilience' },
  { id: 'capital-markets-strategy', label: 'Capital Markets Strategy' },
];

export default function Dashboard() {
  const [selectedSkills, setSelectedSkills] = useState<string[]>(['elite-ipo']);
  const [prompt, setPrompt] = useState('Analyze the top company opportunities in Malaysian IPOs for the next 12 months.');
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([
    { role: 'assistant', text: 'Welcome to Praesagus. Select skills and ask your research question.' },
  ]);
  const [summary, setSummary] = useState<any>(null);
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchDashboard(), fetchSkills()])
      .then(([dashboardResult, skillsResult]) => {
        setSummary(dashboardResult.summary);
        setSkills(skillsResult.skills);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const skillPreview = useMemo(() => {
    if (!selectedSkills.length) {
      return 'No skills selected. Pick at least one skill to guide the analysis.';
    }
    return `Using skills: ${selectedSkills
      .map((id) => skills.find((skill) => skill.id === id)?.label ?? id)
      .join(', ')}.`;
  }, [selectedSkills, skills]);

  async function sendMessage() {
    if (!prompt.trim()) return;
    const userMessage = { role: 'user' as const, text: prompt };
    setMessages((prev) => [...prev, userMessage]);
    setPrompt('');
    try {
      const payload = { skill_id: selectedSkills[0], prompt, tickers: [], context: '' };
      const response = await postResearch(payload);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `Research request queued: ${response.request_id}. ${response.result}`,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `Research request failed: ${err.message}`,
        },
      ]);
    }
  }

  const trendCards = summary?.top_trends ?? [];

  return (
    <div className="dashboard-page">
      <section className="dashboard-top">
        <div>
          <h2>Dashboard</h2>
          <p>Live signal summaries, chart data, and platform health snapshots.</p>
        </div>
        <div className="dashboard-stats">
          <div className="stat-card">
            <span>{summary?.signal_count ?? '—'}</span>
            <p>Signals tracked</p>
          </div>
          <div className="stat-card">
            <span>{summary?.platform_count ?? '—'}</span>
            <p>Connected platforms</p>
          </div>
          <div className="stat-card">
            <span>{summary?.feature_store ?? 'unknown'}</span>
            <p>Feature store</p>
          </div>
        </div>
      </section>

      {loading && <p>Loading dashboard...</p>}
      {error && <p className="error-message">{error}</p>}

      <section className="trend-overview">
        <h3>Top trends</h3>
        <div className="cards-grid">
          {trendCards.map((trend: any) => (
            <div key={trend.entity} className="trend-card">
              <div className="trend-card-header">
                <h3>{trend.entity}</h3>
                <span className="trend-score">{trend.score.toFixed(2)}</span>
              </div>
              <p>{trend.evidence?.length ?? 0} evidence sources</p>
              <div className="trend-tags">
                <span>Mentions: {trend.mention_count}</span>
                <span>Last seen: {trend.last_seen ?? 'n/a'}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="chart-summary">
        <h3>Dashboard charts</h3>
        <div className="chart-grid">
          <div className="chart-card">
            <h4>Score breakdown</h4>
            <pre>{JSON.stringify(summary?.chart_data?.score_breakdown ?? [], null, 2)}</pre>
          </div>
          <div className="chart-card">
            <h4>Mention breakdown</h4>
            <pre>{JSON.stringify(summary?.chart_data?.mention_breakdown ?? [], null, 2)}</pre>
          </div>
        </div>
      </section>

      <section className="skill-panel">
        <h3>Select analysis skills</h3>
        <div className="skill-grid">
          {SKILLS.map((skill) => (
            <button
              key={skill.id}
              type="button"
              className={selectedSkills.includes(skill.id) ? 'skill-chip selected' : 'skill-chip'}
              onClick={() => {
                setSelectedSkills((current) =>
                  current.includes(skill.id) ? current.filter((item) => item !== skill.id) : [...current, skill.id],
                );
              }}
            >
              {skill.label}
            </button>
          ))}
        </div>
      </section>

      <section className="chat-section">
        <div className="skill-summary">{skillPreview}</div>
        <div className="chat-panel">
          <div className="messages">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.role}`}>
                <div className="message-role">{message.role === 'assistant' ? 'Assistant' : 'You'}</div>
                <div className="message-text">{message.text}</div>
              </div>
            ))}
          </div>
          <div className="prompt-area">
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Enter your research prompt here..."
            />
            <button onClick={sendMessage} className="send-button">
              Send
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
