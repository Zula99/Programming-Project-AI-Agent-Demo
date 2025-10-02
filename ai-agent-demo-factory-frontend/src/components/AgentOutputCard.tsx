'use client'

import { useEffect, useRef, useState } from "react";
import { HiOutlineCheckCircle, HiOutlineXCircle, HiClock, HiCheckCircle } from "react-icons/hi";

interface AgentOutputCardProps {
  runId?: string | null;
  isConnected?: boolean;
  status?: "idle" | "pending" | "running" | "waiting_for_input" | "completed" | "error" | "stopped";
  logs?: LogEntry[];
  backendLogs?: BackendLogEntry[];
}

interface LogEntry {
  timestamp: string;
  message: string;
  type: "info" | "success" | "warning" | "error" | "question";
}

interface BackendLogEntry {
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  message: string;
  source: string;
}

interface MilestoneEntry {
  timestamp: string;
  phase: string;
  message: string;
  completed: boolean;
  order?: number;
}

export default function AgentOutputCard({
  runId,
  isConnected = false,
  status = "idle",
  logs = [],
  backendLogs = []
}: AgentOutputCardProps) {
    const logsEndRef = useRef<HTMLDivElement>(null);
    const [milestones, setMilestones] = useState<MilestoneEntry[]>([]);

    // Extract milestones from backend logs
    useEffect(() => {
        const milestonePatterns = [
            // 1. Initialize SmartMirrorAgent
            { pattern: /Processing URL:/, phase: "Initialize Crawl4AI SmartMirrorAgent", order: 1 },

            // 2. Start Site Reconnaissance
            { pattern: /Performing reconnaissance on/, phase: "Start Site Recon", order: 2 },

            // 3. Analyze Target Domain - MUST have "Reconnaissance complete:" followed by site info
            { pattern: /Reconnaissance complete:.*Site type:/, phase: "Analyze Target Domain", order: 3, completed: true },

            // 4. Output site type and strategy/prompt
            { pattern: /STARTING SITE ANALYSIS & STRATEGY SELECTION/, phase: "Determine Site Type & Strategy", order: 4 },

            // 5. Strategy Selected - when crawl plan is shown
            { pattern: /Crawl Plan:|Strategy:.*FULL_BROWSER|Strategy:.*JAVASCRIPT_RENDER|Strategy:.*BASIC_HTTP/, phase: "Strategy Selected", order: 5, completed: true },

            // 6. Start Sitemap Classification
            { pattern: /STARTING AI CLASSIFICATION OF SITEMAP URLS/, phase: "Start Sitemap Classification", order: 6 },

            // 7. Finish Sitemap Classification - MUST have "URL CLASSIFICATION RESULTS" header
            { pattern: /URL CLASSIFICATION RESULTS/, phase: "Finish Sitemap Classification", order: 7, completed: true },

            // 8. Initialize Hybrid Crawler - MUST have "STARTING HYBRID CRAWL EXECUTION"
            { pattern: /STARTING HYBRID CRAWL EXECUTION/, phase: "Initialize Hybrid Crawler", order: 8 },

            // 9. Finish Crawl - with checkmark emoji
            { pattern: /Hybrid crawl completed/, phase: "Finish Crawl", order: 9, completed: true },

            // 10. Quality Assessment
            { pattern: /STARTING QUALITY ASSESSMENT & ANALYSIS/, phase: "Quality Assessment", order: 10 },

            // 11. Overall Quality Score - must have "Overall:" in the quality assessment
            { pattern: /Quality Assessment.*Overall:.*\d\.\d{3}/, phase: "Overall Quality Score", order: 11, completed: true },
        ];

        const newMilestones: MilestoneEntry[] = [];
        const phasesSeen = new Set<string>();

        backendLogs.forEach(log => {
            milestonePatterns.forEach(({ pattern, phase, order, completed = false }) => {
                if (pattern.test(log.message) && !phasesSeen.has(phase)) {
                    phasesSeen.add(phase);
                    newMilestones.push({
                        timestamp: log.timestamp,
                        phase: phase,
                        message: log.message.replace(/={70}/g, '').replace(/={60}/g, '').replace(/={80}/g, '').trim(),
                        completed: completed,
                        order: order
                    });
                }
            });
        });

        // Sort by order to maintain proper sequence
        newMilestones.sort((a, b) => (a.order || 0) - (b.order || 0));
        setMilestones(newMilestones);
    }, [backendLogs]);

    // Auto-scroll to bottom when new milestones arrive
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [milestones]);

    const getStatusIcon = () => {
        switch (status) {
            case "running":
                return <HiClock className="h-5 w-5 text-blue-500 animate-spin" />;
            case "completed":
                return <HiOutlineCheckCircle className="h-5 w-5 text-green-500" />;
            case "error":
                return <HiOutlineXCircle className="h-5 w-5 text-red-500" />;
            case "stopped":
                return <HiOutlineXCircle className="h-5 w-5 text-orange-500" />;
            case "waiting_for_input":
                return <HiClock className="h-5 w-5 text-yellow-500" />;
            default:
                return <HiClock className="h-5 w-5 text-gray-400" />;
        }
    };

    const getStatusText = () => {
        switch (status) {
            case "running":
                return "Agent Running";
            case "completed":
                return "Completed";
            case "error":
                return "Error";
            case "stopped":
                return "Stopped";
            case "waiting_for_input":
                return "Waiting for Input";
            default:
                return "Ready";
        }
    };

    const getLogTypeColor = (type: LogEntry["type"]) => {
        switch (type) {
            case "success":
                return "text-green-400";
            case "warning":
                return "text-yellow-400";
            case "error":
                return "text-red-400";
            case "question":
                return "text-blue-400";
            default:
                return "text-gray-300";
        }
    };

    return (
        <section className="bg-white border rounded-lg p-4">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900">Crawl4AI Agent Output</h2>
                    <p className="text-sm text-gray-500">
                        {runId ? `Run ID: ${runId}` : "No active session"}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {getStatusIcon()}
                    <span className="text-sm font-medium text-gray-700">
                        {getStatusText()}
                    </span>
                    {isConnected && (
                        <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-100 px-2 py-1 rounded-full">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            Live
                        </span>
                    )}
                </div>
            </div>

            {/* Agent Milestone Progress */}
            <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-lg p-6 h-96 overflow-auto">
                {milestones.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">
                        <HiClock className="h-12 w-12 mx-auto mb-3 text-gray-600" />
                        <p className="text-lg">Waiting for crawl to start...</p>
                        <p className="text-sm mt-2">Milestones will appear here</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {milestones.map((milestone, index) => (
                            <div key={index} className="flex items-start gap-4 bg-gray-800 bg-opacity-50 rounded-lg p-4 border border-gray-700">
                                <div className="flex-shrink-0">
                                    {milestone.completed ? (
                                        <HiCheckCircle className="h-6 w-6 text-green-400" />
                                    ) : (
                                        <HiClock className="h-6 w-6 text-blue-400 animate-pulse" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs text-gray-500 font-mono">
                                            {milestone.timestamp}
                                        </span>
                                        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                                            milestone.completed ? 'bg-green-900 text-green-300' : 'bg-blue-900 text-blue-300'
                                        }`}>
                                            {milestone.phase}
                                        </span>
                                    </div>
                                    <p className="text-sm text-gray-300">
                                        {milestone.message}
                                    </p>
                                </div>
                            </div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                )}
            </div>

            {/* Connection Status */}
            <div className="mt-3 text-xs text-gray-500 flex items-center justify-between">
                <span>
                    WebSocket: {isConnected ? "Connected" : "Disconnected"}
                </span>
                <span>
                    {milestones.length} milestone{milestones.length === 1 ? "" : "s"} tracked
                </span>
            </div>
        </section>
    );
}