import { useEffect, useState } from 'react';
import { fetchSkills, postResearch } from '../services/api';

export default function Research() {
  const [skills, setSkills] = useState<any[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string>('elite-ipo');
  const [prompt, setPrompt] = useState('Identify the next emerging consumer trend in Southeast Asia.');
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSkills()
      .then((result) => setSkills(result.skills))
      .catch((err) => setError(err.message));
  }, []);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const result = await postResearch({ skill_id: selectedSkill, prompt });
      setResponse(result.result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Research Lab</h2>
        <p>Select from research skills and build an analysis prompt.</p>
      </div>

      <div className="research-panel">
        <label>
          Select skill
          <select value={selectedSkill} onChange={(event) => setSelectedSkill(event.target.value)}>
            {skills.map((skill) => (
              <option key={skill.id} value={skill.id}>
                {skill.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Prompt
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
        </label>

        <button type="button" onClick={handleSubmit} disabled={loading}>
          {loading ? 'Submitting...' : 'Run Research'}
        </button>

        {error && <p className="error-message">{error}</p>}
        {response && (
          <div className="research-response">
            <h3>Research Result</h3>
            <p>{response}</p>
          </div>
        )}
      </div>
    </div>
  );
}
