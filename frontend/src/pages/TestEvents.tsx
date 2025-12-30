import { useEffect, useState } from 'react';
import { getTestEvents } from '../utils/api';
import type { TestEvent } from '../types';

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
      console.error('Failed to load events:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="card">Loading test events...</div>;
  }

  return (
    <div>
      <div className="card">
        <h2>Test Generation Events</h2>
        {events.length === 0 ? (
          <p style={{ color: '#666' }}>No test events found.</p>
        ) : (
          <ul className="list" style={{ marginTop: '15px' }}>
            {events.map((event) => (
              <li key={event.id} className="list-item">
                <div style={{ fontWeight: '500' }}>
                  {event.command_used}
                  <span className={`badge badge-${event.status === 'success' ? 'success' : 'danger'}`}>
                    {event.status}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {event.ai_provider && `Provider: ${event.ai_provider}`}
                  {event.model && ` | Model: ${event.model}`}
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {new Date(event.timestamp).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

