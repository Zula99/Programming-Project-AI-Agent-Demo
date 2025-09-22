'use client'

import { useState, useEffect, useRef } from "react";
import Header from "@/components/Header";
import Crawl4AIUrlBar from "@/components/Crawl4AIUrlBar";
import AgentOutputCard from "@/components/AgentOutputCard";
import AgentInteractionPanel from "@/components/AgentInteractionPanel";
import { startCrawl4AI, sendAgentResponse, createWebSocketConnection, type AgentLog } from "@/lib/crawl4ai-api";

type AgentStatus = "idle" | "running" | "waiting_for_input" | "completed" | "error";

export default function Crawl4AIPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [currentQuestion, setCurrentQuestion] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Handle starting a new crawl
  const handleStartCrawl = async (url: string) => {
    try {
      const response = await startCrawl4AI(url);
      setRunId(response.run_id);
      setStatus("running");
      setLogs([]);
      setCurrentQuestion(null);

      // Establish WebSocket connection
      connectWebSocket(response.run_id);
    } catch (error) {
      console.error("Failed to start Crawl4AI:", error);
      alert("Failed to start Crawl4AI agent. Please try again.");
    }
  };

  // Handle user responses to agent questions
  const handleAgentResponse = async (response: string) => {
    if (!runId) return;

    try {
      await sendAgentResponse(runId, response);
    } catch (error) {
      console.error("Failed to send response:", error);
      alert("Failed to send response. Please try again.");
    }
  };

  // Connect to WebSocket for live updates
  const connectWebSocket = (sessionRunId: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = createWebSocketConnection(
      sessionRunId,
      // On new log message
      (log) => {
        setLogs(prev => [...prev, log]);
      },
      // On status change
      (newStatus) => {
        setStatus(newStatus);
      },
      // On error
      (error) => {
        console.error("WebSocket error:", error);
        setIsConnected(false);
      }
    );

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected");
    };

    // Handle status updates and questions from WebSocket
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
          setLogs(prev => [...prev, data.log]);
        } else if (data.type === 'status') {
          setStatus(data.status);
          if (data.question) {
            setCurrentQuestion(data.question);
          } else {
            setCurrentQuestion(null);
          }
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    wsRef.current = ws;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <Header />
      <Crawl4AIUrlBar
        onStartCrawl={handleStartCrawl}
        isRunning={status === "running" || status === "waiting_for_input"}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Left: User Interaction Controls */}
        <div className="md:col-span-1">
          <AgentInteractionPanel
            onResponse={handleAgentResponse}
            isWaitingForInput={status === "waiting_for_input"}
            currentQuestion={currentQuestion}
          />
        </div>

        {/* Right: Agent Output */}
        <div className="md:col-span-2">
          <AgentOutputCard
            runId={runId}
            isConnected={isConnected}
            status={status}
            logs={logs}
          />
        </div>
      </div>
    </main>
  );
}