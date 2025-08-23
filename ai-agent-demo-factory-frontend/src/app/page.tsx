import Header from "@/components/Header";
import URLBar from "@/components/URLBar";
import RecentRuns from "@/components/RecentRuns";
import ActiveRun from "@/components/ActiveRun";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <Header />
      <URLBar />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Left: Recent runs */}
        <div className="md:col-span-1">
          <RecentRuns />
        </div>

        {/* Right: Active run */}
        <div className="md:col-span-2">
          <ActiveRun />
        </div>
      </div>
    </main>
  );
}