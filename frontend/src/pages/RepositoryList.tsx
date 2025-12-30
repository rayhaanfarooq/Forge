import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRepos, addRepo } from '../utils/api';
import type { Repository } from '../types';

export default function RepositoryList() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newRepoPath, setNewRepoPath] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadRepos();
  }, []);

  async function loadRepos() {
    try {
      setLoading(true);
      const data = await getRepos();
      setRepos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories');
    } finally {
      setLoading(false);
    }
  }

  async function handleAddRepo(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await addRepo(newRepoPath);
      setNewRepoPath('');
      setShowAddForm(false);
      loadRepos();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add repository');
    }
  }

  if (loading) {
    return <div className="card">Loading repositories...</div>;
  }

  return (
    <div>
      <div className="card">
        <h2>Repositories</h2>
        {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}
        
        {!showAddForm ? (
          <button className="btn" onClick={() => setShowAddForm(true)}>
            Add Repository
          </button>
        ) : (
          <form onSubmit={handleAddRepo}>
            <input
              type="text"
              className="input"
              placeholder="Repository path (e.g., /path/to/repo)"
              value={newRepoPath}
              onChange={(e) => setNewRepoPath(e.target.value)}
              required
            />
            <button type="submit" className="btn">Add</button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setShowAddForm(false);
                setNewRepoPath('');
              }}
            >
              Cancel
            </button>
          </form>
        )}

        {repos.length === 0 ? (
          <p style={{ marginTop: '20px', color: '#666' }}>No repositories tracked yet.</p>
        ) : (
          <ul className="list" style={{ marginTop: '20px' }}>
            {repos.map((repo) => (
              <li
                key={repo.id}
                className="list-item"
                onClick={() => navigate(`/repos/${repo.id}`)}
              >
                <div style={{ fontWeight: '500' }}>{repo.name}</div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {repo.local_path}
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  Base: {repo.base_branch} | Last scanned: {repo.last_scanned_at ? new Date(repo.last_scanned_at).toLocaleString() : 'Never'}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

