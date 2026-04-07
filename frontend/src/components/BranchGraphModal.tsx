import { useEffect, useState } from "react";
import type { BranchNode } from "../types";

interface BranchGraphModalProps {
  open: boolean;
  branches: BranchNode[];
  selectedBranch: string;
  switchingBranch: string | null;
  onClose: () => void;
  onSwitchBranch: (branchName: string) => void;
}

interface PositionedBranch extends BranchNode {
  x: number;
  y: number;
}

const NODE_WIDTH = 210;
const NODE_HEIGHT = 82;
const COLUMN_GAP = 270;
const ROW_GAP = 134;
const PADDING_X = 96;
const PADDING_Y = 96;

function getDepth(
  branch: BranchNode,
  byName: Map<string, BranchNode>,
  cache: Map<string, number>
): number {
  const cached = cache.get(branch.branch_name);
  if (cached !== undefined) {
    return cached;
  }

  if (
    !branch.parent_branch ||
    branch.parent_branch === branch.branch_name ||
    !byName.has(branch.parent_branch)
  ) {
    cache.set(branch.branch_name, 0);
    return 0;
  }

  const depth = getDepth(byName.get(branch.parent_branch)!, byName, cache) + 1;
  cache.set(branch.branch_name, depth);
  return depth;
}

function layoutBranches(branches: BranchNode[]) {
  const byName = new Map(branches.map((branch) => [branch.branch_name, branch]));
  const depthCache = new Map<string, number>();
  const grouped = new Map<number, BranchNode[]>();

  for (const branch of branches) {
    const depth = getDepth(branch, byName, depthCache);
    const current = grouped.get(depth) ?? [];
    current.push(branch);
    grouped.set(depth, current);
  }

  const positioned: PositionedBranch[] = [];
  let maxWidth = PADDING_X * 2 + NODE_WIDTH;
  let maxHeight = PADDING_Y * 2 + NODE_HEIGHT;

  const levels = [...grouped.keys()].sort((a, b) => a - b);
  for (const level of levels) {
    const branchesAtLevel = grouped.get(level) ?? [];
    branchesAtLevel.sort((a, b) => {
      if (a.is_current !== b.is_current) {
        return a.is_current ? -1 : 1;
      }
      return a.branch_name.localeCompare(b.branch_name);
    });

    branchesAtLevel.forEach((branch, index) => {
      const x = PADDING_X + level * COLUMN_GAP;
      const y = PADDING_Y + index * ROW_GAP + level * 20;
      positioned.push({ ...branch, x, y });
      maxWidth = Math.max(maxWidth, x + NODE_WIDTH + PADDING_X);
      maxHeight = Math.max(maxHeight, y + NODE_HEIGHT + PADDING_Y);
    });
  }

  return { positioned, width: maxWidth, height: maxHeight };
}

function describeHealth(health: string) {
  switch (health) {
    case "current":
      return "Current branch";
    case "healthy":
      return "Synced and passing";
    case "issues":
      return "Needs attention";
    case "stale":
      return "Inactive or stale";
    default:
      return "Observed";
  }
}

function formatRelative(timestamp: string | null) {
  if (!timestamp) {
    return "Not recorded";
  }

  const value = new Date(timestamp);
  return value.toLocaleString();
}

export default function BranchGraphModal({
  open,
  branches,
  selectedBranch,
  switchingBranch,
  onClose,
  onSwitchBranch,
}: BranchGraphModalProps) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragState, setDragState] = useState<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);
  const [inspectedBranch, setInspectedBranch] = useState(selectedBranch);

  useEffect(() => {
    if (!open) {
      return;
    }
    setScale(1);
    setOffset({ x: 0, y: 0 });
    setInspectedBranch(selectedBranch);
  }, [open, selectedBranch]);

  if (!open) {
    return null;
  }

  const { positioned, width, height } = layoutBranches(branches);
  const positionedByName = new Map(positioned.map((branch) => [branch.branch_name, branch]));
  const inspected =
    positionedByName.get(inspectedBranch) ??
    positionedByName.get(selectedBranch) ??
    positioned[0] ??
    null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-panel">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Branch Overview</p>
            <h2>Visual branch graph</h2>
          </div>
          <button className="ghost-button" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="graph-legend">
          <span className="legend-pill legend-current">Current</span>
          <span className="legend-pill legend-healthy">Healthy</span>
          <span className="legend-pill legend-issues">Issues</span>
          <span className="legend-pill legend-stale">Stale</span>
        </div>

        <div className="graph-workspace">
          <div className="graph-stage">
            <div className="graph-toolbar">
              <button className="ghost-button" onClick={() => setScale((value) => Math.min(value + 0.1, 1.8))}>
                Zoom in
              </button>
              <button className="ghost-button" onClick={() => setScale((value) => Math.max(value - 0.1, 0.6))}>
                Zoom out
              </button>
              <button className="ghost-button" onClick={() => {
                setScale(1);
                setOffset({ x: 0, y: 0 });
              }}>
                Reset
              </button>
            </div>

            <div
              className={`graph-canvas ${dragState ? "is-dragging" : ""}`}
              onMouseMove={(event) => {
                if (!dragState) {
                  return;
                }

                setOffset({
                  x: dragState.originX + (event.clientX - dragState.startX),
                  y: dragState.originY + (event.clientY - dragState.startY),
                });
              }}
              onMouseUp={() => setDragState(null)}
              onMouseLeave={() => setDragState(null)}
              onWheel={(event) => {
                event.preventDefault();
                const delta = event.deltaY > 0 ? -0.08 : 0.08;
                setScale((value) => Math.min(Math.max(value + delta, 0.6), 1.8));
              }}
            >
              <svg
                viewBox={`0 0 ${width} ${height}`}
                width="100%"
                height="100%"
                onMouseDown={(event) => {
                  if ((event.target as HTMLElement).closest("[data-node='true']")) {
                    return;
                  }

                  setDragState({
                    startX: event.clientX,
                    startY: event.clientY,
                    originX: offset.x,
                    originY: offset.y,
                  });
                }}
              >
                <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
                  {positioned.map((branch) => {
                    if (!branch.parent_branch || !positionedByName.has(branch.parent_branch)) {
                      return null;
                    }

                    const parent = positionedByName.get(branch.parent_branch)!;
                    const fromX = parent.x + NODE_WIDTH;
                    const fromY = parent.y + NODE_HEIGHT / 2;
                    const toX = branch.x;
                    const toY = branch.y + NODE_HEIGHT / 2;
                    const curve = Math.max((toX - fromX) / 2, 36);

                    return (
                      <path
                        key={`${parent.branch_name}-${branch.branch_name}`}
                        d={`M ${fromX} ${fromY} C ${fromX + curve} ${fromY}, ${toX - curve} ${toY}, ${toX} ${toY}`}
                        className="graph-edge"
                      />
                    );
                  })}

                  {positioned.map((branch) => (
                    <g
                      key={branch.branch_name}
                      data-node="true"
                      transform={`translate(${branch.x} ${branch.y})`}
                      className={`graph-node graph-node-${branch.health} ${
                        branch.branch_name === selectedBranch ? "is-selected" : ""
                      }`}
                      onMouseEnter={() => setInspectedBranch(branch.branch_name)}
                      onClick={() => {
                        setInspectedBranch(branch.branch_name);
                      }}
                    >
                      <rect rx="22" width={NODE_WIDTH} height={NODE_HEIGHT} />
                      <text x="22" y="30" className="graph-node-title">
                        {branch.branch_name}
                      </text>
                      <text x="22" y="52" className="graph-node-meta">
                        {describeHealth(branch.health)}
                      </text>
                      <text x="22" y="69" className="graph-node-meta">
                        {branch.commits_ahead} ahead · {branch.commits_behind} behind
                      </text>
                    </g>
                  ))}
                </g>
              </svg>
            </div>
          </div>

          <aside className="graph-detail">
            {inspected ? (
              <>
                <div className="detail-header">
                  <div>
                    <p className="detail-label">Inspecting</p>
                    <h3>{inspected.branch_name}</h3>
                  </div>
                  <span className={`health-pill health-${inspected.health}`}>
                    {describeHealth(inspected.health)}
                  </span>
                </div>

                <div className="detail-grid">
                  <div className="detail-item">
                    <span>Parent</span>
                    <strong>{inspected.parent_branch ?? inspected.base_branch}</strong>
                  </div>
                  <div className="detail-item">
                    <span>PR</span>
                    <strong>{inspected.pr_status}</strong>
                  </div>
                  <div className="detail-item">
                    <span>Tests</span>
                    <strong>{inspected.test_status}</strong>
                  </div>
                  <div className="detail-item">
                    <span>Last sync</span>
                    <strong>{formatRelative(inspected.last_synced_at)}</strong>
                  </div>
                </div>

                <div className="detail-block">
                  <p className="detail-label">Commit summary</p>
                  <div className="detail-callout">
                    {inspected.latest_commit_message ?? "No commits captured yet for this branch."}
                  </div>
                  <p className="detail-footnote">
                    {inspected.latest_commit_hash
                      ? `${inspected.latest_commit_hash.slice(0, 8)} by ${inspected.latest_commit_author ?? "Unknown"}`
                      : "Commit metadata becomes richer as the repository is scanned."}
                  </p>
                </div>

                <div className="detail-block">
                  <p className="detail-label">Divergence</p>
                  <div className="detail-callout">
                    {inspected.commits_ahead} commits ahead and {inspected.commits_behind} behind {inspected.base_branch}.
                  </div>
                </div>

                <button
                  className="action-button action-button-secondary"
                  disabled={Boolean(switchingBranch) || inspected.is_current}
                  onClick={() => onSwitchBranch(inspected.branch_name)}
                >
                  {inspected.is_current
                    ? "Already current"
                    : switchingBranch === inspected.branch_name
                      ? "Switching..."
                      : `Switch to ${inspected.branch_name}`}
                </button>
              </>
            ) : (
              <div className="empty-state compact-empty">
                <div className="empty-state-title">No branches to display</div>
                <div className="empty-state-text">
                  Scan a tracked repository to populate the graph.
                </div>
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
