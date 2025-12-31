# Suggestions for Future Improvements

This document contains suggestions for improving and extending the Copilot Terminal Carousel application.

## High Priority

### 1. Session Reconnection on Server Restart

**Current State**: When the server restarts, all PTY processes are lost and sessions cannot be reconnected.

**Suggestion**: Implement session restoration from persisted state:
- Store PTY process state before shutdown
- Attempt to reattach to running processes on startup
- Provide clear UI indication of session status

### 2. Terminal Scrollback Persistence

**Current State**: Terminal scrollback is only stored in the browser and lost on page refresh.

**Suggestion**: 
- Store scrollback buffer in the backend
- Send scrollback history on session attach
- Implement lazy loading for large scrollback buffers

### 3. Multiple Client Support

**Current State**: Each WebSocket connection is treated independently.

**Suggestion**: 
- Implement proper multi-client session sharing
- Broadcast terminal output to all attached clients
- Show other clients attached to the same session

## Medium Priority

### 4. Session Search and Filtering

**Current State**: Sessions are listed chronologically without search capability.

**Suggestion**:
- Add session search by ID or creation date
- Add filtering by status (running/exited)
- Add session tagging for organization

### 5. Terminal Themes

**Current State**: Terminal uses a fixed dark theme.

**Suggestion**:
- Add theme selection (dark, light, high contrast)
- Support custom theme definition
- Persist theme preference

### 6. Copy/Paste Improvements

**Current State**: Basic copy/paste via browser selection.

**Suggestion**:
- Add dedicated copy button for last output
- Implement paste confirmation for large content
- Support rich text copying with formatting

### 7. Session Export

**Current State**: Transcripts are only available as JSONL files.

**Suggestion**:
- Add export to plain text
- Add export to HTML with ANSI rendering
- Add export to Markdown format

### 8. Keyboard Shortcuts

**Current State**: No application-level keyboard shortcuts.

**Suggestion**:
- `Ctrl+Shift+T` - New session
- `Ctrl+Shift+W` - Close session
- `Ctrl+Tab` / `Ctrl+Shift+Tab` - Switch sessions
- `Ctrl+K` - Clear terminal

## Lower Priority

### 9. Split Terminal View

**Current State**: Only one terminal visible at a time.

**Suggestion**:
- Allow horizontal/vertical split panes
- Compare output from multiple sessions
- Flexible layout system

### 10. Session Templates

**Current State**: All sessions start with the same configuration.

**Suggestion**:
- Define session templates with preset configurations
- Quick-create from templates
- Share templates between users

### 11. Audit Logging

**Current State**: Basic JSONL logging exists but no audit trail.

**Suggestion**:
- Add detailed audit logging for security review
- Log client connections with timestamps
- Track session access patterns

### 12. Metrics and Monitoring

**Current State**: No metrics collection.

**Suggestion**:
- Add Prometheus metrics endpoint
- Track session creation/termination rates
- Monitor WebSocket connection health
- Add performance metrics (latency, throughput)

### 13. API Token Authentication

**Current State**: No authentication mechanism.

**Suggestion**:
- Implement optional API token authentication
- Token generation and management
- Rate limiting per token

### 14. Remote Access Mode

**Current State**: Localhost only by default.

**Suggestion**:
- Add TLS support for remote access
- Implement proper authentication when exposed
- Add IP whitelist/blacklist
- Consider WebSocket secure (wss://) only

### 15. Docker Improvements

**Current State**: Basic Windows container support.

**Suggestion**:
- Multi-stage builds for smaller images
- Docker Compose for development
- Kubernetes deployment manifests
- Health check improvements

## Technical Debt

### 16. Frontend State Management

**Current State**: State managed with React hooks.

**Suggestion**:
- Consider Redux or Zustand for complex state
- Implement proper error boundaries
- Add loading states for all async operations

### 17. Backend Error Handling

**Current State**: Basic error handling with generic messages.

**Suggestion**:
- Implement structured error types
- Add error codes documentation
- Improve error messages for debugging

### 18. Test Coverage

**Current State**: Unit and integration tests exist.

**Suggestion**:
- Add performance regression tests
- Add stress testing for concurrent sessions
- Add security-focused tests
- Increase coverage to 90%+

### 19. Documentation

**Current State**: Basic documentation available.

**Suggestion**:
- Add API documentation (OpenAPI/Swagger)
- Add developer guide for contributions
- Add troubleshooting runbook
- Add video tutorials

### 20. Accessibility

**Current State**: Basic accessibility support.

**Suggestion**:
- Add ARIA labels for all interactive elements
- Ensure keyboard navigation works fully
- Test with screen readers
- Add high contrast mode

## Performance Optimizations

### 21. WebSocket Message Batching

**Current State**: Each PTY output chunk is sent immediately.

**Suggestion**:
- Batch small output chunks
- Add configurable batching delay
- Reduce WebSocket message overhead

### 22. Frontend Bundle Optimization

**Current State**: Standard Vite build.

**Suggestion**:
- Analyze and optimize bundle size
- Implement code splitting
- Lazy load non-critical components
- Add service worker for caching

### 23. Memory Management

**Current State**: Sessions stay in memory until termination.

**Suggestion**:
- Implement session eviction for exited sessions
- Add configurable memory limits
- Monitor and alert on memory usage

## Integration Ideas

### 24. GitHub Integration

**Suggestion**:
- Link sessions to GitHub repositories
- Display repository context in session
- Quick commands for common git operations

### 25. IDE Integration

**Suggestion**:
- VS Code extension for session management
- Open files from terminal in editor
- Sync terminal state with IDE

### 26. Notification System

**Suggestion**:
- Desktop notifications for long-running commands
- Alert when session exits
- Browser notifications for background tabs
