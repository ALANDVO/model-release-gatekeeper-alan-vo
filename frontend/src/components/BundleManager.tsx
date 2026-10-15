import React, { useState } from 'react';
import { api } from '../api/client';
import { CandidateBundleExport } from '../api/types';

interface BundleManagerProps {
  candidateId: string;
  candidateName: string;
  onImportSuccess?: () => void;
}

export const BundleManager: React.FC<BundleManagerProps> = ({ candidateId, candidateName, onImportSuccess }) => {
  const [bundle, setBundle] = useState<CandidateBundleExport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const [jsonInput, setJsonInput] = useState('');
  const [importAsNew, setImportAsNew] = useState(true);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    try { setBundle(await api.exportCandidateBundle(candidateId)); }
    catch (err: unknown) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setLoading(false); }
  };

  const handleDownload = () => {
    if (!bundle) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${candidateName}-bundle-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    setImportLoading(true);
    setImportError(null);
    setImportSuccess(null);
    try {
      const res = await api.importCandidateBundle({ bundle: JSON.parse(jsonInput), import_as_new: importAsNew });
      setImportSuccess(res.message);
      setJsonInput('');
      if (onImportSuccess) onImportSuccess();
    } catch (err: unknown) { setImportError(err instanceof Error ? err.message : String(err)); }
    finally { setImportLoading(false); }
  };

  const errStyle = { padding: '0.5rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', fontSize: '0.8rem' };
  const okStyle = { padding: '0.5rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#34d399', borderRadius: '0.375rem', fontSize: '0.8rem' };
  const muted = { fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Candidate Bundle</h3>
        <span className="badge badge-blue">Portability</span>
      </div>

      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Export Bundle</h4>
        <p style={muted}>Export complete candidate record including evaluations, approvals, and manifests as a portable JSON bundle.</p>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-primary btn-sm" onClick={handleExport} disabled={loading}>{loading ? 'Exporting...' : 'Export Bundle'}</button>
          {bundle && <button className="btn btn-secondary btn-sm" onClick={handleDownload} disabled={loading}>Download JSON</button>}
        </div>
        {error && <div style={errStyle}>{error}</div>}
        {bundle && <div style={okStyle}>Bundle ready: {bundle.evaluations.length} evaluations, {bundle.approvals.length} approvals, {bundle.manifests.length} manifests</div>}
      </div>

      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Import Bundle</h4>
        <p style={muted}>Import a previously exported candidate bundle. Creates new candidate with new ID by default.</p>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
          <input type="checkbox" checked={importAsNew} onChange={e => setImportAsNew(e.target.checked)} />
          Import as new candidate (preserves original, creates new ID)
        </label>
        <form onSubmit={handleImport} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <textarea rows={5} placeholder="Paste candidate bundle JSON..." value={jsonInput} onChange={e => setJsonInput(e.target.value)} style={{ fontFamily: 'monospace', fontSize: '0.75rem' }} />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setJsonInput('')}>Clear</button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={importLoading}>{importLoading ? 'Importing...' : 'Import Bundle'}</button>
          </div>
        </form>
        {importError && <div style={errStyle}>{importError}</div>}
        {importSuccess && <div style={okStyle}>{importSuccess}</div>}
      </div>
    </div>
  );
};