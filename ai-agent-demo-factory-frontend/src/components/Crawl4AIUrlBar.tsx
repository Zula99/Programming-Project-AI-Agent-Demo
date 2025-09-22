'use client'

import { useState } from "react";

interface Crawl4AIUrlBarProps {
  onStartCrawl?: (url: string) => void;
  isRunning?: boolean;
}

export default function Crawl4AIUrlBar({ onStartCrawl, isRunning = false }: Crawl4AIUrlBarProps) {
    const [url, setUrl] = useState("https://example.com");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (onStartCrawl && url.trim() && !isRunning) {
            onStartCrawl(url.trim());
        }
    };

    return (
        <form onSubmit={handleSubmit} className="flex items-center gap-2 mt-4">
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
        </form>
    );
}