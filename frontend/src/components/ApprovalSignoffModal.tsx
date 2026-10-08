import React, { useState } from 'react';
import { api } from '../api/client';
import { Evaluation, Approval } from '../api/types';
import { useAuth } from '../context/AuthContext';

interface Props {
  evaluation: Evaluation;
  isOpen: boolean;
  onClose: () => void;
  onApprovalRecorded: (a: Approval) => void;
}

export const ApprovalSignoffModal: React.FC<Props> = ({ evaluation, isOpen, onClose, onApprovalRecorded }) => {
  const { user } = useAuth();
  const [role, setRole] = useState<'ml_engineer' | 'safety_lead' | 'release_manager'>('ml_engineer');
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED'>('APPROVED');
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const a = await api.recordApproval({
        evaluation_id: evaluation.id,
        reviewer_role: role,
        decision,
        comments,
      });
      onApprovalRecorded(a);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content card" style={{ padding: '1.5rem', maxWidth: '500px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Record Stakeholder Sign-Off</h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Gate Verdict: {evaluation.gate_verdict}</div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>

        {error && <div style={{ padding: '0.5rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '0.75rem' }}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <select value={role} onChange={e => setRole(e.target.value as 'ml_engineer' | 'safety_lead' | 'release_manager')}>
            <option value="ml_engineer">ML Engineer (Convergence & Metrics)</option>
            <option value="safety_lead">AI Safety / Alignment Lead</option>
            <option value="release_manager" disabled={user?.role !== 'admin'}>Release Manager {user?.role !== 'admin' ? '(Admin Only)' : ''}</option>
          </select>
          <select value={decision} onChange={e => setDecision(e.target.value as 'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED')}>
            <option value="APPROVED">APPROVED</option>
            <option value="CHANGES_REQUESTED">CHANGES REQUESTED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
          <textarea rows={3} placeholder="Review comments and sign-off justification..." value={comments} onChange={e => setComments(e.target.value)} />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className={`btn btn-sm ${decision === 'APPROVED' ? 'btn-primary' : 'btn-danger'}`} disabled={loading}>
              {loading ? 'Signing...' : `Submit ${decision}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
