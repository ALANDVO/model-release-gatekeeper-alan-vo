import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Role } from '../api/types';

interface NavbarProps {
  activeTab: 'candidates' | 'policies' | 'manifests' | 'audit';
  setActiveTab: (tab: 'candidates' | 'policies' | 'manifests' | 'audit') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, config, demoLogin, initiateOidcLogin, logout } = useAuth();

  return (
    <header style={{ backgroundColor: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)' }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>Model Release Gatekeeper</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Alan Vo | AI & Machine Learning</div>
          </div>
          <nav style={{ display: 'flex', gap: '0.35rem' }}>
            <button className={`btn btn-sm ${activeTab === 'candidates' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('candidates')}>Candidates</button>
            <button className={`btn btn-sm ${activeTab === 'policies' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('policies')}>Policies</button>
            <button className={`btn btn-sm ${activeTab === 'manifests' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('manifests')}>Manifests</button>
            <button className={`btn btn-sm ${activeTab === 'audit' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('audit')}>Audit</button>
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {config?.demo_mode && (
            <select
              value={user?.role || 'analyst'}
              onChange={(e) => demoLogin(e.target.value as Role)}
              style={{ width: 'auto', padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
            >
              <option value="viewer">Viewer</option>
              <option value="analyst">Analyst</option>
              <option value="admin">Admin</option>
            </select>
          )}
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge badge-blue">{user.role}</span>
              <button className="btn btn-secondary btn-sm" onClick={logout}>Logout</button>
            </div>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={initiateOidcLogin}>Login</button>
          )}
        </div>
      </div>
    </header>
  );
};
