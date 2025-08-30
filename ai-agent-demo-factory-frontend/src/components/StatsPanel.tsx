'use client';

import { useState, useEffect } from 'react';
import { FiBarChart, FiDatabase, FiTrendingUp, FiActivity } from 'react-icons/fi';

interface CrawlStats {
  totalCrawls: number;
  totalPages: number;
  avgSpeed: number;
  successRate: number;
}

export default function StatsPanel() {
  const [stats, setStats] = useState<CrawlStats>({
    totalCrawls: 0,
    totalPages: 0,
    avgSpeed: 0,
    successRate: 0
  });
  const [loading, setLoading] = useState(true);

  // Fetch statistics from backend
  useEffect(() => {
    const fetchStats = async () => {
      try {
        // TODO: Replace with real backend API call
        // Currently using mock data, can be integrated with real stats API
        const mockStats = {
          totalCrawls: 15,
          totalPages: 1250,
          avgSpeed: 45.2,
          successRate: 94.5
        };
        setStats(mockStats);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    
    // Update stats every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Crawl Statistics Overview
      </h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center p-4 bg-blue-50 rounded-lg">
          <div className="text-2xl mb-2"></div>
          <p className="text-2xl font-bold text-blue-600">{stats.totalCrawls}</p>
          <p className="text-sm text-gray-600">Total Crawls</p>
        </div>
        
        <div className="text-center p-4 bg-green-50 rounded-lg">
          <div className="text-2xl mb-2"></div>
          <p className="text-2xl font-bold text-green-600">{stats.totalPages.toLocaleString()}</p>
          <p className="text-sm text-gray-600">Total Pages</p>
        </div>
        
        <div className="text-center p-4 bg-purple-50 rounded-lg">
          <div className="text-2xl mb-2"></div>
          <p className="text-2xl font-bold text-purple-600">{stats.avgSpeed}</p>
          <p className="text-sm text-gray-600">Avg Speed (pages/min)</p>
        </div>
        
        <div className="text-center p-4 bg-orange-50 rounded-lg">
          <div className="text-2xl mb-2"></div>
          <p className="text-2xl font-bold text-orange-600">{stats.successRate}%</p>
          <p className="text-sm text-gray-600">Success Rate</p>
        </div>
      </div>
    </div>
  );
}
