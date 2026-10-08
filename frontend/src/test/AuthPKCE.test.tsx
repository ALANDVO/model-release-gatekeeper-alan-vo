import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { api, getAuthToken } from '../api/client';

const TestAuthConsumer: React.FC = () => {
  const { user, error, handleOidcCallback } = useAuth();
  return (
    <div>
      <div data-testid="user">{user ? user.username : 'unauthenticated'}</div>
      <div data-testid="error">{error || 'no-error'}</div>
      <button
        onClick={() => handleOidcCallback('test-auth-code', 'valid-state')}
      >
        Trigger Callback
      </button>
    </div>
  );
};

describe('AuthContext PKCE and in-memory token handling', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('rejects callback if state does not match sessionStorage state', async () => {
    sessionStorage.setItem('pkce_state', 'expected-state');
    sessionStorage.setItem('pkce_code_verifier', 'verifier-123');

    vi.spyOn(api, 'getAuthConfig').mockResolvedValue({
      issuer_url: 'http://localhost:8080',
      client_id: 'client',
      audience: 'aud',
      demo_mode: false,
      environment: 'development',
    });

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    const btn = screen.getByText('Trigger Callback');
    await act(async () => {
      btn.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('PKCE state validation failed');
      expect(getAuthToken()).toBeNull();
    });
  });

  it('exchanges code for token and updates user state on matching state', async () => {
    sessionStorage.setItem('pkce_state', 'valid-state');
    sessionStorage.setItem('pkce_code_verifier', 'verifier-123');

    vi.spyOn(api, 'getAuthConfig').mockResolvedValue({
      issuer_url: 'http://localhost:8080',
      client_id: 'client',
      audience: 'aud',
      demo_mode: false,
      environment: 'development',
    });

    vi.spyOn(api, 'exchangeToken').mockResolvedValue({
      access_token: 'valid.token.jwt',
      token_type: 'Bearer',
      expires_in: 3600,
      role: 'analyst',
      username: 'pkce-user',
    });

    vi.spyOn(api, 'getUserInfo').mockResolvedValue({
      user_id: 'u-1',
      username: 'pkce-user',
      email: 'pkce@example.com',
      role: 'analyst',
      is_demo: false,
    });

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    const btn = screen.getByText('Trigger Callback');
    await act(async () => {
      btn.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('pkce-user');
      expect(getAuthToken()).toBe('valid.token.jwt');
      // Verify temporary PKCE state was cleared from sessionStorage
      expect(sessionStorage.getItem('pkce_state')).toBeNull();
    });
  });
});
