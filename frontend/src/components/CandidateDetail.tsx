import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Candidate, Evaluation, Approval, ReleaseManifest } from '../api/types';
import { EvaluationRunner } from './EvaluationRunner';
import { ApprovalSignoffModal } from './ApprovalSignoffModal';
import { LLMAdvisoryPanel } from './LLMAdvisoryPanel';
import { useAuth } from '../context/AuthContext';

export const CandidateDetail: React.FC<{ candidateId: string; onBack: () => void }> = ({ candidateId, onBack }) => {
  const { user } = useAuth();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [manifest, setManifest] = useState<ReleaseManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEvalOpen, setIsEvalOpen] = useState(false);
  const [isSignoffOpen, setIsSignoffOpen] = useState(false);
  const [activeEval, setActiveEval] = useState<Evaluation | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cand, evalsRes, appsRes] = await Promise.all([
        api.getCandidate(candidateId),
        api.listEvaluations(candidateId),
        api.listApprovals(candidateId),
      ]);
      setCandidate(cand);
      setEvaluations(evalsRes.items);
      setApprovals(appsRes);
      if (evalsRes.items.length > 0) setActiveEval(evalsRes.items[0]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [candidateId]);

  const handleExportManifest = async () => {
    if (!candidate || !activeEval) return;
    try {
      const exp = await api.exportManifest(candidate.id, activeEval.id);
      setManifest(exp);
      const updated = await api.getCandidate(candidate.id);
      setCandidate(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  if (loading) return <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>Loading candidate...</div>;
  if (!candidate) return <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>Candidate not found.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={onBack}>← Back</button>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
              {candidate.name} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>v{candidate.version}</span>
              <span className={`badge ${candidate.status === 'APPROVED' ? 'badge-green' : candidate.status === 'REJECTED' ? 'badge-red' : 'badge-yellow'}`} style={{ marginLeft: '0.5rem' }}>
                {candidate.status}
              </span>
            </h1>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Registered by {candidate.created_by}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {user?.role !== 'viewer' && <button className="btn btn-secondary btn-sm" onClick={() => setIsEvalOpen(true)}>Run Evaluation</button>}
          {activeEval && user?.role !== 'viewer' && <button className="btn btn-secondary btn-sm" onClick={() => setIsSignoffOpen(true)}>Sign-Off</button>}
          {activeEval && user?.role === 'admin' && <button className="btn btn-primary btn-sm" onClick={handleExportManifest}>Export Manifest</button>}
        </div>
      </div>

      {error && <div style={{ padding: '0.75rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem' }}>{error}</div>}

      <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <div><div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>TASK</div><strong>{candidate.task_type}</strong></div>
        <div><div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ARCHITECTURE</div><strong>{candidate.base_model}</strong></div>
        <div><div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ARTIFACT CHECKSUM</div><code>{candidate.artifact_hash.slice(0, 14)}...</code></div>
        <div><div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>LOCATION</div><span style={{ fontSize: '0.8rem' }}>{candidate.artifact_uri}</span></div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.75rem' }}>Evaluations ({evaluations.length})</h2>
        {evaluations.map(ev => (
          <div key={ev.id} style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span className={`badge ${ev.gate_verdict === 'APPROVED_FOR_RELEASE' ? 'badge-green' : 'badge-red'}`}>{ev.gate_verdict} ({ev.readiness_score}%)</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ev.benchmark_dataset}</span>
            </div>
            <table>
              <thead><tr><th>Metric</th><th>Condition</th><th>Threshold</th><th>Actual</th><th>Severity</th><th>Status</th></tr></thead>
              <tbody>
                {ev.gate_results.map((r, i) => (
                  <tr key={i}>
                    <td><strong>{r.metric_name}</strong></td>
                    <td><code>{r.operator}</code></td>
                    <td>{r.threshold}</td>
                    <td><strong>{r.actual_value ?? 'N/A'}</strong></td>
                    <td><span className={`badge ${r.severity === 'blocker' ? 'badge-red' : 'badge-yellow'}`}>{r.severity}</span></td>
                    <td><span className={`badge ${r.passed ? 'badge-green' : 'badge-red'}`}>{r.passed ? 'PASS' : 'FAIL'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <LLMAdvisoryPanel evaluation={ev} />
          </div>
        ))}
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.75rem' }}>Stakeholder Sign-Offs ({approvals.length})</h2>
        <table>
          <thead><tr><th>Reviewer</th><th>Role</th><th>Decision</th><th>Signature</th><th>Timestamp</th></tr></thead>
          <tbody>
            {approvals.map(a => (
              <tr key={a.id}>
                <td><strong>{a.reviewer_id}</strong></td>
                <td><span className="badge badge-blue">{a.reviewer_role}</span></td>
                <td><span className={`badge ${a.decision === 'APPROVED' ? 'badge-green' : 'badge-red'}`}>{a.decision}</span></td>
                <td><code>{a.signature.slice(0, 12)}...</code></td>
                <td>{new Date(a.signed_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {manifest && (
        <div className="card" style={{ border: '1px solid var(--accent-emerald)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Signed Release Manifest</h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <a href={api.getManifestDownloadUrl(manifest.id, 'json')} className="btn btn-secondary btn-sm" download>JSON</a>
              <a href={api.getManifestDownloadUrl(manifest.id, 'yaml')} className="btn btn-secondary btn-sm" download>YAML</a>
            </div>
          </div>
          <pre style={{ marginTop: '0.5rem' }}>{manifest.manifest_hash}</pre>
        </div>
      )}

      <EvaluationRunner
        candidate={candidate}
        isOpen={isEvalOpen}
        onClose={() => setIsEvalOpen(false)}
        onEvaluationCompleted={(e) => { setEvaluations([e, ...evaluations]); setActiveEval(e); loadData(); }}
      />
      {activeEval && (
        <ApprovalSignoffModal
          evaluation={activeEval}
          isOpen={isSignoffOpen}
          onClose={() => setIsSignoffOpen(false)}
          onApprovalRecorded={(a) => { setApprovals([a, ...approvals]); loadData(); }}
        />
      )}
    </div>
  );
};
