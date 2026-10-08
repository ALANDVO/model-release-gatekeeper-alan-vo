import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ManifestViewer } from '../components/ManifestViewer';
import { api } from '../api/client';

describe('ManifestViewer component', () => {
  it('loads sample manifest and verifies tamper-evident digest', async () => {
    vi.spyOn(api, 'verifyManifest').mockResolvedValue({
      valid: true,
      computed_hash: '4a8e99ef3519808a38b69da2188ff4579c388bc5f2723c3167104e67215c9284',
      hash_match: true,
      signature_valid: true,
      verdict: 'VERIFIED_VALID',
      details: {},
    });

    render(<ManifestViewer />);

    const loadSampleBtn = screen.getByText('Load Sample Manifest');
    fireEvent.click(loadSampleBtn);

    const verifyBtn = screen.getByText('Verify Manifest Integrity');
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText('VERIFIED_VALID')).toBeInTheDocument();
      expect(screen.getByText('Manifest Cryptographically Verified')).toBeInTheDocument();
    });
  });
});
