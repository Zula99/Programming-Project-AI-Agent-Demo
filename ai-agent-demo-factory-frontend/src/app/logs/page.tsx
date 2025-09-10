import Header from "@/components/Header";
import CrawlLogs from "@/components/CrawlLogs";

export default function LogsPage() {
  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <Header />
      
      <div className="mt-6">
        <CrawlLogs />
      </div>
    </main>
  );
}