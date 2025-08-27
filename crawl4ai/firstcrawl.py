from crawl4ai import AsyncWebCrawler
import asyncio
import os

async def main():
    # Make an "output" folder in your repo if it doesn't exist
    os.makedirs("output", exist_ok=True)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")

        # Save results to a markdown file in your repo
        with open("output/example.md", "w", encoding="utf-8") as f:
            f.write(result.markdown)

        print("✅ Crawl complete! Saved to output/example.md")

if __name__ == "__main__":
    asyncio.run(main())
