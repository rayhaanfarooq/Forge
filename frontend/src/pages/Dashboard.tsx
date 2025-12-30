import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getRepos, getTestEvents } from '../utils/api';
import type { Stats, Repository, TestEvent } from '../types';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [recentEvents, setRecentEvents] = useState<TestEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const [statsData, reposData, eventsData] = await Promise.all([
        getStats(),
        getRepos(),
        getTestEvents(),
      ]);
      setStats(statsData);
      setRepos(reposData);
      setRecentEvents(eventsData.slice(0, 5));
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  if (!stats) {
    return <div className="card">Failed to load statistics</div>;
  }

  const successRate = stats.total_test_events > 0 
    ? Math.round((stats.successful_tests / stats.total_test_events) * 100)
    : 0;

  return (
    <div>
      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card-icon">📦</div>
          <div className="stat-card-value">{stats.total_repos}</div>
          <div className="stat-card-label">Repositories</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-card-icon">🌿</div>
          <div className="stat-card-value">{stats.total_branches}</div>
          <div className="stat-card-label">Total Branches</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-card-icon">💻</div>
          <div className="stat-card-value">{stats.total_commits}</div>
          <div className="stat-card-label">Commits Tracked</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-card-icon">✅</div>
          <div className="stat-card-value">{stats.total_test_events}</div>
          <div className="stat-card-label">Test Events</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-card-icon">🎯</div>
          <div className="stat-card-value">{successRate}%</div>
          <div className="stat-card-label">Success Rate</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-card-icon">⚡</div>
          <div className="stat-card-value">{stats.recent_activity}</div>
          <div className="stat-card-label">Activity (7 days)</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Recent Repositories */}
        <div className="card">
          <h2>Recent Repositories</h2>
          {repos.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📁</div>
              <div className="empty-state-title">No repositories yet</div>
              <div className="empty-state-text">Add a repository to get started</div>
            </div>
          ) : (
            <div>
              {repos.slice(0, 5).map((repo) => (
                <div
                  key={repo.id}
                  className="repo-card"
                  onClick={() => navigate(`/repos/${repo.id}`)}
                >
                  <div className="repo-card-header">
                    <div>
                      <div className="repo-card-name">{repo.name}</div>
                      <div className="repo-card-path">{repo.local_path}</div>
                    </div>
                  </div>
                  <div className="repo-card-meta">
                    <span>Base: {repo.base_branch}</span>
                    {repo.last_scanned_at && (
                      <span>Scanned: {new Date(repo.last_scanned_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
              ))}
              {repos.length > 5 && (
                <button
                  className="btn btn-secondary"
                  style={{ width: '100%', marginTop: '12px' }}
                  onClick={() => navigate('/')}
                >
                  View All Repositories
                </button>
              )}
            </div>
          )}
        </div>

        {/* Recent Test Events */}
        <div className="card">
          <h2>Recent Test Events</h2>
          {recentEvents.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🧪</div>
              <div className="empty-state-title">No test events yet</div>
              <div className="empty-state-text">Run forge create-tests to see activity</div>
            </div>
          ) : (
            <div>
              {recentEvents.map((event) => (
                <div key={event.id} className="list-item">
                  <div className="list-item-title">
                    {event.command_used}
                    <span className={`badge badge-${event.status === 'success' ? 'success' : 'danger'}`}>
                      {event.status}
                    </span>
                  </div>
                  <div className="list-item-subtitle">
                    {event.ai_provider && `Provider: ${event.ai_provider}`}
                    {event.model && ` | Model: ${event.model}`}
                  </div>
                  <div className="list-item-subtitle">
                    {new Date(event.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
              <button
                className="btn btn-secondary"
                style={{ width: '100%', marginTop: '12px' }}
                onClick={() => navigate('/test-events')}
              >
                View All Events
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

