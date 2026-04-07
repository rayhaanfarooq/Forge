import type {
  Branch,
  BranchMetrics,
  Commit,
  RepoCommandResult,
  Repository,
  RepositoryDashboard,
  Stats,
  TestEvent,
} from "../types";

const API_BASE = "/api";

async function fetchAPI<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // Fall back to status text when the backend doesn't return JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function getRepos(): Promise<Repository[]> {
  return fetchAPI<Repository[]>("/repos");
}

export async function addRepo(localPath: string): Promise<Repository> {
  return fetchAPI<Repository>("/repos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ local_path: localPath }),
  });
}

export async function scanRepo(repoId: number): Promise<void> {
  await fetchAPI<{ message: string }>(`/repos/${repoId}/scan`, {
    method: "POST",
  });
}

export async function getRepoBranches(repoId: number): Promise<Branch[]> {
  return fetchAPI<Branch[]>(`/repos/${repoId}/branches`);
}

export async function getRepoDashboard(
  repoId: number,
  branch?: string
): Promise<RepositoryDashboard> {
  const query = branch ? `?branch=${encodeURIComponent(branch)}` : "";
  return fetchAPI<RepositoryDashboard>(`/repos/${repoId}/dashboard${query}`);
}

export async function switchRepoBranch(
  repoId: number,
  branchName: string
): Promise<void> {
  await fetchAPI<{ message: string }>(`/repos/${repoId}/branches/switch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ branch_name: branchName }),
  });
}

export async function runRepoAction(
  repoId: number,
  action: "sync" | "test" | "submit"
): Promise<RepoCommandResult> {
  return fetchAPI<RepoCommandResult>(`/repos/${repoId}/actions/${action}`, {
    method: "POST",
  });
}

export async function getBranchCommits(branchId: number): Promise<Commit[]> {
  return fetchAPI<Commit[]>(`/branches/${branchId}/commits`);
}

export async function getBranchMetrics(
  branchId: number
): Promise<BranchMetrics> {
  return fetchAPI<BranchMetrics>(`/branches/${branchId}/metrics`);
}

export async function getTestEvents(
  repoId?: number,
  branchId?: number
): Promise<TestEvent[]> {
  const params = new URLSearchParams();
  if (repoId) {
    params.append("repo_id", repoId.toString());
  }
  if (branchId) {
    params.append("branch_id", branchId.toString());
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchAPI<TestEvent[]>(`/test-events${query}`);
}

export async function getStats(): Promise<Stats> {
  return fetchAPI<Stats>("/stats");
}
