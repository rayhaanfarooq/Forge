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

export interface CoverageArea {
  path: string;
  untested_functions: number;
}

export interface CoverageSummary {
  coverage_percent: number;
  total_public_functions: number;
  tested_public_functions: number;
  generated_test_files: number;
  source_files_scanned: number;
  untested_areas: CoverageArea[];
}

export interface Readiness {
  synced_with_base: boolean;
  tests_passing: boolean;
  coverage_sufficient: boolean;
  no_conflicts: boolean;
  ready_to_submit: boolean;
}

export interface ActivityItem {
  kind: string;
  title: string;
  detail: string;
  status: string;
  timestamp: string;
}

export interface BranchNode {
  id: number;
  branch_name: string;
  parent_branch: string | null;
  base_branch: string;
  status: string;
  health: string;
  is_current: boolean;
  commits_ahead: number;
  commits_behind: number;
  last_synced_at: string | null;
  latest_activity_at: string | null;
  latest_commit_message: string | null;
  latest_commit_hash: string | null;
  latest_commit_author: string | null;
  test_status: string;
  pr_status: string;
}

export interface TimelineCommit {
  commit_hash: string;
  author: string;
  timestamp: string;
  message: string;
  files_changed_count: number;
  lines_added: number;
  lines_removed: number;
}

export interface RepositoryDashboard {
  repository: Repository;
  current_branch: string;
  selected_branch: string;
  sync_status: string;
  branch_graph: BranchNode[];
  commit_timeline: TimelineCommit[];
  coverage: CoverageSummary;
  readiness: Readiness;
  activity_feed: ActivityItem[];
}

export interface RepoCommandResult {
  action: string;
  success: boolean;
  output: string;
}
