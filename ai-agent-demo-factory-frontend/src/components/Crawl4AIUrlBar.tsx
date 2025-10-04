'use client'

import { useState } from "react";

interface Crawl4AIUrlBarProps {
  onStartCrawl?: (url: string, maxPages?: number) => void;
  onStopCrawl?: () => void;
  isRunning?: boolean;
}

export default function Crawl4AIUrlBar({ onStartCrawl, onStopCrawl, isRunning = false }: Crawl4AIUrlBarProps) {
    const [url, setUrl] = useState("https://example.com");
    const [maxPages, setMaxPages] = useState<string>("");

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
        <div className="space-y-2 mt-4">
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
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
                <button
                type="submit"
                disabled={isRunning || !url.trim()}
                suppressHydrationWarning={true}
                className={`px-4 py-2 rounded-lg flex items-center gap-1 font-medium transition-all
                    ${isRunning || !url.trim()
                        ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                        : 'bg-blue-500 text-white hover:shadow-lg hover:bg-blue-700'
                    }`}
            >
                {isRunning ? 'Running...' : 'Start Crawl4AI Agent'}
            </button>

                {isRunning && (
                    <button
                        type="button"
                        onClick={handleStop}
                        suppressHydrationWarning={true}
                        className="px-4 py-2 rounded-lg flex items-center gap-1 font-medium transition-all bg-red-500 text-white hover:shadow-lg hover:bg-red-700"
                    >
                        End Crawl
                    </button>
                )}
            </form>

            {/* Max Pages Control */}
            <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-600">
                    Max Pages (optional):
                </label>
                <input
                    type="number"
                    value={maxPages}
                    onChange={(e) => setMaxPages(e.target.value)}
                    placeholder="Auto (intelligent stopping)"
                    className="w-48 px-3 py-1 bg-white text-gray-700 border rounded-lg outline-none focus:border-blue-500"
                    disabled={isRunning}
                    min="1"
                    max="10000"
                />
                <span className="text-xs text-gray-500">
                    Leave empty for automatic intelligent stopping
                </span>
            </div>
        </div>
    );
}