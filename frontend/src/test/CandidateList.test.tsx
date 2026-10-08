import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CandidateList } from '../components/CandidateList';
import { AuthProvider } from '../context/AuthContext';
import { api } from '../api/client';
import { Candidate } from '../api/types';

describe('CandidateList component', () => {
  it('renders candidates table and displays model names with status badges', async () => {
    const mockCandidates: Candidate[] = [
      {
        id: 'c-1',
        name: 'llama-3-safety-v1',
        version: '1.0.0',
        task_type: 'text-generation',
        base_model: 'llama-3',
        artifact_uri: 's3://models/llama.bin',
        artifact_hash: '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        description: 'Safety evaluated model',
        tags: ['prod'],
        status: 'APPROVED',
        created_by: 'alan-vo',
        created_at: '2026-10-08T00:00:00Z',
        updated_at: '2026-10-08T00:00:00Z',
      },
    ];

    vi.spyOn(api, 'getAuthConfig').mockResolvedValue({
      issuer_url: 'http://localhost:8080',
      client_id: 'client',
      audience: 'aud',
      demo_mode: false,
      environment: 'development',
    });

    vi.spyOn(api, 'listCandidates').mockResolvedValue({
      items: mockCandidates,
      total: 1,
      page: 1,
      page_size: 10,
    });

    render(
      <AuthProvider>
        <CandidateList onSelectCandidate={vi.fn()} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('llama-3-safety-v1')).toBeInTheDocument();
      expect(screen.getByText('APPROVED')).toBeInTheDocument();
    });
  });
});
