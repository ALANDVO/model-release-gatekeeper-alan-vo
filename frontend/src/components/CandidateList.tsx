import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Candidate } from '../api/types';
import { CandidateCreateModal } from './CandidateCreateModal';
import { useAuth } from '../context/AuthContext';

export const CandidateList: React.FC<{ onSelectCandidate: (c: Candidate) => void }> = ({ onSelectCandidate }) => {
  const { user } = useAuth();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [taskFilter, setTaskFilter] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchCandidates = async () => {
    setLoading(true);
    try {
      const res = await api.listCandidates({
        search: search || undefined,
        task_type: taskFilter || undefined,
      });
      setCandidates(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCandidates(); }, [taskFilter]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Model Candidates</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Evaluate models against release policy gates.</p>
        </div>
        {user?.role !== 'viewer' && (
          <button className="btn btn-primary btn-sm" onClick={() => setIsModalOpen(true)}>+ Register Candidate</button>
        )}
      </div>

      <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem' }}>
        <form onSubmit={(e) => { e.preventDefault(); fetchCandidates(); }} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: '0.5rem' }}>
          <input type="text" placeholder="Search models..." value={search} onChange={e => setSearch(e.target.value)} />
          <select value={taskFilter} onChange={e => setTaskFilter(e.target.value)}>
            <option value="">All Tasks</option>
            <option value="text-generation">Text Generation</option>
            <option value="text-classification">Text Classification</option>
          </select>
          <button type="submit" className="btn btn-secondary btn-sm">Filter</button>
        </form>
      </div>

      {error && <div style={{ padding: '0.75rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '1rem' }}>{error}</div>}

      {loading ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>Loading candidates...</div>
      ) : candidates.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>No candidates found.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Task</th>
                <th>Architecture</th>
                <th>Checksum</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <tr key={c.id}>
                  <td><strong>{c.name}</strong> <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>v{c.version}</span></td>
                  <td>{c.task_type}</td>
                  <td>{c.base_model}</td>
                  <td><code>{c.artifact_hash.slice(0, 10)}...</code></td>
                  <td>
                    <span className={`badge ${c.status === 'APPROVED' ? 'badge-green' : c.status === 'REJECTED' ? 'badge-red' : 'badge-yellow'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => onSelectCandidate(c)}>Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CandidateCreateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={c => { setCandidates([c, ...candidates]); onSelectCandidate(c); }}
      />
    </div>
  );
};
