import React, { useState } from 'react';
import { api } from '../api/client';
import { Candidate } from '../api/types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (candidate: Candidate) => void;
}

export const CandidateCreateModal: React.FC<Props> = ({ isOpen, onClose, onCreated }) => {
  const [name, setName] = useState('');
  const [version, setVersion] = useState('');
  const [taskType, setTaskType] = useState('text-generation');
  const [baseModel, setBaseModel] = useState('');
  const [artifactUri, setArtifactUri] = useState('');
  const [artifactHash, setArtifactHash] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handlePreFill = () => {
    setName('roberta-safety-gatekeeper-v1');
    setVersion('1.0.0');
    setTaskType('text-generation');
    setBaseModel('roberta-large');
    setArtifactUri('s3://models/roberta-safety-v1.0.0.pt');
    setArtifactHash('4a8e99ef3519808a38b69da2188ff4579c388bc5f2723c3167104e67215c9284');
    setDescription('Curated safety model candidate for MMLU and TruthfulQA release gating.');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const created = await api.createCandidate({
        name,
        version,
        task_type: taskType,
        base_model: baseModel,
        artifact_uri: artifactUri,
        artifact_hash: artifactHash,
        description,
        tags: ['release-candidate'],
      });
      onCreated(created);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content card" style={{ padding: '1.5rem', maxWidth: '550px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Register Model Candidate</h2>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>

        {error && <div style={{ padding: '0.5rem', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '0.375rem', marginBottom: '0.75rem' }}>{error}</div>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handlePreFill}>Load Benchmark Example</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.5rem' }}>
            <input type="text" placeholder="Model Name" required value={name} onChange={e => setName(e.target.value)} />
            <input type="text" placeholder="Version (e.g. 1.0.0)" required value={version} onChange={e => setVersion(e.target.value)} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <select value={taskType} onChange={e => setTaskType(e.target.value)}>
              <option value="text-generation">Text Generation</option>
              <option value="text-classification">Text Classification</option>
            </select>
            <input type="text" placeholder="Base Architecture" required value={baseModel} onChange={e => setBaseModel(e.target.value)} />
          </div>
          <input type="text" placeholder="Artifact Storage URI" required value={artifactUri} onChange={e => setArtifactUri(e.target.value)} />
          <input type="text" placeholder="Artifact SHA-256 Checksum" required value={artifactHash} onChange={e => setArtifactHash(e.target.value)} />
          <textarea rows={2} placeholder="Description" value={description} onChange={e => setDescription(e.target.value)} />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>{loading ? 'Registering...' : 'Register'}</button>
          </div>
        </form>
      </div>
    </div>
  );
};
