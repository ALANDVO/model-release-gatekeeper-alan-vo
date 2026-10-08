import React, { useState } from 'react';
import { api } from '../api/client';
import { Evaluation, LLMAdvisoryResponse } from '../api/types';

export const LLMAdvisoryPanel: React.FC<{ evaluation: Evaluation }> = ({ evaluation }) => {
  const [advisory, setAdvisory] = useState<LLMAdvisoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getLLMAdvisory(evaluation.id);
      setAdvisory(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: '0.75rem', border: '1px solid #4f46e5', backgroundColor: 'rgba(79, 70, 229, 0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <strong style={{ fontSize: '0.9rem' }}>AI Release Risk Advisory</strong>
            <span className="badge badge-blue">Opt-In Advisory</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Grounded metrics advisory. Deterministic gates prevail.</span>
        </div>
        {!advisory && !loading && (
          <button className="btn btn-secondary btn-sm" onClick={handleFetch}>Generate Advisory</button>
        )}
      </div>

      {loading && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Generating advisory...</div>}
      {error && <div style={{ fontSize: '0.8rem', color: '#fb7185', marginTop: '0.5rem' }}>{error}</div>}

      {advisory && (
        <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span className={`badge ${advisory.risk_level === 'LOW' ? 'badge-green' : 'badge-yellow'}`}>{advisory.risk_level} RISK</span>
            <span style={{ color: 'var(--text-muted)' }}>{advisory.provider} ({advisory.model})</span>
          </div>
          <p style={{ fontSize: '0.85rem' }}>{advisory.advisory_summary}</p>
          {advisory.recommendations.length > 0 && (
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem' }}>
              {advisory.recommendations.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};
