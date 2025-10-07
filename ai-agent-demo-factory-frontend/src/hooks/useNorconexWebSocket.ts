import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  run_id?: string;
  timestamp?: string;
  message?: string;
  log_level?: string;
  progress?: number;
  status?: string;
  stats?: any;
  data?: any;
  metadata?: any;
}

export interface LogMessage {
  type: 'log';
  run_id: string;
  timestamp: string;
  log_level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  metadata?: any;
}

export interface ProgressMessage {
  type: 'progress';
  run_id: string;
  timestamp: string;
  progress: number;
  status: string;
  stats?: any;
}

export interface CrawlEvent {
  type: 'crawl_started' | 'crawl_completed' | 'crawl_failed' | 'page_crawled';
  run_id: string;
  timestamp: string;
  data: any;
}

interface UseNorconexWebSocketOptions {
  onLog?: (log: LogMessage) => void;
  onProgress?: (progress: ProgressMessage) => void;
  onCrawlStarted?: (event: CrawlEvent) => void;
  onCrawlCompleted?: (event: CrawlEvent) => void;
  onCrawlFailed?: (event: CrawlEvent) => void;
  onPageCrawled?: (event: CrawlEvent) => void;
  onMessage?: (message: WebSocketMessage) => void;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useNorconexWebSocket(
  runId: string | null,
  options: UseNorconexWebSocketOptions = {}
) {
  const {
    onLog,
    onProgress,
    onCrawlStarted,
    onCrawlCompleted,
    onCrawlFailed,
    onPageCrawled,
    onMessage,
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [progress, setProgress] = useState<ProgressMessage | null>(null);
  const [lastEvent, setLastEvent] = useState<CrawlEvent | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!runId) return;

    try {
      // Close existing connection if any
      if (wsRef.current) {
        wsRef.current.close();
      }

      // Determine WebSocket URL
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.hostname;
      const wsPort = '5000'; // Backend port
      const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/crawl/${runId}`;

      console.log(`[WebSocket] Connecting to ${wsUrl}`);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[WebSocket] Connected to run_id: ${runId}`);
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;

        // Send ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000); // Ping every 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // Handle different message types
          switch (message.type) {
            case 'connection_established':
              console.log('[WebSocket] Connection established:', message.message);
              break;

            case 'message_history':
              // Load historical messages
              if (message.data && Array.isArray(message.data)) {
                const historicalLogs = message.data.filter((m: any) => m.type === 'log');
                setLogs((prev) => [...historicalLogs, ...prev]);
              }
              break;

            case 'log':
              const logMsg = message as LogMessage;
              setLogs((prev) => [...prev, logMsg]);
              if (onLog) onLog(logMsg);
              break;

            case 'progress':
              const progressMsg = message as ProgressMessage;
              setProgress(progressMsg);
              if (onProgress) onProgress(progressMsg);
              break;

            case 'crawl_started':
              const startedEvent = message as CrawlEvent;
              setLastEvent(startedEvent);
              if (onCrawlStarted) onCrawlStarted(startedEvent);
              break;

            case 'crawl_completed':
              const completedEvent = message as CrawlEvent;
              setLastEvent(completedEvent);
              if (onCrawlCompleted) onCrawlCompleted(completedEvent);
              break;

            case 'crawl_failed':
              const failedEvent = message as CrawlEvent;
              setLastEvent(failedEvent);
              if (onCrawlFailed) onCrawlFailed(failedEvent);
              break;

            case 'page_crawled':
              const pageCrawledEvent = message as CrawlEvent;
              if (onPageCrawled) onPageCrawled(pageCrawledEvent);
              break;

            case 'pong':
              // Response to ping - connection is alive
              break;

            default:
              console.log('[WebSocket] Unknown message type:', message.type);
          }

          // Call general message handler
          if (onMessage) onMessage(message);
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setConnectionError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`[WebSocket] Disconnected (code: ${event.code}, reason: ${event.reason})`);
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(
            `[WebSocket] Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setConnectionError('Max reconnection attempts reached');
        }
      };
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      setConnectionError(String(error));
    }
  }, [runId, onLog, onProgress, onCrawlStarted, onCrawlCompleted, onCrawlFailed, onPageCrawled, onMessage, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && runId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [runId, autoConnect, connect, disconnect]);

  return {
    isConnected,
    logs,
    progress,
    lastEvent,
    connectionError,
    connect,
    disconnect,
    clearLogs,
  };
}
