import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Policy, GateRule, Severity, Operator } from '../api/types';
import { useAuth } from '../context/AuthContext';

export const PolicyManager: React.FC = () => {
  const { user } = useAuth();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [taskType, setTaskType] = useState('text-generation');
  const [description, setDescription] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [rules, setRules] = useState<GateRule[]>([
    { metric_name: 'accuracy', operator: '>=', threshold: 0.85, tolerance: 0.01, severity: 'blocker' },
    { metric_name: 'latency_p95_ms', operator: '<=', threshold: 300.0, tolerance: 15.0, severity: 'warning' }
  ]);

  const fetchPolicies = async () => {
    setLoading(true);
    try {
      const res = await api.listPolicies();
      setPolicies(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPolicies(); }, []);

  const handleAddRule = () => {
    setRules([...rules, { metric_name: '', operator: '>=', threshold: 0.8, tolerance: 0.0, severity: 'blocker' }]);
  };

  const handleRemoveRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index));
  };

  const handleRuleChange = (index: number, field: keyof GateRule, value: unknown) => {
    const updated = [...rules];
    updated[index] = { ...updated[index], [field]: value };
    setRules(updated);
  };

  const handleCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createPolicy({ name, task_type: taskType, description, rules, is_default: isDefault });
      setPolicies([created, ...policies]);
      setIsModalOpen(false);
      setName('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Release Gate Policies</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Automated gating rules and threshold requirements.</p>
        </div>
        {user?.role === 'admin' && (
          <button className="btn btn-primary btn-sm" onClick={() => setIsModalOpen(true)}>+ Create Policy</button>
        )}
      </div>

      {error && <div style={{ padding: '0.75rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '1rem' }}>{error}</div>}

      {loading ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>Loading policies...</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {policies.map(p => (
            <div key={p.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>{p.name}</h2>
                  <span className="badge badge-blue">{p.task_type}</span>
                  {p.is_default && <span className="badge badge-green">Default</span>}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>v{p.version} | {p.created_by}</div>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>{p.description}</p>
              <table>
                <thead><tr><th>Metric</th><th>Condition</th><th>Threshold</th><th>Tolerance</th><th>Severity</th></tr></thead>
                <tbody>
                  {p.rules.map((r, i) => (
                    <tr key={i}>
                      <td><strong>{r.metric_name}</strong></td>
                      <td><code>{r.operator}</code></td>
                      <td>{r.threshold}</td>
                      <td>±{r.tolerance}</td>
                      <td><span className={`badge ${r.severity === 'blocker' ? 'badge-red' : 'badge-yellow'}`}>{r.severity}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content card" style={{ padding: '1.5rem', maxWidth: '650px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Create Policy</h2>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsModalOpen(false)}>✕</button>
            </div>
            <form onSubmit={handleCreatePolicy} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <input type="text" placeholder="Policy Name" required value={name} onChange={e => setName(e.target.value)} />
              <select value={taskType} onChange={e => setTaskType(e.target.value)}>
                <option value="text-generation">Text Generation</option>
                <option value="text-classification">Text Classification</option>
              </select>
              <textarea placeholder="Description" rows={2} value={description} onChange={e => setDescription(e.target.value)} />
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input type="checkbox" id="is_def" checked={isDefault} onChange={e => setIsDefault(e.target.checked)} style={{ width: 'auto' }} />
                <label htmlFor="is_def" style={{ fontSize: '0.8rem' }}>Set default for {taskType}</label>
              </div>

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Rules</span>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={handleAddRule}>+ Add Rule</button>
                </div>
                {rules.map((r, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <input type="text" placeholder="Metric" value={r.metric_name} onChange={e => handleRuleChange(idx, 'metric_name', e.target.value)} required />
                    <select value={r.operator} onChange={e => handleRuleChange(idx, 'operator', e.target.value as Operator)}>
                      <option value=">=">&gt;=</option><option value="<=">&lt;=</option><option value="==">==</option>
                    </select>
                    <input type="number" step="0.001" value={r.threshold} onChange={e => handleRuleChange(idx, 'threshold', parseFloat(e.target.value) || 0)} required />
                    <select value={r.severity} onChange={e => handleRuleChange(idx, 'severity', e.target.value as Severity)}>
                      <option value="blocker">Blocker</option><option value="warning">Warning</option>
                    </select>
                    <button type="button" className="btn btn-danger btn-sm" onClick={() => handleRemoveRule(idx)} disabled={rules.length <= 1}>✕</button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Save Policy</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
