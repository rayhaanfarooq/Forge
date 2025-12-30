import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getBranchCommits, getBranchMetrics } from '../utils/api';
import type { Commit, BranchMetrics } from '../types';

export default function BranchDetail() {
  const { branchId } = useParams<{ branchId: string }>();
  const navigate = useNavigate();
  const [commits, setCommits] = useState<Commit[]>([]);
  const [metrics, setMetrics] = useState<BranchMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (branchId) {
      loadData();
    }
  }, [branchId]);

  async function loadData() {
    if (!branchId) return;
    try {
      setLoading(true);
      const [commitsData, metricsData] = await Promise.all([
        getBranchCommits(parseInt(branchId)),
        getBranchMetrics(parseInt(branchId)),
      ]);
      setCommits(commitsData);
      setMetrics(metricsData);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="card">Loading...</div>;
  }

  return (
    <div>
      <div className="card">
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>
          Back
        </button>
      </div>

      {metrics && (
        <div className="card">
          <h2>Metrics</h2>
          <div className="metrics">
            <div className="metric">
              <div className="metric-label">Commits Behind Base</div>
              <div className="metric-value">{metrics.commits_behind_base}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Days Since Last Sync</div>
              <div className="metric-value">
                {metrics.days_since_last_sync !== null
                  ? metrics.days_since_last_sync.toFixed(1)
                  : 'N/A'}
              </div>
            </div>
            <div className="metric">
              <div className="metric-label">Has Generated Tests</div>
              <div className="metric-value">
                {metrics.has_generated_tests ? 'Yes' : 'No'}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Commits ({commits.length})</h2>
        {commits.length === 0 ? (
          <p style={{ color: '#666' }}>No commits found.</p>
        ) : (
          <ul className="list" style={{ marginTop: '15px' }}>
            {commits.map((commit) => (
              <li key={commit.id} className="list-item">
                <div style={{ fontWeight: '500' }}>
                  {commit.message}
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {commit.commit_hash.substring(0, 8)} by {commit.author} | {new Date(commit.timestamp).toLocaleString()}
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {commit.files_changed_count} files | +{commit.lines_added} / -{commit.lines_removed}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

