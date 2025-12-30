import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRepos, addRepo } from "../utils/api";
import type { Repository } from "../types";

export default function RepositoryList() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newRepoPath, setNewRepoPath] = useState("");
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
      setError(
        err instanceof Error ? err.message : "Failed to load repositories"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleAddRepo(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await addRepo(newRepoPath);
      setNewRepoPath("");
      setShowAddForm(false);
      loadRepos();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add repository");
    }
  }

  if (loading) {
    return <div className="loading">Loading repositories...</div>;
  }

  return (
    <div>
      <div className="card">
        <h2>📦 Repositories</h2>
        {error && <div className="error">{error}</div>}

        {!showAddForm ? (
          <button className="btn btn-icon" onClick={() => setShowAddForm(true)}>
            <span>+</span> Add Repository
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
            <button type="submit" className="btn">
              Add
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setShowAddForm(false);
                setNewRepoPath("");
              }}
            >
              Cancel
            </button>
          </form>
        )}

        {repos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📁</div>
            <div className="empty-state-title">No repositories tracked yet</div>
            <div className="empty-state-text">
              Add a repository to start tracking your projects
            </div>
          </div>
        ) : (
          <div style={{ marginTop: "20px" }}>
            {repos.map((repo) => (
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
                  <span>
                    Last scanned:{" "}
                    {repo.last_scanned_at
                      ? new Date(repo.last_scanned_at).toLocaleString()
                      : "Never"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
