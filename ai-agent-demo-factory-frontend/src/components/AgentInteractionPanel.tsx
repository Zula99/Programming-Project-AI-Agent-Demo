'use client'

import { useState } from "react";
import { HiCheck, HiChatBubbleBottomCenterText, HiXMark } from "react-icons/hi2";

interface AgentInteractionPanelProps {
  onResponse?: (response: string) => void;
  isWaitingForInput?: boolean;
  currentQuestion?: string;
}

export default function AgentInteractionPanel({
  onResponse,
  isWaitingForInput = false,
  currentQuestion
}: AgentInteractionPanelProps) {
    const [textInput, setTextInput] = useState("");
    const [lastResponse, setLastResponse] = useState<string | null>(null);

    const handleResponse = (response: string) => {
        setLastResponse(response);
        if (onResponse) {
            onResponse(response);
        }
        if (response !== "yes" && response !== "no") {
            setTextInput("");
        }
    };

    const handleTextSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (textInput.trim()) {
            handleResponse(textInput.trim());
        }
    };

    return (
        <section className="bg-white border rounded-lg p-4">
            {/* Header */}
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <HiChatBubbleBottomCenterText className="h-5 w-5" />
                    Agent Interaction
                </h2>
                <p className="text-sm text-gray-500">
                    Respond to agent questions and provide input
                </p>
            </div>

            {/* Current Question */}
            {currentQuestion && isWaitingForInput && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <h3 className="text-sm font-medium text-blue-900 mb-2">Agent Question:</h3>
                    <p className="text-sm text-blue-800">{currentQuestion}</p>
                </div>
            )}

            {/* Quick Response Buttons */}
            <div className="space-y-3">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Quick Responses
                    </label>
                    <div className="flex gap-2">
                        <button
                            onClick={() => handleResponse("yes")}
                            disabled={!isWaitingForInput}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
                                ${isWaitingForInput
                                    ? 'bg-green-500 text-white hover:bg-green-600 hover:shadow-md'
                                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                }`}
                        >
                            <HiCheck className="h-4 w-4" />
                            Yes
                        </button>
                        <button
                            onClick={() => handleResponse("no")}
                            disabled={!isWaitingForInput}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
                                ${isWaitingForInput
                                    ? 'bg-red-500 text-white hover:bg-red-600 hover:shadow-md'
                                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                }`}
                        >
                            <HiXMark className="h-4 w-4" />
                            No
                        </button>
                    </div>
                </div>

                {/* Text Input */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Custom Response
                    </label>
                    <form onSubmit={handleTextSubmit} className="flex gap-2">
                        <input
                            type="text"
                            value={textInput}
                            onChange={(e) => setTextInput(e.target.value)}
                            placeholder="Type your response..."
                            disabled={!isWaitingForInput}
                            className={`flex-1 px-3 py-2 border rounded-lg outline-none transition-colors
                                ${isWaitingForInput
                                    ? 'border-gray-300 focus:border-blue-500'
                                    : 'border-gray-200 bg-gray-50 text-gray-500'
                                }`}
                        />
                        <button
                            type="submit"
                            disabled={!isWaitingForInput || !textInput.trim()}
                            className={`px-4 py-2 rounded-lg font-medium transition-all
                                ${isWaitingForInput && textInput.trim()
                                    ? 'bg-blue-500 text-white hover:bg-blue-600 hover:shadow-md'
                                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                }`}
                        >
                            Send
                        </button>
                    </form>
                </div>
            </div>

            {/* Last Response */}
            {lastResponse && (
                <div className="mt-4 p-3 bg-gray-50 border rounded-lg">
                    <h3 className="text-xs font-medium text-gray-600 mb-1">Last Response:</h3>
                    <p className="text-sm text-gray-800 font-mono">{lastResponse}</p>
                </div>
            )}

            {/* Status */}
            <div className="mt-4 text-xs text-gray-500 flex items-center justify-between">
                <span>
                    Status: {isWaitingForInput ? "Waiting for input" : "Agent working"}
                </span>
                {!isWaitingForInput && (
                    <span className="text-gray-400">
                        Controls disabled during processing
                    </span>
                )}
            </div>
        </section>
    );
}