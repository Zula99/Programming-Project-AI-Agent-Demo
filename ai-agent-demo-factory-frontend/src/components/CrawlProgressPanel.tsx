'use client'

import { useState, useEffect } from "react";
import { HiClock, HiChartBar, HiDocumentText, HiForward, HiBeaker, HiArchiveBox } from "react-icons/hi2";

interface CrawlProgress {
  percentage: number;
  pages_crawled: number;
  pages_remaining: number;
  total_pages: number;
  estimated_time_remaining: number; // in seconds
  crawl_speed: number; // pages per minute
  ai_classifications: number; // AI classifications made
  cache_hits: number; // Cache hits during crawl
  loaded_caches: number; // Total cached links (sitemap + crawl cache hits)
}

interface CrawlProgressPanelProps {
  runId?: string | null;
  progress?: CrawlProgress;
  status?: "idle" | "pending" | "running" | "waiting_for_input" | "completed" | "error" | "stopped";
}

export default function CrawlProgressPanel({
  runId,
  progress,
  status = "idle"
}: CrawlProgressPanelProps) {

  const formatTime = (seconds: number): string => {
    if (seconds <= 0) return "0s";

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  const getProgressColor = () => {
    if (status === "error") return "bg-red-500";
    if (status === "completed") return "bg-green-500";
    if (status === "stopped") return "bg-orange-500";
    if (status === "waiting_for_input") return "bg-yellow-500";
    return "bg-blue-500";
  };

  const isActive = status === "running" || status === "waiting_for_input";

  return (
    <section className="bg-white border rounded-lg p-4">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <HiChartBar className="h-5 w-5" />
          Crawl Progress
        </h2>
        <p className="text-sm text-gray-500">
          Real-time crawling statistics and progress
        </p>
      </div>

      {!runId ? (
        <div className="text-center py-8 text-gray-500">
          <HiClock className="h-8 w-8 mx-auto mb-2 text-gray-400" />
          <p>Progress will appear when a crawl is started</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Progress Bar */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">Overall Progress</span>
              <span className="text-sm text-gray-600">
                {progress?.percentage?.toFixed(1) || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-300 ${getProgressColor()}`}
                style={{ width: `${progress?.percentage || 0}%` }}
              />
            </div>
          </div>

          {/* Statistics Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Pages Crawled */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <HiDocumentText className="h-4 w-4 text-blue-500" />
                <span className="text-xs font-medium text-gray-600">Crawled</span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                {progress?.pages_crawled || 0}
              </div>
            </div>

            {/* Pages Remaining */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <HiClock className="h-4 w-4 text-orange-500" />
                <span className="text-xs font-medium text-gray-600">Remaining</span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                {progress?.pages_remaining || 0}
              </div>
              <div className="text-xs text-gray-500">
                pages left
              </div>
            </div>

            {/* Crawl Speed */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <HiForward className="h-4 w-4 text-purple-500" />
                <span className="text-xs font-medium text-gray-600">Speed</span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                {progress?.crawl_speed?.toFixed(1) || 0}
              </div>
              <div className="text-xs text-gray-500">
                pages/min
              </div>
            </div>

            {/* Time Remaining */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <HiClock className="h-4 w-4 text-green-500" />
                <span className="text-xs font-medium text-gray-600">ETA</span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                {progress?.estimated_time_remaining
                  ? formatTime(progress.estimated_time_remaining)
                  : "0s"
                }
              </div>
              <div className="text-xs text-gray-500">
                estimated
              </div>
            </div>

            {/* Loaded Caches */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <HiArchiveBox className="h-4 w-4 text-teal-500" />
                <span className="text-xs font-medium text-gray-600">Loaded Caches</span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                {progress?.loaded_caches || 0}
              </div>
              <div className="text-xs text-gray-500">
                cached links
              </div>
            </div>
          </div>

          {/* Status Indicator */}
          <div className="pt-3 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Status</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  isActive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                }`} />
                <span className="text-sm font-medium text-gray-700 capitalize">
                  {status === "waiting_for_input" ? "Waiting for input" : status}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}