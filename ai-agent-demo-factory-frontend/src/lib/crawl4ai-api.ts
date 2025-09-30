// API client functions for Crawl4AI agent communication

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

export interface Crawl4AISession {
  run_id: string;
  target_url: string;
  status: 'pending' | 'running' | 'waiting_for_input' | 'completed' | 'error';
  started_at: number;
  current_question?: string;
}

export interface AgentLog {
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'question';
}

export interface Crawl4AIStatus {
  session: Crawl4AISession;
  logs: AgentLog[];
}

/**
 * Start a new Crawl4AI agent session
 */
export async function startCrawl4AI(targetUrl: string, aiModel?: string): Promise<{ run_id: string }> {
  const response = await fetch(`${API_BASE}/crawl4ai/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      target_url: targetUrl,
      ...(aiModel && { ai_model: aiModel })
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start Crawl4AI: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get the current status and logs for a Crawl4AI session
 */
export async function getCrawl4AIStatus(runId: string): Promise<Crawl4AIStatus> {
  const response = await fetch(`${API_BASE}/crawl4ai/status/${runId}`);

  if (!response.ok) {
    throw new Error(`Failed to get status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send a response to the agent (yes/no/custom text)
 */
export async function sendAgentResponse(runId: string, response: string): Promise<void> {
  const res = await fetch(`${API_BASE}/crawl4ai/respond`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      run_id: runId,
      response: response,
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to send response: ${res.statusText}`);
  }
}

/**
 * Create a WebSocket connection for live agent output
 */
export function createWebSocketConnection(
  runId: string,
  onMessage: (log: AgentLog) => void,
  onStatusChange: (status: Crawl4AISession['status']) => void,
  onError: (error: Event) => void
): WebSocket {
  const wsUrl = `${API_BASE.replace('http://', 'ws://').replace('https://', 'wss://')}/crawl4ai/ws/${runId}`;

  console.log('Connecting to WebSocket:', wsUrl);

  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        onMessage(data.log);
      } else if (data.type === 'status') {
        onStatusChange(data.status);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket connection error:', error);
    onError(error);
  };

  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
  };

  return ws;
}