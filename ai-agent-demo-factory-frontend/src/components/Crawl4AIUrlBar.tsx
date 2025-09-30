'use client'

import { useState } from "react";

interface Crawl4AIUrlBarProps {
  onStartCrawl?: (url: string, aiModel?: string) => void;
  isRunning?: boolean;
}

export default function Crawl4AIUrlBar({ onStartCrawl, isRunning = false }: Crawl4AIUrlBarProps) {
    const [url, setUrl] = useState("https://example.com");
    const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");

    const aiModels = [
        { value: "gpt-4o-mini", label: "GPT-4o Mini (Fast & Cost-effective)", provider: "OpenAI" },
        { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo (Balanced)", provider: "OpenAI" },
        { value: "gpt-4", label: "GPT-4 (Most Capable)", provider: "OpenAI" },
        { value: "claude-3-haiku", label: "Claude 3 Haiku (Fast)", provider: "Anthropic" },
        { value: "claude-3-sonnet", label: "Claude 3 Sonnet (Balanced)", provider: "Anthropic" }
    ];

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (onStartCrawl && url.trim() && !isRunning) {
            onStartCrawl(url.trim(), selectedModel);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            {/* URL Input Row */}
            <div className="flex items-center gap-2">
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
            </div>

            {/* AI Model Selection Row */}
            <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                    AI Model:
                </label>
                <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={isRunning}
                    className="flex-1 bg-white text-gray-700 border rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    suppressHydrationWarning={true}
                >
                    {aiModels.map((model) => (
                        <option key={model.value} value={model.value}>
                            {model.label} ({model.provider})
                        </option>
                    ))}
                </select>
                <div className="text-xs text-gray-500 px-2">
                    Selected: {aiModels.find(m => m.value === selectedModel)?.provider}
                </div>
            </div>
        </form>
    );
}