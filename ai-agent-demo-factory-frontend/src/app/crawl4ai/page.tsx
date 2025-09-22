'use client'

import { useState, useEffect, useRef } from "react";
import Header from "@/components/Header";
import Crawl4AIUrlBar from "@/components/Crawl4AIUrlBar";
import AgentOutputCard from "@/components/AgentOutputCard";
import CrawlProgressPanel from "@/components/CrawlProgressPanel";
import { startCrawl4AI, createWebSocketConnection, type AgentLog } from "@/lib/crawl4ai-api";

type AgentStatus = "idle" | "running" | "waiting_for_input" | "completed" | "error";

interface CrawlProgress {
  percentage: number;
  pages_crawled: number;
  pages_remaining: number;
  total_pages: number;
  estimated_time_remaining: number;
  crawl_speed: number;
}

export default function Crawl4AIPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [progress, setProgress] = useState<CrawlProgress>({
    percentage: 0,
    pages_crawled: 0,
    pages_remaining: 0,
    total_pages: 0,
    estimated_time_remaining: 0,
    crawl_speed: 0
  });
  const wsRef = useRef<WebSocket | null>(null);

  // Handle starting a new crawl
  const handleStartCrawl = async (url: string) => {
    try {
      const response = await startCrawl4AI(url);
      setRunId(response.run_id);
      setStatus("running");
      setLogs([]);

      // Reset progress
      setProgress({
        percentage: 0,
        pages_crawled: 0,
        pages_remaining: 0,
        total_pages: 0,
        estimated_time_remaining: 0,
        crawl_speed: 0
      });

      // Establish WebSocket connection with a slight delay
      setTimeout(() => {
        connectWebSocket(response.run_id);
      }, 500);
    } catch (error) {
      console.error("Failed to start Crawl4AI:", error);
      alert("Failed to start Crawl4AI agent. Please try again.");
    }
  };


  // Connect to WebSocket for live updates
  const connectWebSocket = (sessionRunId: string) => {
    try {
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
          console.warn("WebSocket error (non-critical):", error);
          setIsConnected(false);
        }
      );

      ws.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected successfully");
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
          } else if (data.type === 'progress') {
            setProgress(data.progress);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.warn("Failed to establish WebSocket connection:", error);
      setIsConnected(false);
    }
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
        isRunning={status === "running"}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Left: Progress Panel */}
        <div className="md:col-span-1 space-y-4">
          {/* Progress panel shows crawl statistics */}
          <CrawlProgressPanel
            runId={runId}
            progress={progress}
            status={status}
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