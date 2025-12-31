interface StatusBarProps {
  isConnected: boolean;
  serverTime: string | null;
}

export function StatusBar({ isConnected, serverTime }: StatusBarProps) {
  return (
    <div className="status-bar">
      <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
        {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
      </span>
      {serverTime && (
        <span className="server-time">
          Server: {new Date(serverTime).toLocaleString()}
        </span>
      )}
    </div>
  );
}
