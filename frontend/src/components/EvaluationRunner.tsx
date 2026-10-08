import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Candidate, Policy, Evaluation } from '../api/types';

interface EvaluationRunnerProps {
  candidate: Candidate;
  isOpen: boolean;
  onClose: () => void;
  onEvaluationCompleted: (evaluation: Evaluation) => void;
}

export const EvaluationRunner: React.FC<EvaluationRunnerProps> = ({
  candidate,
  isOpen,
  onClose,
  onEvaluationCompleted,
}) => {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState('');
  const [benchmarkDataset, setBenchmarkDataset] = useState('gatekeeper-ai-safety-bench-v1');
  const [datasetHash, setDatasetHash] = useState('4a8e99ef3519808a38b69da2188ff4579c388bc5f2723c3167104e67215c9284');

  const [accMmlu, setAccMmlu] = useState('0.85');
  const [toxicityRate, setToxicityRate] = useState('0.008');
  const [hallucinationRate, setHallucinationRate] = useState('0.03');
  const [latencyP95, setLatencyP95] = useState('240.0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.listPolicies(candidate.task_type)
        .then(res => {
          setPolicies(res);
          const def = res.find(p => p.is_default);
          if (def) setSelectedPolicyId(def.id);
          else if (res.length > 0) setSelectedPolicyId(res[0].id);
        })
        .catch(err => setError(err.message));
    }
  }, [isOpen, candidate.task_type]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.executeEvaluation({
        candidate_id: candidate.id,
        policy_id: selectedPolicyId || undefined,
        benchmark_dataset: benchmarkDataset,
        dataset_hash: datasetHash,
        metrics: {
          accuracy_mmlu: parseFloat(accMmlu) || 0,
          toxicity_rate: parseFloat(toxicityRate) || 0,
          hallucination_rate: parseFloat(hallucinationRate) || 0,
          latency_p95_ms: parseFloat(latencyP95) || 0,
        },
      });
      onEvaluationCompleted(res);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content card" style={{ padding: '1.5rem', maxWidth: '600px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Run Gate Evaluation: {candidate.name}</h2>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>

        {error && <div style={{ padding: '0.5rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '0.75rem' }}>{error}</div>}

        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setAccMmlu('0.88'); setToxicityRate('0.005'); setLatencyP95('210'); }}>Passing Preset</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setToxicityRate('0.05'); setAccMmlu('0.60'); }}>Blocker Fail</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setLatencyP95('520'); }}>Latency Warning</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <select value={selectedPolicyId} onChange={e => setSelectedPolicyId(e.target.value)} required>
            {policies.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input type="text" placeholder="Dataset Name" value={benchmarkDataset} onChange={e => setBenchmarkDataset(e.target.value)} required />
          <input type="text" placeholder="Dataset SHA-256 Hash" value={datasetHash} onChange={e => setDatasetHash(e.target.value)} required />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>accuracy_mmlu (&gt;=0.70)</label>
              <input type="number" step="0.01" value={accMmlu} onChange={e => setAccMmlu(e.target.value)} required />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>toxicity_rate (&lt;=0.02)</label>
              <input type="number" step="0.001" value={toxicityRate} onChange={e => setToxicityRate(e.target.value)} required />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>hallucination_rate (&lt;=0.05)</label>
              <input type="number" step="0.005" value={hallucinationRate} onChange={e => setHallucinationRate(e.target.value)} required />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>latency_p95_ms (&lt;=450ms)</label>
              <input type="number" step="1" value={latencyP95} onChange={e => setLatencyP95(e.target.value)} required />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>
              {loading ? 'Evaluating...' : 'Execute Evaluation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
