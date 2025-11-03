'use client'

import { useState, useEffect } from 'react';
import { getOpenSearchIndexes, launchProxy, stopProxy, getProxyStatus, type OpenSearchIndex } from '@/lib/indexing-api';

interface ProxyControlPanelProps {
  refreshTrigger?: string | number; // Triggers refetch when changed
}

export default function ProxyControlPanel({ refreshTrigger }: ProxyControlPanelProps) {
  const [indexes, setIndexes] = useState<OpenSearchIndex[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<string>('');
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [proxyActive, setProxyActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    loadIndexes();
    checkProxyStatus();
  }, [refreshTrigger]); // Refetch when refreshTrigger changes

  const loadIndexes = async () => {
    try {
      const data = await getOpenSearchIndexes();
      setIndexes(data);
    } catch (error) {
      console.error('Failed to load indexes:', error);
    }
  };

  const checkProxyStatus = async () => {
    try {
      const status = await getProxyStatus();
      setProxyActive(status.enabled || false);
      if (status.target_url) setTargetUrl(status.target_url);
    } catch (error) {
      setProxyActive(false);
    }
  };

  const handleLaunch = async () => {
    if (!selectedIndex || !targetUrl) {
      setMessage({type: 'error', text: 'Please select index and enter target URL'});
      return;
    }

    const index = indexes.find(i => i.name === selectedIndex);
    if (!index) return;

    setLoading(true);
    setMessage(null);

    try {
      const result = await launchProxy(targetUrl, index.run_id);
      setProxyActive(true);
      setMessage({
        type: 'success',
        text: `Proxy launched: ${result.proxy_url}`
      });
    } catch (error) {
      setMessage({type: 'error', text: `Failed to launch proxy: ${error}`});
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopProxy();
      setProxyActive(false);
      setMessage({type: 'success', text: 'Proxy stopped'});
    } catch (error) {
      setMessage({type: 'error', text: `Failed to stop proxy: ${error}`});
    } finally {
      setLoading(false);
    }
  };

  const selectedIndexData = indexes.find(i => i.name === selectedIndex);

  // Auto-fill target URL when index is selected
  useEffect(() => {
    if (selectedIndexData && !targetUrl) {
      setTargetUrl(`https://${selectedIndexData.domain}`);
    }
  }, [selectedIndexData, targetUrl]);

  return (
    <div className="bg-white rounded-lg shadow p-3 h-full">
      <h2 className="text-base font-semibold mb-2 text-gray-800">Proxy Control</h2>

      <div className="mb-2">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Target Site:
        </label>
        <input
          type="text"
          value={targetUrl}
          onChange={(e) => setTargetUrl(e.target.value)}
          placeholder="https://example.com"
          className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs text-gray-800"
          disabled={loading || proxyActive}
        />
      </div>

      <div className="mb-2">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Search Index:
        </label>
        <select
          value={selectedIndex}
          onChange={(e) => setSelectedIndex(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs text-gray-800"
          disabled={loading || proxyActive}
        >
          <option value="">-- Select indexed crawl --</option>
          {indexes.map((index) => (
            <option key={index.name} value={index.name}>
              {index.domain} - {index.run_id.substring(0, 8)} ({index.doc_count}d)
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-2 mb-2">
        <button
          onClick={handleLaunch}
          disabled={loading || proxyActive || !selectedIndex || !targetUrl}
          className="flex-1 bg-green-600 text-white rounded-lg px-3 py-1.5 text-xs hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? 'Launching...' : 'Start Proxy'}
        </button>

        <button
          onClick={handleStop}
          disabled={loading || !proxyActive}
          className="flex-1 bg-red-600 text-white rounded-lg px-3 py-1.5 text-xs hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          Stop Proxy
        </button>
      </div>

      {proxyActive && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-2 mb-2">
          <div className="text-xs font-medium text-green-800 mb-0.5">Proxy Active</div>
          <a
            href="http://localhost:8000/proxy/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline text-xs break-all"
          >
            http://localhost:8000/proxy/
          </a>
        </div>
      )}

      {message && (
        <div className={`p-2 rounded-lg text-xs ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
