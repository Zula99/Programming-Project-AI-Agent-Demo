'use client'

import { useState } from "react";

interface Crawl4AIUrlBarProps {
  onStartCrawl?: (url: string, maxPages?: number) => void;
  onStopCrawl?: () => void;
  isRunning?: boolean;
  maxPages?: string;
  setMaxPages?: (value: string) => void;
}

export default function Crawl4AIUrlBar({ onStartCrawl, onStopCrawl, isRunning = false, maxPages: propMaxPages, setMaxPages: propSetMaxPages }: Crawl4AIUrlBarProps) {
    const [url, setUrl] = useState("https://example.com");
    const [localMaxPages, setLocalMaxPages] = useState<string>("");

    // Use prop values if provided, otherwise use local state
    const maxPages = propMaxPages !== undefined ? propMaxPages : localMaxPages;
    const setMaxPages = propSetMaxPages || setLocalMaxPages;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (onStartCrawl && url.trim() && !isRunning) {
            const pages = maxPages.trim() ? parseInt(maxPages) : undefined;
            onStartCrawl(url.trim(), pages);
        }
    };

    const handleStop = () => {
        if (onStopCrawl && isRunning) {
            onStopCrawl();
        }
    };

    return (
        <form onSubmit={handleSubmit} className="mt-4">
            <div className="flex items-center gap-2">
                {/* Target Site Input */}
                <div className="flex items-center flex-1 bg-white text-gray-700 border rounded-lg px-3 py-2">
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="Enter website URL to crawl..."
                        className="flex-1 outline-none"
                        disabled={isRunning}
                        required
                        suppressHydrationWarning={true}
                    />
                </div>

                {/* Start/Stop Button */}
                {!isRunning ? (
                    <button
                        type="submit"
                        disabled={!url.trim()}
                        suppressHydrationWarning={true}
                        className={`px-4 py-2 rounded-lg font-medium transition-all ${
                            !url.trim()
                                ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                                : 'bg-blue-500 text-white hover:shadow-lg hover:bg-blue-700'
                        }`}
                    >
                        Start Crawl4AI Agent
                    </button>
                ) : (
                    <button
                        type="button"
                        onClick={handleStop}
                        suppressHydrationWarning={true}
                        className="px-4 py-2 rounded-lg font-medium transition-all bg-red-500 text-white hover:shadow-lg hover:bg-red-700"
                    >
                        End Crawl
                    </button>
                )}

                {/* Max Pages Input - Compact with Icon */}
                <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-3 py-2" title="Max Pages (Optional: Leave empty for intelligent auto-stopping)">
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <input
                        type="number"
                        value={maxPages}
                        onChange={(e) => setMaxPages(e.target.value)}
                        placeholder="Auto"
                        className="w-20 text-gray-800 text-center outline-none"
                        disabled={isRunning}
                        min="1"
                        max="10000"
                    />
                </div>
            </div>
        </form>
    );
}