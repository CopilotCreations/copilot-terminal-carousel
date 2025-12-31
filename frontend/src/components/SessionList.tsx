import { useState } from 'react';
import type { SessionIndexEntry } from '../api/messageSchemas';

interface SessionListProps {
  sessions: SessionIndexEntry[];
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onTerminateSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, name: string) => void;
}

export function SessionList({
  sessions,
  selectedSessionId,
  onSelectSession,
  onTerminateSession,
  onRenameSession,
}: SessionListProps) {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString();
    } catch {
      return dateStr;
    }
  };

  const handleStartEdit = (session: SessionIndexEntry, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(session.sessionId);
    setEditName(session.name || '');
  };

  const handleSaveEdit = (sessionId: string) => {
    if (editName.trim()) {
      onRenameSession(sessionId, editName.trim());
    }
    setEditingSessionId(null);
    setEditName('');
  };

  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setEditName('');
  };

  const handleKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      handleSaveEdit(sessionId);
    } else if (e.key === 'Escape') {
      handleCancelEdit();
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
            {editingSessionId === session.sessionId ? (
              <input
                type="text"
                className="session-name-input"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, session.sessionId)}
                onBlur={() => handleSaveEdit(session.sessionId)}
                onClick={(e) => e.stopPropagation()}
                autoFocus
                maxLength={100}
              />
            ) : (
              <span
                className="session-id"
                title={session.sessionId}
                onDoubleClick={(e) => handleStartEdit(session, e)}
              >
                {session.name || session.sessionId.slice(0, 8) + '...'}
              </span>
            )}
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
