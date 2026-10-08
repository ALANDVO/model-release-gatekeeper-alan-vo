import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserInfo, Role, AuthConfig } from '../api/types';
import { api, setAuthToken } from '../api/client';

interface AuthContextType {
  user: UserInfo | null;
  role: Role | null;
  config: AuthConfig | null;
  loading: boolean;
  error: string | null;
  demoLogin: (role: Role) => Promise<void>;
  initiateOidcLogin: () => Promise<void>;
  handleOidcCallback: (code: string, state: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function generateRandomString(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const array = new Uint8Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array, byte => chars[byte % chars.length]).join('');
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  const bytes = new Uint8Array(digest);
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAuthConfig()
      .then(cfg => {
        setConfig(cfg);
        if (cfg.demo_mode) {
          demoLogin('analyst').catch(() => setLoading(false));
        } else {
          setLoading(false);
        }
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const demoLogin = async (selectedRole: Role) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.demoLogin(`operator-${selectedRole}`, `${selectedRole}@alan-gatekeeper.local`, selectedRole);
      setAuthToken(resp.access_token);
      const u = await api.getUserInfo();
      setUser(u);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setAuthToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const initiateOidcLogin = async () => {
    if (!config) return;
    const state = generateRandomString(32);
    const verifier = generateRandomString(64);
    const challenge = await generateCodeChallenge(verifier);
    sessionStorage.setItem('pkce_state', state);
    sessionStorage.setItem('pkce_code_verifier', verifier);

    const redirectUri = `${window.location.origin}/callback`;
    const authUrl = new URL(`${config.issuer_url}/protocol/openid-connect/auth`);
    authUrl.searchParams.set('client_id', config.client_id);
    authUrl.searchParams.set('redirect_uri', redirectUri);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('scope', 'openid profile email roles');
    authUrl.searchParams.set('state', state);
    authUrl.searchParams.set('code_challenge', challenge);
    authUrl.searchParams.set('code_challenge_method', 'S256');
    window.location.href = authUrl.toString();
  };

  const handleOidcCallback = async (code: string, state: string) => {
    setLoading(true);
    const savedState = sessionStorage.getItem('pkce_state');
    const verifier = sessionStorage.getItem('pkce_code_verifier');
    sessionStorage.removeItem('pkce_state');
    sessionStorage.removeItem('pkce_code_verifier');

    if (!savedState || savedState !== state) {
      setError('PKCE state validation failed. Possible CSRF attack detected.');
      setLoading(false);
      return;
    }
    try {
      const resp = await api.exchangeToken(code, verifier || '', `${window.location.origin}/callback`);
      setAuthToken(resp.access_token);
      const u = await api.getUserInfo();
      setUser(u);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setAuthToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setAuthToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, role: user ? user.role : null, config, loading, error, demoLogin, initiateOidcLogin, handleOidcCallback, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
