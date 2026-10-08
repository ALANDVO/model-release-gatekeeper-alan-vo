import React, { useState } from 'react';
import { api } from '../api/client';
import { ManifestVerifyResponse } from '../api/types';

export const ManifestViewer: React.FC = () => {
  const [jsonInput, setJsonInput] = useState('');
  const [expectedHash, setExpectedHash] = useState('');
  const [result, setResult] = useState<ManifestVerifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sampleManifest = {
    schema_version: '1.0.0',
    generator: 'Model Release Gatekeeper',
    author: 'Alan Vo <alanvo@gmail.com>',
    candidate: { id: 'c1', name: 'roberta-safety-gatekeeper-v1', version: '1.0.0', status: 'APPROVED' },
    evaluation: { gate_verdict: 'APPROVED_FOR_RELEASE', readiness_score: 100.0 },
    release_verdict: 'APPROVED',
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const parsed = JSON.parse(jsonInput);
      const res = await api.verifyManifest({
        manifest_json: parsed,
        expected_hash: expectedHash || undefined,
      });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Release Manifest Verification</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Verify cryptographic tamper-evidence of signed release manifests.</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={() => setJsonInput(JSON.stringify(sampleManifest, null, 2))}>
          Load Sample Manifest
        </button>
      </div>

      <div className="card">
        {error && <div style={{ padding: '0.5rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '0.75rem' }}>{error}</div>}
        <form onSubmit={handleVerify} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <textarea
            rows={7}
            required
            placeholder="Paste release manifest JSON..."
            value={jsonInput}
            onChange={e => setJsonInput(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
          />
          <input
            type="text"
            placeholder="Expected SHA-256 Digest (Optional)"
            value={expectedHash}
            onChange={e => setExpectedHash(e.target.value)}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify Manifest Integrity'}
            </button>
          </div>
        </form>
      </div>

      {result && (
        <div className="card" style={{ border: `1px solid ${result.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span className={`badge ${result.valid ? 'badge-green' : 'badge-red'}`}>{result.verdict}</span>
            <strong>{result.valid ? 'Manifest Cryptographically Verified' : 'Tamper Detected'}</strong>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Computed SHA-256:</span>
          <pre style={{ marginTop: '0.25rem' }}>{result.computed_hash}</pre>
        </div>
      )}
    </div>
  );
};
