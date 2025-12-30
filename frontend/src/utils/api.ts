import type { Repository, Branch, Commit, TestEvent, BranchMetrics } from '../types';

const API_BASE = '/api';

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}

export async function getRepos(): Promise<Repository[]> {
  return fetchAPI<Repository[]>('/repos');
}

export async function addRepo(localPath: string): Promise<Repository> {
  const response = await fetch(`${API_BASE}/repos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ local_path: localPath }),
  });
  if (!response.ok) {
    throw new Error(`Failed to add repo: ${response.statusText}`);
  }
  return response.json();
}

export async function scanRepo(repoId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/repos/${repoId}/scan`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to scan repo: ${response.statusText}`);
  }
}

export async function getRepoBranches(repoId: number): Promise<Branch[]> {
  return fetchAPI<Branch[]>(`/repos/${repoId}/branches`);
}

export async function getBranchCommits(branchId: number): Promise<Commit[]> {
  return fetchAPI<Commit[]>(`/branches/${branchId}/commits`);
}

export async function getBranchMetrics(branchId: number): Promise<BranchMetrics> {
  return fetchAPI<BranchMetrics>(`/branches/${branchId}/metrics`);
}

export async function getTestEvents(repoId?: number, branchId?: number): Promise<TestEvent[]> {
  const params = new URLSearchParams();
  if (repoId) params.append('repo_id', repoId.toString());
  if (branchId) params.append('branch_id', branchId.toString());
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchAPI<TestEvent[]>(`/test-events${query}`);
}

