'use client'

// Find HeroIcons here: https://react-icons.github.io/react-icons/icons/hi/
import StatusBadge from "./StatusBadge";
import TabList from "./TabList";
import SortableTH from "./SortableTH";
import { useRunContext } from "@/contexts/RunContext";
import { useMemo, useState, useEffect, ChangeEvent, FormEvent } from "react";
import { 
	HiDownload,
    HiOutlineCheckCircle,
    HiClipboard,
    HiFilter,
} from "react-icons/hi";
import { HiArrowPath, HiMagnifyingGlass } from "react-icons/hi2";

type RunStatus = "running" | "complete";
type Tab = "data" | "config" | "logs" | "stats";

interface OSResult {
	_id: string;
	_score: number;
	_source: {
		title: string;
		description: string;
		url: string;
		content?: string;
		metadata?: { depth?: string; contentType?: string };
	}
}

interface OSSearchResponse {
	took: number;
	hits: { total: { value: number }; hits: OSResult[] };
}

type PageRow = {
    id: string;
    path: string;
    title: string;
    type: "html" | "pdf" | "doc";
    size: number; // KB
};

const initialRows: PageRow[] = [
    { id: "1", path: "/", title: "Home", type: "html", size: 18_322 },
    { id: "2", path: "/pricing", title: "Pricing", type: "html", size: 25_101 },
    { id: "3", path: "/about", title: "About", type: "html", size: 19_552 },
]

function formatTimestamp(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleString();
}

function formatKB(bytes: number) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function urlPath(u: string): string {
	try {
		const p = new URL(u);
		return p.pathname || "/";
	} catch {
		return "/";
	}
}

function inferType(ct?: string, url?: string): PageRow["type"] {
	const lc = (ct || "").toLowerCase();
	const u = (url || "").toLowerCase();
	if (lc.includes("pdf") || u.endsWith(".pdf")) return "pdf";
	if (lc.includes("html") || lc.includes("text/")) return "html";
	return "doc";
}

function mapHitToRow(hit: OSResult): PageRow {
	const contentLen = hit._source.content?.length ?? 0;
	return {
		id: hit._id,
		path: urlPath(hit._source.url),
		title: hit._source.title || "Untitled",
		type: inferType(hit._source.metadata?.contentType, hit._source.url),
		size: contentLen,
	};
}

export default function ActiveRun() {
    const { selectedRun } = useRunContext();
    const [activeTab, setActiveTab] = useState<Tab>("data");

    // Debug logging and auto-switch to Stats tab for completed runs
    useEffect(() => {
        console.log('ActiveRun - selectedRun changed:', selectedRun);
        // Auto-switch to Stats tab for completed runs
        if (selectedRun && selectedRun.status === 'complete' && selectedRun.stats) {
            setActiveTab('stats');
        } else if (selectedRun && selectedRun.status === 'running') {
            setActiveTab('data');
        }
    }, [selectedRun]);
    const [query, setQuery] = useState("");
	const [sortKey, setSortKey] = useState<keyof Pick<PageRow, "path" | "title" | "type" | "size">>("path");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
	const [rows, setRows] = useState<PageRow[]>([]);
	const [loading, setLoading] = useState(false);
	const [searchTime, setSearchTime] = useState<number | null>(null);
	const [error, setError] = useState<string>("");

    // Default fallback for when no run is selected
    const displayRun = selectedRun || {
        run_id: "no-selection",
        url: "No run selected",
        status: "unknown",
        progress: 0,
        started_at: Date.now() / 1000,
        template: "none",
        pages_crawled: 0
    };

	// Initial load, getting some docs from index
	useEffect(() => {
		let cancelled = false;
		(async () => {
			setLoading(true);
			setError("");

			try {
				const res = await fetch("/api/search", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ matchAll: true, size: 5000 }),
				});

				if (!res.ok) throw new Error(`Search failed: ${res.status}`);

				const data: OSSearchResponse = await res.json();
				if (!cancelled) {
					setRows(data.hits.hits.map(mapHitToRow));
					setSearchTime(data.took);
				}
			} catch (e) {
				if (!cancelled) 
					setError(e instanceof Error ? e.message : "Search failed");
			} finally {
				if (!cancelled) setLoading(false);
			}
		})();
		return () => { cancelled = true; };
	}, []);

	const filtered = useMemo(() => {
  		const q = query.trim().toLowerCase();
  		const effectiveRows = rows.length ? rows : initialRows;

  		const dataset = q
  		  ? effectiveRows.filter(
  		      (r) =>
  		        r.path.toLowerCase().includes(q) ||
  		        r.title.toLowerCase().includes(q) ||
  		        r.type.toLowerCase().includes(q)
  		    )
  		  : effectiveRows;
		
  		const sorted = [...dataset].sort((a, b) => {
  		  const av = a[sortKey];
  		  const bv = b[sortKey];
  		  if (typeof av === "number" && typeof bv === "number") {
  		    return sortDir === "asc" ? av - bv : bv - av;
  		  }
  		  const as = String(av).toLowerCase();
  		  const bs = String(bv).toLowerCase();
  		  return sortDir === "asc" ? as.localeCompare(bs) : bs.localeCompare(as);
  		});
	
  		return sorted;
	}, [rows, query, sortKey, sortDir]);


    const toggleSort = (key: keyof Pick<PageRow, "path" | "title" | "type" | "size">) => {
        if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        else {
            setSortKey(key);
            setSortDir("asc");
        }
    };

	async function handleSearchSubmit(e: FormEvent) {
		e.preventDefault();
		const q = query.trim();
		if (!q) return;
		setLoading(true); setError("");
		try {
			const res = await fetch("/api/search", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ query: q, size: 5000 }),
			});
			if (!res.ok) throw new Error(`Search failed: ${res.status}`);
			const data: OSSearchResponse = await res.json();
			setRows(data.hits.hits.map(mapHitToRow));
			setSearchTime(data.took);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Search failed");
		} finally {
			setLoading(false);
		}
	}

    return (
        <section className="bg-white border rounded-lg p-4">
            {/*Header*/}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                        {selectedRun ? `Active run (${selectedRun.run_id.substring(0, 8)})` : 'Select a run'}
                    </h2>
                    <p className="text-sm text-gray-800">
                        <span className="font-medium text-blue-600">
                            {displayRun.url || 'No URL specified'}
                        </span>
                        {selectedRun && displayRun.url && (
                            <button
                                onClick={() => window.open(displayRun.url, '_blank')}
                                className="ml-1 text-blue-500 hover:text-blue-700"
                                title="Open URL in new tab"
                            >
                                🔗
                            </button>
                        )}
                        <span className="ml-2 text-gray-600">|</span>
                        <span className="ml-2 font-mono text-gray-800">
                            ID: {displayRun.run_id.substring(0, 8)}
                        </span>
                        {selectedRun && (
                            <span className="ml-2 text-gray-600">|</span>
                        )}
                        {selectedRun && (
                            <span className="ml-2 text-gray-800">
                                Started: {formatTimestamp(displayRun.started_at)}
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <StatusBadge status={displayRun.status as any} />
                    {selectedRun && displayRun.status === 'running' && (
                        <div className="text-sm text-gray-800 font-medium">
                            Progress: {displayRun.progress}%
                        </div>
                    )}
					{searchTime !== null && (
						<span className="hidden sm:inline text-sm text-gray-700">{loading ? "Searching..." : `Fetched in ${searchTime}ms`}</span>
					)}
                    <CopyButton value={displayRun.run_id} />
                </div>
            </div>

            {/*Tabs*/}
            <TabList value={activeTab} onChange={setActiveTab} />

            {/*Panels*/}
            {activeTab === "data" && (
                <div className="mt-4">
                    {/*Toolbar*/}
					<form onSubmit={handleSearchSubmit} className="mb-3 flex flex-wrap items-center gap-2">
                    	<div className="mb-3 flex flex-wrap items-center gap-2">
                    	    <div className="flex flex-1 items-center rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-sm hover:border-gray-300">
                    	        <HiMagnifyingGlass className="mr-2 h-5 w-5 text-gray-400" />
                    	        <input
                    	            value={query}
                    	            onChange={(e: ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
                    	            placeholder="Filter by path, title, or type"
                    	            className="w-full bg-transparent outline-none placeholder:text-gray-400"
                    	        />
                    	    </div>
							<button
								type="submit"
								className="inline-flex items-center gap-2 rounded-lg border border-gray-300
											bg-white px-3 py-2 text-gray-700 shadow-sm transition-all 
											hover:bg-gray-50 hover:shadow-md focus-visible:outline-none
											focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2"
								title="Query OpenSearch"
							>
								<HiArrowPath className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />
							</button>
							<button
								type="button"
								className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 
											font-medium text-white shadow-sm transition-all hover:bg-blue-500 
											hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 
											focus-visible:ring-blue-500/70 focus-visible:ring-offset-2"
								title="Download CSV"
							>
								<HiDownload className="h-5 w-5" />
								CSV
							</button>
                    	</div>
					</form>

					{/*Count*/}
					<div className="mb-2 flex items-center justify-between">
						<div className="text-sm text-gray-500">
							<span className="font-medium text-gray-900">Indexed Pages</span> ({filtered.length})
						</div>
						<div className="flex items-center gap-2 text-xs text-gray-500">
							{loading ? (
								<>
									<HiArrowPath className="h-4 w-4 animate-spin" /> Loading...
								</>
							) : null}
						</div>
					</div>

					{/*Table*/}
					<div className="overflow-hidden rounded-lg border">
						<div className="max-h-[420px] overflow-auto">
							<table className="min-w-full text-sm">
								<thead className="sticky top-0 bg-gray-50 text-left text-gray-600">
									<tr className="[&>th]:py-2 [&>th]:px-3">
										<SortableTH
											label="Path"
											active={sortKey === "path"}
											dir={sortKey === "path" ? sortDir : undefined}
											onClick={() => toggleSort("path")}
										/>
										<SortableTH
											label="Title"
											active={sortKey === "title"}
											dir={sortKey === "title" ? sortDir : undefined}
											onClick={() => toggleSort("title")}
										/>
										<SortableTH
											label="Type"
											active={sortKey === "type"}
											dir={sortKey === "type" ? sortDir : undefined}
											onClick={() => toggleSort("type")}
										/>
										<SortableTH
											label="Size"
											active={sortKey === "size"}
											dir={sortKey === "size" ? sortDir : undefined}
											onClick={() => toggleSort("size")}
										/>
									</tr>
								</thead>
								<tbody className="divide-y divide-gray-100">
									{filtered.map((row) => (
										<tr key={row.id} className="hover:bg-gray-50">
											<td className="py-2 px-3 font-mono text-gray-800">
												<span className="truncate block max-w-[420px]">{row.path}</span>
											</td>
											<td className="py-2 px-3 text-gray-800">{row.title}</td>
											<td className="py-2 px-3 text-gray-800">{row.type}</td>
											<td className="py-2 px-3 tabular-nums text-gray-800">{formatKB(row.size)}</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</div>
                </div>
            )}

			{activeTab === "config" && (
				<div className="mt-4 space-y-3">
					<div className="flex items-center justify-between">
						<h3 className="text-sm font-medium text-gray-900">Crawler config</h3>
						<CopyButton value={JSON.stringify(selectedRun ? {
                            run_id: displayRun.run_id,
                            url: displayRun.url,
                            template: displayRun.template,
                            status: displayRun.status,
                            progress: displayRun.progress,
                            started_at: displayRun.started_at,
                            pages_crawled: displayRun.pages_crawled,
                            stats: selectedRun.stats || {}
                        } : sampleConfig, null, 2)} label="Copy JSON" />
					</div>
					<pre className="overflow-auto rounded-lg border bg-gray-50 p-3 text-xs leading-relaxed text-gray-800">
						{JSON.stringify(selectedRun ? {
                            run_id: displayRun.run_id,
                            url: displayRun.url,
                            template: displayRun.template,
                            status: displayRun.status,
                            progress: displayRun.progress,
                            started_at: displayRun.started_at,
                            completed_at: selectedRun.completed_at,
                            pages_crawled: displayRun.pages_crawled,
                            stats: selectedRun.stats || {}
                        } : sampleConfig, null, 2)}
					</pre>
				</div>
			)}

			{activeTab === "logs" && (
				<div className="mt-4">
					<div className="mb-2 flex items-center justify-between">
						<h3 className="text-sm font-medium text-gray-900">Run logs</h3>
						<span className="inline-flex items-center gap-1 text-xs text-green-700">
							<HiOutlineCheckCircle className="h-4 w-4" /> live
						</span>
					</div>
					<pre className="max-h-[420px] overflow-auto rounded-lg border bg-black p-3 text-xs leading-relaxed text-green-300">
						{`10:12:03  [INFO] seed=https://example.com depth=2 renderJS=true
							10:12:05  [FETCH] 200  GET  /  (18322 bytes)
							10:12:07  [PARSE] links found: 14
							10:12:12  [FETCH] 200  GET  /pricing  (25101 bytes)
							10:12:15  [FETCH] 200  GET  /about  (19552 bytes)
							10:12:18  [FETCH] 200  GET  /case-studies  (39881 bytes)
							10:12:23  [FETCH] 200  GET  /blog  (28430 bytes)
							10:12:27  [FETCH] 200  GET  /blog/ai-for-search  (44012 bytes)
							10:12:32  [FETCH] 200  GET  /whitepaper.pdf  (512330 bytes)
							10:12:38  [DONE]  indexed=10  queued=0  errors=0`}
					</pre>
				</div>
			)}

			{activeTab === "stats" && (
				<div className="mt-4">
					<div className="mb-3 flex items-center justify-between">
						<h3 className="text-sm font-medium text-gray-900">Crawl Statistics</h3>
						{selectedRun && (
							<div className="text-xs text-gray-700 font-medium">
								Template: {selectedRun.template}
							</div>
						)}
					</div>

					{selectedRun && selectedRun.stats ? (
						<div className="space-y-6">
							{/* URL and Run ID Header */}
							<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
								<div className="space-y-3">
									<div>
										<label className="text-sm font-medium text-gray-900">Target URL:</label>
										<div className="mt-1 flex items-center gap-2">
											<span className="text-blue-600 font-medium break-all">
												{selectedRun.url || 'No URL available'}
											</span>
											{selectedRun.url && (
												<button
													onClick={() => window.open(selectedRun.url, '_blank')}
													className="text-blue-500 hover:text-blue-700 text-sm"
													title="Open URL in new tab"
												>
													🔗
												</button>
											)}
										</div>
									</div>
									<div>
										<label className="text-sm font-medium text-gray-900">Run ID:</label>
										<div className="mt-1 flex items-center gap-2">
											<code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-900">
												{selectedRun.run_id}
											</code>
											<CopyButton value={selectedRun.run_id} label="Copy Run ID" />
										</div>
									</div>
								</div>
							</div>
							{/* Overview Stats */}
							<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
								<div className="bg-blue-50 rounded-lg p-3">
									<div className="text-2xl font-bold text-blue-600">
										{selectedRun.stats.total_pages_crawled || 0}
									</div>
									<div className="text-sm text-gray-800 font-medium">Total Pages</div>
								</div>
								<div className="bg-green-50 rounded-lg p-3">
									<div className="text-2xl font-bold text-green-600">
										{selectedRun.stats.pages_indexed || 0}
									</div>
									<div className="text-sm text-gray-800 font-medium">Indexed</div>
								</div>
								<div className="bg-yellow-50 rounded-lg p-3">
									<div className="text-2xl font-bold text-yellow-600">
										{selectedRun.stats.pages_rejected || 0}
									</div>
									<div className="text-sm text-gray-800 font-medium">Rejected</div>
								</div>
								<div className="bg-purple-50 rounded-lg p-3">
									<div className="text-2xl font-bold text-purple-600">
										{selectedRun.stats.crawl_duration_seconds || 0}s
									</div>
									<div className="text-sm text-gray-800 font-medium">Duration</div>
								</div>
							</div>

							{/* Detailed Stats */}
							<div className="grid md:grid-cols-2 gap-6">
								{/* Processing Stats */}
								<div className="bg-white border rounded-lg p-4">
									<h4 className="font-medium text-gray-900 mb-3">Processing</h4>
									<div className="space-y-2 text-sm">
										<div className="flex justify-between">
											<span className="text-gray-800">Pages Fetched:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.pages_fetched || 0}</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">Pages Processed:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.pages_processed || 0}</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">Pages Queued:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.pages_queued || 0}</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">URLs Extracted:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.urls_extracted || 0}</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">Pages Skipped:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.pages_skipped || 0}</span>
										</div>
									</div>
								</div>

								{/* Performance Stats */}
								<div className="bg-white border rounded-lg p-4">
									<h4 className="font-medium text-gray-900 mb-3">Performance</h4>
									<div className="space-y-2 text-sm">
										<div className="flex justify-between">
											<span className="text-gray-800">Avg Throughput:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.avg_throughput?.toFixed(2) || 0} pages/sec</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">Norconex Duration:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.norconex_duration_seconds || 0}s</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">Max Depth Reached:</span>
											<span className="font-medium text-gray-900">{selectedRun.stats.max_depth_reached || 0}</span>
										</div>
										<div className="flex justify-between">
											<span className="text-gray-800">Errors Encountered:</span>
											<span className={`font-medium ${selectedRun.stats.errors_encountered ? 'text-red-600' : 'text-green-600'}`}>
												{selectedRun.stats.errors_encountered || 0}
											</span>
										</div>
									</div>
								</div>
							</div>

							{/* Timing Information */}
							<div className="bg-gray-50 rounded-lg p-4">
								<h4 className="font-medium text-gray-900 mb-3">Timing</h4>
								<div className="grid md:grid-cols-3 gap-4 text-sm">
									<div>
										<span className="text-gray-800 font-medium">Started:</span>
										<div className="font-medium text-gray-900">{formatTimestamp(selectedRun.started_at)}</div>
									</div>
									{selectedRun.completed_at && (
										<div>
											<span className="text-gray-800 font-medium">Completed:</span>
											<div className="font-medium text-gray-900">{formatTimestamp(selectedRun.completed_at)}</div>
										</div>
									)}
									<div>
										<span className="text-gray-800 font-medium">Status:</span>
										<div className="mt-1">
											<StatusBadge status={selectedRun.status as any} />
										</div>
									</div>
								</div>
							</div>
						</div>
					) : (
						<div className="text-center py-8 text-gray-500">
							{selectedRun ? 'No statistics available for this run' : 'Select a run to view statistics'}
						</div>
					)}
				</div>
			)}
        </section>
    );
}

function CopyButton({ value, label = "Copy ID" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1200);
        } catch {}
      }}
      className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-all hover:bg-gray-50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2"
      title={label}
    >
      {copied ? (
        <HiOutlineCheckCircle className="h-5 w-5 text-green-600" />
      ) : (
        <HiClipboard className="h-5 w-5" />
      )}
      <span className="hidden sm:inline">{copied ? "Copied" : label}</span>
    </button>
  );
}

// Sample config for Config tab
const sampleConfig = {
  seedUrl: "https://example.com",
  include: ["/", "/pricing", "/about", "/blog"],
  exclude: ["/admin", "/auth", "/cart"],
  depth: 2,
  maxPages: 250,
  renderJS: true,
  respectRobotsTxt: true,
  obeySitemaps: true,
  userAgent: "DemoCrawler/1.0",
  rateLimit: { requestsPerSecond: 4, burst: 8 },
};