import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import BranchGraphModal from "../components/BranchGraphModal";
import {
  getRepoDashboard,
  getRepos,
  runRepoAction,
  switchRepoBranch,
} from "../utils/api";
import type {
  BranchNode,
  RepoCommandResult,
  Repository,
  RepositoryDashboard,
} from "../types";

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not recorded";
  }
  return new Date(value).toLocaleString();
}

function formatActionName(action: string) {
  if (action === "submit") {
    return "Submit";
  }
  if (action === "sync") {
    return "Sync";
  }
  return "Test";
}

function getBranchPriority(branch: BranchNode) {
  if (branch.health === "issues") {
    return 0;
  }
  if (branch.health === "current") {
    return 1;
  }
  if (branch.health === "healthy") {
    return 2;
  }
  if (branch.health === "stale") {
    return 4;
  }
  return 3;
}

function getHealthLabel(health: string) {
  switch (health) {
    case "current":
      return "Current";
    case "healthy":
      return "Healthy";
    case "issues":
      return "Needs attention";
    case "stale":
      return "Stale";
    default:
      return "Observed";
  }
}

interface MetricCardProps {
  label: string;
  value: string;
  detail: string;
}

function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

export default function Dashboard() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<RepositoryDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [runningAction, setRunningAction] = useState<"sync" | "test" | "submit" | null>(null);
  const [switchingBranch, setSwitchingBranch] = useState<string | null>(null);
  const [branchesOpen, setBranchesOpen] = useState(false);
  const [notice, setNotice] = useState<RepoCommandResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    void loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedRepoId === null) {
      return;
    }
    void loadSnapshot(selectedRepoId);
  }, [selectedRepoId]);

  async function loadInitialData() {
    try {
      setLoading(true);
      setError(null);
      const repoData = await getRepos();
      setRepos(repoData);

      if (repoData.length === 0) {
        setSelectedRepoId(null);
        setSnapshot(null);
        return;
      }

      const stored = window.localStorage.getItem("forge:selected-repo");
      const preferredRepoId = stored ? Number(stored) : null;
      const nextRepoId =
        preferredRepoId && repoData.some((repo) => repo.id === preferredRepoId)
          ? preferredRepoId
          : repoData[0].id;
      setSelectedRepoId(nextRepoId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function loadSnapshot(repoId: number, branch?: string) {
    try {
      setSnapshotLoading(true);
      setError(null);
      const data = await getRepoDashboard(repoId, branch);
      setSnapshot(data);
      window.localStorage.setItem("forge:selected-repo", String(repoId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repository state");
    } finally {
      setSnapshotLoading(false);
    }
  }

  async function refreshDashboard(branch?: string) {
    if (selectedRepoId === null) {
      return;
    }
    await loadSnapshot(selectedRepoId, branch);
  }

  async function handleAction(action: "sync" | "test" | "submit") {
    if (selectedRepoId === null) {
      return;
    }

    try {
      setRunningAction(action);
      setError(null);
      const result = await runRepoAction(selectedRepoId, action);
      setNotice(result);
      await refreshDashboard();
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to run ${action}`;
      setNotice({
        action,
        success: false,
        output: message,
      });
      setError(message);
    } finally {
      setRunningAction(null);
    }
  }

  async function handleSwitchBranch(branchName: string) {
    if (selectedRepoId === null) {
      return;
    }

    if (snapshot?.current_branch === branchName) {
      await loadSnapshot(selectedRepoId, branchName);
      return;
    }

    try {
      setSwitchingBranch(branchName);
      setError(null);
      await switchRepoBranch(selectedRepoId, branchName);
      setNotice({
        action: "sync",
        success: true,
        output: `Switched repository context to ${branchName}.`,
      });
      await refreshDashboard(branchName);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to switch to ${branchName}`;
      setError(message);
      setNotice({
        action: "sync",
        success: false,
        output: message,
      });
    } finally {
      setSwitchingBranch(null);
    }
  }

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  if (repos.length === 0) {
    return (
      <div className="dashboard-stack">
        <section className="panel">
          <div className="empty-state">
            <div className="empty-state-title">No repositories tracked yet</div>
            <div className="empty-state-text">
              Add a repository to start using the Forge dashboard.
            </div>
            <button className="action-button" onClick={() => navigate("/repos")}>
              Add repository
            </button>
          </div>
        </section>
      </div>
    );
  }

  const selectedRepo = repos.find((repo) => repo.id === selectedRepoId) ?? repos[0];
  const selectedBranch =
    snapshot?.branch_graph.find((branch) => branch.branch_name === snapshot.selected_branch) ?? null;
  const branchRadar = [...(snapshot?.branch_graph ?? [])].sort((left, right) => {
    const priorityDelta = getBranchPriority(left) - getBranchPriority(right);
    if (priorityDelta !== 0) {
      return priorityDelta;
    }
    return left.branch_name.localeCompare(right.branch_name);
  });
  const readinessChecks = snapshot
    ? [
        {
          label: "Synced with base",
          done: snapshot.readiness.synced_with_base,
          detail: `${snapshot.selected_branch} vs ${snapshot.repository.base_branch}`,
        },
        {
          label: "Tests passing",
          done: snapshot.readiness.tests_passing,
          detail: selectedBranch?.test_status ?? "unknown",
        },
        {
          label: "Coverage sufficient",
          done: snapshot.readiness.coverage_sufficient,
          detail: `${snapshot.coverage.coverage_percent}% estimated coverage`,
        },
        {
          label: "No conflicts",
          done: snapshot.readiness.no_conflicts,
          detail: "Checked against the base branch",
        },
      ]
    : [];

  return (
    <div className="dashboard-stack">
      {notice && (
        <section className={`notice-panel ${notice.success ? "notice-success" : "notice-danger"}`}>
          <div className="notice-head">
            <strong>{formatActionName(notice.action)}</strong>
            <button className="ghost-button" onClick={() => setNotice(null)}>
              Dismiss
            </button>
          </div>
          <pre>{notice.output || "No command output was returned."}</pre>
        </section>
      )}

      {error && !notice && <div className="error">{error}</div>}

      <section className="panel workspace-panel">
        <div className="workspace-header">
          <div>
            <p className="section-label">Workspace</p>
            <h2>{selectedRepo.name}</h2>
            <p className="workspace-path">{selectedRepo.local_path}</p>
          </div>

          <div className="workspace-links">
            <button className="ghost-button" onClick={() => navigate("/repos")}>
              Repositories
            </button>
            <button className="ghost-button" onClick={() => navigate("/test-events")}>
              Test events
            </button>
            <button className="ghost-button" onClick={() => navigate(`/repos/${selectedRepo.id}`)}>
              Repository detail
            </button>
          </div>
        </div>

        <div className="command-grid">
          <label className="command-field">
            <span>Repository</span>
            <select
              className="select-field"
              value={selectedRepoId ?? ""}
              onChange={(event) => setSelectedRepoId(Number(event.target.value))}
            >
              {repos.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name}
                </option>
              ))}
            </select>
          </label>

          <label className="command-field">
            <span>Branch</span>
            <select
              className="select-field"
              value={snapshot?.selected_branch ?? snapshot?.current_branch ?? ""}
              disabled={!snapshot || Boolean(switchingBranch) || snapshotLoading}
              onChange={(event) => void handleSwitchBranch(event.target.value)}
            >
              {(snapshot?.branch_graph ?? []).map((branch) => (
                <option key={branch.branch_name} value={branch.branch_name}>
                  {branch.branch_name}
                </option>
              ))}
            </select>
          </label>

          <div className="command-meta">
            <span className="meta-chip">Base: {selectedRepo.base_branch}</span>
            <span className="meta-chip">
              Last scanned: {formatDateTime(snapshot?.repository.last_scanned_at ?? selectedRepo.last_scanned_at)}
            </span>
          </div>

          <div className="command-actions">
            <button
              className="ghost-button"
              disabled={runningAction !== null || snapshotLoading}
              onClick={() => void handleAction("sync")}
            >
              {runningAction === "sync" ? "Syncing..." : "Sync"}
            </button>
            <button
              className="ghost-button"
              disabled={runningAction !== null || snapshotLoading}
              onClick={() => void handleAction("test")}
            >
              {runningAction === "test" ? "Testing..." : "Test"}
            </button>
            <button
              className="action-button"
              disabled={runningAction !== null || snapshotLoading}
              onClick={() => void handleAction("submit")}
            >
              {runningAction === "submit" ? "Submitting..." : "Submit"}
            </button>
            <button className="ghost-button" onClick={() => setBranchesOpen(true)}>
              View branches
            </button>
          </div>
        </div>
      </section>

      {snapshotLoading || !snapshot ? (
        <div className="loading">Refreshing repository state...</div>
      ) : (
        <div className="dashboard-layout">
          <div className="dashboard-main">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">Status</p>
                  <h2>{snapshot.selected_branch}</h2>
                </div>
                <div className="status-badges">
                  <span className={`status-pill ${snapshot.sync_status === "Synced" ? "status-success" : "status-warning"}`}>
                    {snapshot.sync_status}
                  </span>
                  <span
                    className={`status-pill ${
                      selectedBranch?.test_status === "passing"
                        ? "status-success"
                        : selectedBranch?.test_status === "failing"
                          ? "status-danger"
                          : "status-muted"
                    }`}
                  >
                    Tests {selectedBranch?.test_status ?? "unknown"}
                  </span>
                </div>
              </div>

              <div className="metric-grid">
                <MetricCard
                  label="Current branch"
                  value={snapshot.current_branch}
                  detail="Active working branch"
                />
                <MetricCard
                  label="Ahead / behind"
                  value={`${selectedBranch?.commits_ahead ?? 0} / ${selectedBranch?.commits_behind ?? 0}`}
                  detail={`Relative to ${snapshot.repository.base_branch}`}
                />
                <MetricCard
                  label="Coverage"
                  value={`${snapshot.coverage.coverage_percent}%`}
                  detail={`${snapshot.coverage.tested_public_functions} tested public functions`}
                />
                <MetricCard
                  label="PR status"
                  value={selectedBranch?.pr_status ?? "none"}
                  detail={selectedBranch ? getHealthLabel(selectedBranch.health) : "Observed"}
                />
              </div>

              <div className="status-sections">
                <div className="status-section">
                  <div className="subsection-title">Ready to submit</div>
                  <div className="readiness-list">
                    {readinessChecks.map((item) => (
                      <div key={item.label} className="readiness-item">
                        <div className={`readiness-mark ${item.done ? "is-done" : "is-pending"}`}>
                          {item.done ? "✓" : "!"}
                        </div>
                        <div>
                          <div className="readiness-title">{item.label}</div>
                          <div className="readiness-detail">{item.detail}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="status-section">
                  <div className="subsection-title">Coverage hotspots</div>
                  <div className="coverage-summary">
                    <div className="coverage-bar">
                      <div
                        className="coverage-bar-fill"
                        style={{ width: `${snapshot.coverage.coverage_percent}%` }}
                      />
                    </div>
                    <div className="untested-list">
                      {snapshot.coverage.untested_areas.length === 0 ? (
                        <div className="empty-inline">No hotspots flagged.</div>
                      ) : (
                        snapshot.coverage.untested_areas.slice(0, 3).map((area) => (
                          <div key={area.path} className="untested-item">
                            <span>{area.path}</span>
                            <strong>{area.untested_functions}</strong>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">Commits</p>
                  <h2>Recent timeline</h2>
                </div>
              </div>

              {snapshot.commit_timeline.length === 0 ? (
                <div className="empty-state compact-empty">
                  <div className="empty-state-title">No commits captured yet</div>
                  <div className="empty-state-text">Scan the repository to refresh the timeline.</div>
                </div>
              ) : (
                <div className="timeline-list">
                  {snapshot.commit_timeline.map((commit) => (
                    <article key={commit.commit_hash} className="timeline-item">
                      <div className="timeline-dot" />
                      <div className="timeline-body">
                        <div className="timeline-title-row">
                          <strong>{commit.message}</strong>
                          <span className="commit-hash">{commit.commit_hash.slice(0, 8)}</span>
                        </div>
                        <div className="timeline-meta">
                          {commit.author} · {new Date(commit.timestamp).toLocaleString()}
                        </div>
                        <div className="timeline-changes">
                          {commit.files_changed_count} files · <span>+{commit.lines_added}</span> ·{" "}
                          <span>-{commit.lines_removed}</span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>

          <aside className="dashboard-sidebar">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">Branches</p>
                  <h2>Context</h2>
                </div>
                <button className="ghost-button" onClick={() => setBranchesOpen(true)}>
                  Graph
                </button>
              </div>

              <div className="branch-list">
                {branchRadar.slice(0, 5).map((branch) => (
                  <button
                    key={branch.branch_name}
                    className={`branch-row ${branch.branch_name === snapshot.current_branch ? "is-current" : ""}`}
                    onClick={() => void handleSwitchBranch(branch.branch_name)}
                  >
                    <div className="branch-row-main">
                      <div className="branch-row-name">{branch.branch_name}</div>
                      <div className="branch-row-meta">
                        {branch.commits_ahead} ahead · {branch.commits_behind} behind
                      </div>
                    </div>
                    <span className={`health-pill health-${branch.health}`}>
                      {getHealthLabel(branch.health)}
                    </span>
                  </button>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">Activity</p>
                  <h2>Recent events</h2>
                </div>
              </div>

              <div className="activity-list">
                {snapshot.activity_feed.slice(0, 6).map((item) => (
                  <article key={`${item.kind}-${item.timestamp}-${item.title}`} className="activity-item">
                    <div className={`activity-marker activity-${item.status}`} />
                    <div className="activity-body">
                      <div className="activity-row">
                        <strong>{item.title}</strong>
                        <span>{new Date(item.timestamp).toLocaleString()}</span>
                      </div>
                      <p>{item.detail}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </aside>
        </div>
      )}

      <BranchGraphModal
        open={branchesOpen}
        branches={snapshot?.branch_graph ?? []}
        selectedBranch={snapshot?.selected_branch ?? ""}
        switchingBranch={switchingBranch}
        onClose={() => setBranchesOpen(false)}
        onSwitchBranch={(branchName) => void handleSwitchBranch(branchName)}
      />
    </div>
  );
}
