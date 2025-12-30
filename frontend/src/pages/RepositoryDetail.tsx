import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRepoBranches, scanRepo, getRepos } from '../utils/api';
import type { Branch, Repository } from '../types';

export default function RepositoryDetail() {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    if (repoId) {
      loadData();
    }
  }, [repoId]);

  async function loadData() {
    if (!repoId) return;
    try {
      setLoading(true);
      const [reposData, branchesData] = await Promise.all([
        getRepos(),
        getRepoBranches(parseInt(repoId)),
      ]);
      const foundRepo = reposData.find((r) => r.id === parseInt(repoId));
      setRepo(foundRepo || null);
      setBranches(branchesData);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    if (!repoId) return;
    try {
      setScanning(true);
      await scanRepo(parseInt(repoId));
      loadData();
    } catch (err) {
      console.error('Failed to scan:', err);
    } finally {
      setScanning(false);
    }
  }

  if (loading) {
    return <div className="card">Loading...</div>;
  }

  if (!repo) {
    return <div className="card">Repository not found</div>;
  }

  return (
    <div>
      <div className="card">
        <h2>{repo.name}</h2>
        <p style={{ color: '#666', marginBottom: '15px' }}>{repo.local_path}</p>
        <button className="btn" onClick={handleScan} disabled={scanning}>
          {scanning ? 'Scanning...' : 'Scan Repository'}
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/')}>
          Back
        </button>
      </div>

      <div className="card">
        <h2>Branches ({branches.length})</h2>
        {branches.length === 0 ? (
          <p style={{ color: '#666' }}>No branches found.</p>
        ) : (
          <ul className="list" style={{ marginTop: '15px' }}>
            {branches.map((branch) => (
              <li
                key={branch.id}
                className="list-item"
                onClick={() => navigate(`/branches/${branch.id}`)}
              >
                <div style={{ fontWeight: '500' }}>{branch.branch_name}</div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  Status: <span className={`badge badge-${branch.status === 'active' ? 'success' : 'warning'}`}>
                    {branch.status}
                  </span>
                  {branch.parent_branch && ` | Parent: ${branch.parent_branch}`}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

