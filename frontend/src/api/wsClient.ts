import { useState, useEffect, useCallback, useRef } from 'react';
import {
  type ClientMessage,
  type ServerMessage,
  parseServerMessage,
} from './messageSchemas';

type MessageHandler = (message: ServerMessage) => void;

interface UseWebSocketReturn {
  isConnected: boolean;
  serverTime: string | null;
  send: (message: ClientMessage) => void;
  subscribe: (messageType: string, handler: MessageHandler) => () => void;
  createSession: () => Promise<void>;
  attachSession: (sessionId: string) => Promise<void>;
  terminateSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, name: string) => Promise<void>;
  listSessions: () => void;
}

const WS_URL = `ws://${window.location.hostname}:5000/ws`;
const RECONNECT_DELAY = 1000;
const MAX_RECONNECT_ATTEMPTS = 30;

export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [serverTime, setServerTime] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const subscribersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const message = parseServerMessage(data);

        if (!message) {
          console.warn('Received invalid message:', data);
          return;
        }

        // Handle server.hello specially
        if (message.type === 'server.hello') {
          setServerTime(message.serverTime);
        }

        // Notify subscribers
        const handlers = subscribersRef.current.get(message.type);
        if (handlers) {
          handlers.forEach((handler) => {
            try {
              handler(message);
            } catch (err) {
              console.error('Message handler error:', err);
            }
          });
        }

        // Also notify 'all' subscribers
        const allHandlers = subscribersRef.current.get('*');
        if (allHandlers) {
          allHandlers.forEach((handler) => {
            try {
              handler(message);
            } catch (err) {
              console.error('Message handler error:', err);
            }
          });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      console.log('WebSocket disconnected');

      // Attempt reconnect
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++;
        console.log(
          `Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`
        );
        reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  const subscribe = useCallback(
    (messageType: string, handler: MessageHandler): (() => void) => {
      if (!subscribersRef.current.has(messageType)) {
        subscribersRef.current.set(messageType, new Set());
      }
      subscribersRef.current.get(messageType)!.add(handler);

      return () => {
        const handlers = subscribersRef.current.get(messageType);
        if (handlers) {
          handlers.delete(handler);
          if (handlers.size === 0) {
            subscribersRef.current.delete(messageType);
          }
        }
      };
    },
    []
  );

  const createSession = useCallback(async () => {
    send({ type: 'session.create' });
  }, [send]);

  const attachSession = useCallback(
    async (sessionId: string) => {
      send({ type: 'session.attach', sessionId });
    },
    [send]
  );

  const terminateSession = useCallback(
    async (sessionId: string) => {
      send({ type: 'session.terminate', sessionId });
    },
    [send]
  );

  const renameSession = useCallback(
    async (sessionId: string, name: string) => {
      send({ type: 'session.rename', sessionId, name });
    },
    [send]
  );

  const listSessions = useCallback(() => {
    send({ type: 'session.list' });
  }, [send]);

  return {
    isConnected,
    serverTime,
    send,
    subscribe,
    createSession,
    attachSession,
    terminateSession,
    renameSession,
    listSessions,
  };
}
