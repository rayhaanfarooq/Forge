import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getRepoBranches, scanRepo, getRepos } from "../utils/api";
import type { Branch, Repository } from "../types";

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
      console.error("Failed to load data:", err);
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
      console.error("Failed to scan:", err);
    } finally {
      setScanning(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!repo) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">❌</div>
          <div className="empty-state-title">Repository not found</div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "20px",
          }}
        >
          <div>
            <h2 style={{ marginBottom: "8px" }}>📦 {repo.name}</h2>
            <div className="repo-card-path">{repo.local_path}</div>
          </div>
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/repos")}
          >
            ← Back
          </button>
        </div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <button
            className="btn btn-icon"
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? "⏳ Scanning..." : "🔄 Scan Repository"}
          </button>
        </div>
      </div>

      <div className="card">
        <h2>🌿 Branches ({branches.length})</h2>
        {branches.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🌿</div>
            <div className="empty-state-title">No branches found</div>
            <div className="empty-state-text">
              Scan the repository to discover branches
            </div>
          </div>
        ) : (
          <div style={{ marginTop: "20px" }}>
            {branches.map((branch) => (
              <div
                key={branch.id}
                className="branch-card"
                onClick={() => navigate(`/branches/${branch.id}`)}
              >
                <div className="list-item-title">
                  {branch.branch_name}
                  <span
                    className={`badge badge-${
                      branch.status === "active" ? "success" : "warning"
                    }`}
                  >
                    {branch.status}
                  </span>
                </div>
                <div className="list-item-subtitle">
                  {branch.parent_branch && `Parent: ${branch.parent_branch} • `}
                  Base: {branch.base_branch}
                  {branch.last_synced_at &&
                    ` • Last synced: ${new Date(
                      branch.last_synced_at
                    ).toLocaleDateString()}`}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
