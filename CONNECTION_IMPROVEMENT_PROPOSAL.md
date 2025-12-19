# Connection Management Improvements for Midnite Solar Integration

## Current Issues

1. **Connection reset by peer** - Device closes connections unexpectedly
2. **Aggressive retry timing** - 2-second retries are too frequent
3. **No exponential backoff** - Retry intervals don't increase over time
4. **Socket descriptor issues** - "Bad file descriptor" errors indicate improper cleanup
5. **Long stabilization period** - Takes ~40 minutes to stabilize

## Proposed Solutions

### 1. Implement Exponential Backoff with Jitter

Replace the fixed 2-second delay with exponential backoff:
- First retry: 2 seconds
- Second retry: 4 seconds
- Third retry: 8 seconds
- Subsequent retries: 16, 32, 64 seconds (with jitter)

Add random jitter (±20%) to prevent thundering herd problems.

### 2. Improve Connection State Management

- Track connection state explicitly (CONNECTED, DISCONNECTED, RECONNECTING)
- Use a lock mechanism to prevent concurrent connection attempts
- Properly close and cleanup sockets on errors

### 3. Adjust Timeout Settings

- Increase default timeout from 5 to 10 seconds
- Make timeout configurable via config flow
- Add separate read/write timeout settings

### 4. Implement Connection Health Monitoring

- Track successful/failed connection attempts
- Implement circuit breaker pattern (temporary pause after multiple failures)
- Add connection quality metrics

### 5. Better Error Handling

- Distinguish between transient and permanent errors
- Handle specific Modbus error codes appropriately
- Log more detailed connection diagnostics

## Implementation Plan

1. Create a `ConnectionManager` class to encapsulate connection logic
2. Update `MidniteAPI` to use the connection manager
3. Add configuration options for timeout and retry settings
4. Implement proper connection cleanup on unload
5. Add comprehensive logging for connection state changes
