'use client'

import { useState, useEffect } from "react";
import StatusBadge from "./StatusBadge";
import { useRunContext } from "@/contexts/RunContext";

type RunStatus = "complete" | "running" | "failed" | "stopped";
type Run = {
    url: string;
    runId: string;
    pages: number;
    status: RunStatus;
    template: string;
}

interface CrawlRun {
    run_id: string;
    url: string;
    status: string;
    progress: number;
    started_at: number;
    completed_at?: number;
    template: string;
    pages_crawled: number;
}

interface CrawlListResponse {
    runs: CrawlRun[];
    total: number;
    active_count: number;
    completed_count: number;
}

export default function RecentRuns() {
    const [runs, setRuns] = useState<Run[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>("");
    const { selectedRun, setSelectedRun, setAllRuns, allRuns } = useRunContext();

    const fetchRuns = async () => {
        try {
            // Use Next.js API route which will handle Docker networking
            const response = await fetch('/api/crawl/list');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data: CrawlListResponse = await response.json();

            // Update shared context with all runs
            setAllRuns(data.runs);

            // Convert backend format to frontend format, keep full ID for matching
            const formattedRuns: Run[] = data.runs.slice(0, 5).map(run => ({
                url: run.url,
                runId: run.run_id, // Keep full ID for reliable matching
                pages: run.pages_crawled || 0,
                status: run.status as RunStatus,
                template: run.template
            }));

            setRuns(formattedRuns);
            setError("");

            // Auto-select the first running crawl if none is selected
            if (!selectedRun && data.runs.length > 0) {
                const firstRunning = data.runs.find(run => run.status === 'running');
                if (firstRunning) {
                    setSelectedRun(firstRunning);
                }
            }
        } catch (err) {
            console.error('Failed to fetch crawl runs:', err);
            setError(err instanceof Error ? err.message : 'Failed to load runs');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRuns();

        // Poll for updates every 5 seconds
        const interval = setInterval(fetchRuns, 5000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="bg-white text-gray-400 p-4 rounded-lg border">
                <h2 className="font-medium mb-3">Recent runs</h2>
                <div className="text-sm text-gray-500">Loading runs...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-white text-gray-400 p-4 rounded-lg border">
                <h2 className="font-medium mb-3">Recent runs</h2>
                <div className="text-sm text-red-500">Error: {error}</div>
            </div>
        );
    }

    return (
        <div className="bg-white text-gray-400 p-4 rounded-lg border">
            <h2 className="font-medium mb-3">Recent runs ({runs.length})</h2>
            {runs.length === 0 ? (
                <div className="text-sm text-gray-500">No runs yet</div>
            ) : (
                <ul className="space-y-3">
                    {runs.map((run) => {
                        const fullRun = allRuns.find(r => r.run_id === run.runId);
                        const isSelected = selectedRun?.run_id === run.runId;

                        return (
                            <li
                                key={run.runId}
                                className={`flex justify-between items-center p-2 rounded cursor-pointer transition-colors ${
                                    isSelected ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50'
                                }`}
                                onClick={() => {
                                    console.log('Clicked run:', run.runId);
                                    console.log('Full run found:', fullRun);
                                    if (fullRun) {
                                        setSelectedRun(fullRun);
                                        console.log('Set selected run to:', fullRun.run_id);
                                    }
                                }}
                            >
                                <div>
                                    <p className={`truncate max-w-48 ${
                                        isSelected ? 'text-blue-600 font-medium' : 'text-blue-500'
                                    }`} title={run.url}>
                                        {run.url}
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        {run.runId.substring(0, 8)} | {run.pages} pages | {run.template}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <StatusBadge status={run.status} />
                                    {isSelected && (
                                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                    )}
                                </div>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}