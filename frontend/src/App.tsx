import { useState, useCallback, useEffect } from 'react';
import { SessionList } from './components/SessionList';
import { TerminalPane } from './components/TerminalPane';
import { StatusBar } from './components/StatusBar';
import { useWebSocket } from './api/wsClient';
import type { SessionIndexEntry } from './api/messageSchemas';

export default function App() {
  const [sessions, setSessions] = useState<SessionIndexEntry[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  
  const {
    isConnected,
    serverTime,
    send,
    subscribe,
    createSession,
    attachSession,
    terminateSession,
    listSessions,
  } = useWebSocket();

  // Load sessions on connect
  useEffect(() => {
    if (isConnected) {
      listSessions();
    }
  }, [isConnected, listSessions]);

  // Subscribe to session list updates
  useEffect(() => {
    const unsubscribe = subscribe('session.list.result', (message) => {
      if (message.type === 'session.list.result') {
        setSessions(message.sessions);
      }
    });
    return unsubscribe;
  }, [subscribe]);

  // Subscribe to session created
  useEffect(() => {
    const unsubscribe = subscribe('session.created', (message) => {
      if (message.type === 'session.created') {
        setSessions((prev) => [
          {
            sessionId: message.session.sessionId,
            status: message.session.status,
            createdAt: message.session.createdAt,
            lastActivityAt: message.session.lastActivityAt,
          },
          ...prev,
        ]);
        setSelectedSessionId(message.session.sessionId);
      }
    });
    return unsubscribe;
  }, [subscribe]);

  // Subscribe to session exited
  useEffect(() => {
    const unsubscribe = subscribe('session.exited', (message) => {
      if (message.type === 'session.exited') {
        setSessions((prev) =>
          prev.map((s) =>
            s.sessionId === message.sessionId ? { ...s, status: 'exited' as const } : s
          )
        );
      }
    });
    return unsubscribe;
  }, [subscribe]);

  const handleNewSession = useCallback(async () => {
    await createSession();
  }, [createSession]);

  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      setSelectedSessionId(sessionId);
      await attachSession(sessionId);
    },
    [attachSession]
  );

  const handleTerminateSession = useCallback(
    async (sessionId: string) => {
      await terminateSession(sessionId);
    },
    [terminateSession]
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 Copilot Terminal Carousel</h1>
        <StatusBar isConnected={isConnected} serverTime={serverTime} />
      </header>

      <main className="app-main">
        <aside className="session-sidebar">
          <button
            className="new-session-btn"
            onClick={handleNewSession}
            disabled={!isConnected}
          >
            + New Session
          </button>
          <SessionList
            sessions={sessions}
            selectedSessionId={selectedSessionId}
            onSelectSession={handleSelectSession}
            onTerminateSession={handleTerminateSession}
          />
        </aside>

        <section className="terminal-container">
          {selectedSessionId ? (
            <TerminalPane
              sessionId={selectedSessionId}
              send={send}
              subscribe={subscribe}
            />
          ) : (
            <div className="no-session">
              <p>No session selected</p>
              <p>Click "New Session" to start a Copilot terminal</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
