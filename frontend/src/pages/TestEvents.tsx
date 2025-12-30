import { useEffect, useState } from "react";
import { getTestEvents } from "../utils/api";
import type { TestEvent } from "../types";

export default function TestEvents() {
  const [events, setEvents] = useState<TestEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvents();
  }, []);

  async function loadEvents() {
    try {
      setLoading(true);
      const data = await getTestEvents();
      setEvents(data);
    } catch (err) {
      console.error("Failed to load events:", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading test events...</div>;
  }

  const successCount = events.filter((e) => e.status === "success").length;
  const failureCount = events.filter((e) => e.status === "failure").length;

  return (
    <div>
      {events.length > 0 && (
        <div className="stats-grid" style={{ marginBottom: "24px" }}>
          <div className="stat-card">
            <div className="stat-card-icon">📊</div>
            <div className="stat-card-value">{events.length}</div>
            <div className="stat-card-label">Total Events</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-icon">✅</div>
            <div className="stat-card-value">{successCount}</div>
            <div className="stat-card-label">Successful</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-icon">❌</div>
            <div className="stat-card-value">{failureCount}</div>
            <div className="stat-card-label">Failed</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-icon">🎯</div>
            <div className="stat-card-value">
              {events.length > 0
                ? Math.round((successCount / events.length) * 100)
                : 0}
              %
            </div>
            <div className="stat-card-label">Success Rate</div>
          </div>
        </div>
      )}

      <div className="card">
        <h2>🧪 Test Generation Events</h2>
        {events.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🧪</div>
            <div className="empty-state-title">No test events found</div>
            <div className="empty-state-text">
              Run forge create-tests or forge submit to see activity
            </div>
          </div>
        ) : (
          <div style={{ marginTop: "20px" }}>
            {events.map((event) => (
              <div key={event.id} className="list-item">
                <div className="list-item-title">
                  {event.command_used}
                  <span
                    className={`badge badge-${
                      event.status === "success" ? "success" : "danger"
                    }`}
                  >
                    {event.status}
                  </span>
                </div>
                <div className="list-item-subtitle">
                  {event.ai_provider && (
                    <>
                      <strong>Provider:</strong> {event.ai_provider}
                      {event.model && " • "}
                    </>
                  )}
                  {event.model && (
                    <>
                      <strong>Model:</strong> {event.model}
                    </>
                  )}
                </div>
                <div className="list-item-subtitle">
                  {new Date(event.timestamp).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
