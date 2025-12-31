import type { SessionIndexEntry } from '../api/messageSchemas';

interface SessionListProps {
  sessions: SessionIndexEntry[];
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onTerminateSession: (sessionId: string) => void;
}

export function SessionList({
  sessions,
  selectedSessionId,
  onSelectSession,
  onTerminateSession,
}: SessionListProps) {
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString();
    } catch {
      return dateStr;
    }
  };

  if (sessions.length === 0) {
    return (
      <div className="session-list empty">
        <p>No sessions</p>
      </div>
    );
  }

  return (
    <ul className="session-list">
      {sessions.map((session) => (
        <li
          key={session.sessionId}
          className={`session-item ${
            session.sessionId === selectedSessionId ? 'selected' : ''
          } ${session.status}`}
          onClick={() => onSelectSession(session.sessionId)}
        >
          <div className="session-info">
            <span className="session-id" title={session.sessionId}>
              {session.sessionId.slice(0, 8)}...
            </span>
            <span className={`session-status ${session.status}`}>
              {session.status === 'running' ? '🟢' : '🔴'} {session.status}
            </span>
          </div>
          <div className="session-meta">
            <span className="session-time">
              Created: {formatDate(session.createdAt)}
            </span>
          </div>
          {session.status === 'running' && (
            <button
              className="terminate-btn"
              onClick={(e) => {
                e.stopPropagation();
                onTerminateSession(session.sessionId);
              }}
              title="Terminate session"
            >
              ✕
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
