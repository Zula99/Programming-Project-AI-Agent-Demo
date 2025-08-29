import Header from "@/components/Header";
import URLBar from "@/components/URLBar";
import RecentRuns from "@/components/RecentRuns";
import ActiveRun from "@/components/ActiveRun";
import SearchResults from "@/components/SearchResults";
import CrawlController from "@/components/CrawlController";
import StatsPanel from "@/components/StatsPanel"; 
import SystemStatus from "@/components/SystemStatus"; 


export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <Header />
      <URLBar />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Left column: Controls and recent runs */}
        <div className="lg:col-span-1 space-y-6">
          <RecentRuns />
          <ActiveRun />
          <StatsPanel />
          <SystemStatus /> 
        </div>

        {/* Right column: Search results and crawl controller */}
        <div className="lg:col-span-2 space-y-6">
          <CrawlController />
          <SearchResults />
        </div>
      </div>
    </main>
  );
}