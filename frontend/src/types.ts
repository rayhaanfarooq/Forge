export interface Repository {
  id: number;
  name: string;
  local_path: string;
  base_branch: string;
  date_added: string;
  last_scanned_at: string | null;
}

export interface Branch {
  id: number;
  repo_id: number;
  branch_name: string;
  parent_branch: string | null;
  base_branch: string;
  created_at: string;
  last_synced_at: string | null;
  status: string;
}

export interface Commit {
  id: number;
  commit_hash: string;
  repo_id: number;
  branch_id: number;
  author: string;
  timestamp: string;
  message: string;
  files_changed_count: number;
  lines_added: number;
  lines_removed: number;
}

export interface TestEvent {
  id: number;
  repo_id: number;
  branch_id: number | null;
  command_used: string;
  ai_provider: string | null;
  model: string | null;
  timestamp: string;
  status: string;
}

export interface BranchMetrics {
  commits_behind_base: number;
  days_since_last_sync: number | null;
  has_generated_tests: boolean;
}

export interface Stats {
  total_repos: number;
  total_branches: number;
  total_commits: number;
  total_test_events: number;
  successful_tests: number;
  failed_tests: number;
  active_branches: number;
  recent_activity: number;
}

