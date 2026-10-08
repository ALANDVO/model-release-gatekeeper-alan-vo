import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AuditLog } from '../api/types';

export const AuditLogViewer: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [entityFilter, setEntityFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await api.listAuditLogs(entityFilter || undefined);
      setLogs(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, [entityFilter]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Immutable Audit Trail</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Audit logging with UTC timestamps and user attribution.</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchLogs}>Refresh</button>
      </div>

      <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem' }}>
        <select value={entityFilter} onChange={(e) => setEntityFilter(e.target.value)}>
          <option value="">All Entities</option>
          <option value="candidate">Candidate</option>
          <option value="policy">Policy</option>
          <option value="evaluation">Evaluation</option>
          <option value="approval">Approval</option>
          <option value="manifest">Manifest</option>
        </select>
      </div>

      {error && <div style={{ padding: '0.5rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '1rem' }}>{error}</div>}

      {loading ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>Loading audit records...</div>
      ) : logs.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>No audit records found.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead><tr><th>Timestamp (UTC)</th><th>Action</th><th>Entity</th><th>Actor</th><th>Role</th><th>Details</th></tr></thead>
            <tbody>
              {logs.map(l => (
                <tr key={l.id}>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(l.timestamp).toISOString()}</td>
                  <td><span className="badge badge-blue">{l.action}</span></td>
                  <td><strong>{l.entity_type}</strong> <code>{l.entity_id.slice(0, 8)}</code></td>
                  <td>{l.actor_id}</td>
                  <td><span className={`badge ${l.actor_role === 'admin' ? 'badge-red' : 'badge-blue'}`}>{l.actor_role}</span></td>
                  <td><code style={{ fontSize: '0.75rem' }}>{JSON.stringify(l.details)}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
