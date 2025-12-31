import { useEffect, useRef, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import type { ClientMessage, ServerMessage } from '../api/messageSchemas';
import '@xterm/xterm/css/xterm.css';
import '../styles/terminal.css';

interface TerminalPaneProps {
  sessionId: string;
  sessionName?: string | null;
  send: (message: ClientMessage) => void;
  subscribe: (
    messageType: string,
    handler: (message: ServerMessage) => void
  ) => () => void;
}

export function TerminalPane({ sessionId, sessionName, send, subscribe }: TerminalPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);

  // Handle terminal output
  const handleOutput = useCallback(
    (message: ServerMessage) => {
      if (
        message.type === 'term.out' &&
        message.sessionId === sessionId &&
        terminalRef.current
      ) {
        terminalRef.current.write(message.data);
      }
    },
    [sessionId]
  );

  // Handle session exit
  const handleExit = useCallback(
    (message: ServerMessage) => {
      if (
        message.type === 'session.exited' &&
        message.sessionId === sessionId &&
        terminalRef.current
      ) {
        terminalRef.current.write(
          `\r\n\x1b[31m[Session exited with code ${message.exitCode ?? 'unknown'}]\x1b[0m\r\n`
        );
      }
    },
    [sessionId]
  );

  // Initialize terminal
  useEffect(() => {
    if (!containerRef.current) return;

    // Create terminal
    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Consolas, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#aeafad',
        cursorAccent: '#1e1e1e',
        selectionBackground: '#264f78',
        black: '#1e1e1e',
        red: '#f44747',
        green: '#6a9955',
        yellow: '#dcdcaa',
        blue: '#569cd6',
        magenta: '#c586c0',
        cyan: '#4ec9b0',
        white: '#d4d4d4',
        brightBlack: '#808080',
        brightRed: '#f44747',
        brightGreen: '#6a9955',
        brightYellow: '#dcdcaa',
        brightBlue: '#569cd6',
        brightMagenta: '#c586c0',
        brightCyan: '#4ec9b0',
        brightWhite: '#ffffff',
      },
    });

    // Add addons
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);

    // Open terminal
    terminal.open(containerRef.current);
    fitAddon.fit();

    terminalRef.current = terminal;
    fitAddonRef.current = fitAddon;

    // Handle input
    terminal.onData((data) => {
      send({
        type: 'term.in',
        sessionId,
        data,
      });
    });

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      if (fitAddonRef.current && terminalRef.current) {
        fitAddonRef.current.fit();
        send({
          type: 'term.resize',
          sessionId,
          cols: terminalRef.current.cols,
          rows: terminalRef.current.rows,
        });
      }
    });

    resizeObserver.observe(containerRef.current);

    // Initial resize notification
    send({
      type: 'term.resize',
      sessionId,
      cols: terminal.cols,
      rows: terminal.rows,
    });

    return () => {
      resizeObserver.disconnect();
      terminal.dispose();
      terminalRef.current = null;
      fitAddonRef.current = null;
    };
  }, [sessionId, send]);

  // Subscribe to output
  useEffect(() => {
    const unsubscribeOutput = subscribe('term.out', handleOutput);
    const unsubscribeExit = subscribe('session.exited', handleExit);

    return () => {
      unsubscribeOutput();
      unsubscribeExit();
    };
  }, [subscribe, handleOutput, handleExit]);

  return (
    <div className="terminal-pane">
      <div className="terminal-header">
        <span className="terminal-title">Session: {sessionName || sessionId.slice(0, 8) + '...'}</span>
      </div>
      <div ref={containerRef} className="terminal-content" />
    </div>
  );
}
