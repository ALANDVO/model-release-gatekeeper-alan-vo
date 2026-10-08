import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { CandidateList } from './components/CandidateList';
import { CandidateDetail } from './components/CandidateDetail';
import { PolicyManager } from './components/PolicyManager';
import { ManifestViewer } from './components/ManifestViewer';
import { AuditLogViewer } from './components/AuditLogViewer';
import { Candidate } from './api/types';

const MainLayout: React.FC = () => {
  const { handleOidcCallback } = useAuth();
  const [activeTab, setActiveTab] = useState<'candidates' | 'policies' | 'manifests' | 'audit'>('candidates');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    if (code && state) {
      window.history.replaceState({}, document.title, window.location.pathname);
      handleOidcCallback(code, state);
    }
  }, [handleOidcCallback]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={(t) => { setActiveTab(t); setSelectedCandidateId(null); }}
      />
      <main className="container" style={{ flex: 1, paddingBottom: '3rem' }}>
        {activeTab === 'candidates' && (
          selectedCandidateId ? (
            <CandidateDetail candidateId={selectedCandidateId} onBack={() => setSelectedCandidateId(null)} />
          ) : (
            <CandidateList onSelectCandidate={(c: Candidate) => setSelectedCandidateId(c.id)} />
          )
        )}
        {activeTab === 'policies' && <PolicyManager />}
        {activeTab === 'manifests' && <ManifestViewer />}
        {activeTab === 'audit' && <AuditLogViewer />}
      </main>
      <footer style={{ borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', padding: '0.75rem', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Model Release Gatekeeper | Built by Alan Vo (<a href="mailto:alanvo@gmail.com" style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}>alanvo@gmail.com</a>) | GitHub ALANDVO
      </footer>
    </div>
  );
};

export const App: React.FC = () => <AuthProvider><MainLayout /></AuthProvider>;
export default App;
