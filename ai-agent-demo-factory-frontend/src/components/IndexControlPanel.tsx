'use client'

import { useState, useEffect } from 'react';
import { getCompletedCrawls, indexCrawl, type CompletedCrawl } from '@/lib/indexing-api';

export default function IndexControlPanel() {
  const [crawls, setCrawls] = useState<CompletedCrawl[]>([]);
  const [selectedCrawl, setSelectedCrawl] = useState<string>('');
  const [indexing, setIndexing] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    loadCrawls();
  }, []);

  const loadCrawls = async () => {
    try {
      const data = await getCompletedCrawls();
      setCrawls(data);
    } catch (error) {
      console.error('Failed to load crawls:', error);
    }
  };

  const handleIndex = async () => {
    if (!selectedCrawl) {
      setMessage({type: 'error', text: 'Please select a crawl'});
      return;
    }

    const crawl = crawls.find(c => c.run_id === selectedCrawl);
    if (!crawl) return;

    setIndexing(true);
    setMessage(null);

    try {
      const result = await indexCrawl(crawl.run_id, crawl.output_path, crawl.domain);
      setMessage({
        type: 'success',
        text: `Indexed as ${result.index_name} (${result.stats.documents_indexed} docs)`
      });
    } catch (error) {
      setMessage({type: 'error', text: `Indexing failed: ${error}`});
    } finally {
      setIndexing(false);
    }
  };

  const selectedCrawlData = crawls.find(c => c.run_id === selectedCrawl);

  return (
    <div className="bg-white rounded-lg shadow p-3 h-full">
      <h2 className="text-base font-semibold mb-2 text-gray-800">Index Control</h2>

      <div className="mb-2">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Select crawl to index:
        </label>
        <select
          value={selectedCrawl}
          onChange={(e) => setSelectedCrawl(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs text-gray-800"
          disabled={indexing}
        >
          <option value="">-- Select a crawl --</option>
          {crawls.map((crawl) => (
            <option key={crawl.run_id} value={crawl.run_id}>
              {crawl.domain} - {crawl.run_id.substring(0, 8)} ({crawl.pages_crawled}p, {crawl.status})
            </option>
          ))}
        </select>
      </div>

      {selectedCrawlData && (
        <div className="bg-gray-50 rounded-lg p-2 mb-2 text-xs text-gray-800 space-y-0.5">
          <div><strong>Domain:</strong> {selectedCrawlData.domain}</div>
          <div><strong>Pages:</strong> {selectedCrawlData.pages_crawled}</div>
          <div><strong>Quality:</strong> {selectedCrawlData.quality_score?.toFixed(1)}%</div>
          <div><strong>Status:</strong> {selectedCrawlData.status}</div>
        </div>
      )}

      <button
        onClick={handleIndex}
        disabled={!selectedCrawl || indexing}
        className="w-full bg-indigo-600 text-white rounded-lg px-3 py-1.5 text-xs hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {indexing ? 'Indexing...' : 'Index to OpenSearch'}
      </button>

      {message && (
        <div className={`mt-2 p-2 rounded-lg text-xs ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
