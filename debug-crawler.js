// debug-crawler.js - Monitor and debug crawler issues
const fs = require('fs');
const path = require('path');

// Configuration
const OPENSEARCH_URL = 'http://localhost:9200';
const INDEX_NAME = 'demo_factory';
const WORKDIR = './norconex/workdir/nab-banking-collector';
const OUTPUT_DIR = './norconex/out/xml';

async function makeRequest(url, options = {}) {
    const http = require('http');
    const urlModule = require('url');

    return new Promise((resolve, reject) => {
        const parsedUrl = urlModule.parse(url);
        const req = http.request({
            hostname: parsedUrl.hostname,
            port: parsedUrl.port,
            path: parsedUrl.path,
            method: options.method || 'GET',
            headers: options.headers || {}
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        status: res.statusCode,
                        data: res.statusCode === 204 ? {} : JSON.parse(data)
                    });
                } catch (e) {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });

        req.on('error', reject);
        if (options.body) {
            req.write(typeof options.body === 'string' ? options.body : JSON.stringify(options.body));
        }
        req.end();
    });
}

async function checkCrawlerStatus() {
    console.log('\ CRAWLER STATUS CHECK');
    console.log('======================\n');

    // 1. Check OpenSearch status
    try {
        const health = await makeRequest(`${OPENSEARCH_URL}/_cluster/health`);
        console.log(' OpenSearch Status:', health.data.status);

        const count = await makeRequest(`${OPENSEARCH_URL}/${INDEX_NAME}/_count`);
        console.log(` Documents indexed: ${count.data.count || 0}`);
    } catch (e) {
        console.log(' OpenSearch not reachable:', e.message);
    }

    // 2. Check crawler work directory
    console.log('\n CRAWLER WORK DIRECTORY:');

    // Check for lock files (indicates crash)
    const findLockFiles = (dir) => {
        if (!fs.existsSync(dir)) return [];

        let locks = [];
        const items = fs.readdirSync(dir);

        for (const item of items) {
            const fullPath = path.join(dir, item);
            const stat = fs.statSync(fullPath);

            if (stat.isDirectory()) {
                locks = locks.concat(findLockFiles(fullPath));
            } else if (item.includes('.lock') || item.includes('.lck')) {
                locks.push(fullPath);
            }
        }
        return locks;
    };

    const lockFiles = findLockFiles(WORKDIR);
    if (lockFiles.length > 0) {
        console.log(' Lock files found (crawler may have crashed):');
        lockFiles.forEach(f => console.log('   -', f));
    } else {
        console.log(' No lock files found');
    }

    // 3. Check queue status
    const queueDir = path.join(WORKDIR, 'queue');
    if (fs.existsSync(queueDir)) {
        const queueFiles = fs.readdirSync(queueDir);
        console.log(`\n Queue status: ${queueFiles.length} batch files`);

        // Check for failed batches
        const failedBatches = queueFiles.filter(f => f.includes('failed') || f.includes('error'));
        if (failedBatches.length > 0) {
            console.log(`  Failed batches: ${failedBatches.length}`);
        }
    }

    // 4. Check output
    if (fs.existsSync(OUTPUT_DIR)) {
        const outputFiles = fs.readdirSync(OUTPUT_DIR);
        const xmlFiles = outputFiles.filter(f => f.endsWith('.xml'));
        console.log(`\nOutput XML files: ${xmlFiles.length}`);

        // Count total documents
        let totalDocs = 0;
        xmlFiles.forEach(file => {
            const content = fs.readFileSync(path.join(OUTPUT_DIR, file), 'utf-8');
            const docMatches = content.match(/<doc>/g);
            if (docMatches) totalDocs += docMatches.length;
        });
        console.log(` Total documents in XMLs: ${totalDocs}`);
    }

    // 5. Check logs for errors
    const logsDir = './norconex/logs';
    if (fs.existsSync(logsDir)) {
        const logFiles = fs.readdirSync(logsDir).sort().reverse();
        if (logFiles.length > 0) {
            const latestLog = path.join(logsDir, logFiles[0]);
            const logContent = fs.readFileSync(latestLog, 'utf-8');

            console.log(`\n Latest log: ${logFiles[0]}`);

            // Check for common errors
            const errorPatterns = [
                { pattern: /OutOfMemoryError/gi, message: 'Out of Memory errors' },
                { pattern: /SocketTimeoutException/gi, message: 'Socket timeout errors' },
                { pattern: /ConnectException/gi, message: 'Connection errors' },
                { pattern: /rejected from/gi, message: 'Queue rejection errors' },
                { pattern: /ERROR.*Elasticsearch/gi, message: 'OpenSearch/ES errors' },
                { pattern: /ERROR.*committer/gi, message: 'Committer errors' }
            ];

            console.log('\n Error Analysis:');
            errorPatterns.forEach(({ pattern, message }) => {
                const matches = logContent.match(pattern);
                if (matches) {
                    console.log(`     ${message}: ${matches.length} occurrences`);
                }
            });

            // Get last few lines
            const lines = logContent.split('\n');
            const lastLines = lines.slice(-10).filter(l => l.trim());
            console.log('\n Last log entries:');
            lastLines.forEach(line => console.log('   ', line.substring(0, 100)));
        }
    }

    // 6. Memory usage
    const memUsage = process.memoryUsage();
    console.log('\n Current Node Memory Usage:');
    console.log(`   Heap: ${Math.round(memUsage.heapUsed / 1024 / 1024)}MB / ${Math.round(memUsage.heapTotal / 1024 / 1024)}MB`);
    console.log(`   RSS: ${Math.round(memUsage.rss / 1024 / 1024)}MB`);
}

async function analyzeCrawledUrls() {
    console.log('\n CRAWLED URL ANALYSIS');
    console.log('=======================\n');

    try {
        // Get all URLs from OpenSearch
        const response = await makeRequest(`${OPENSEARCH_URL}/${INDEX_NAME}/_search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                size: 1000,
                _source: ['url', 'crawl_depth'],
                sort: [{ crawl_depth: 'asc' }]
            })
        });

        if (response.data.hits) {
            const urls = response.data.hits.hits.map(h => h._source);

            // Group by domain
            const domains = {};
            urls.forEach(({ url, crawl_depth }) => {
                try {
                    const urlObj = new URL(url);
                    const domain = urlObj.hostname;
                    if (!domains[domain]) domains[domain] = [];
                    domains[domain].push({ url, depth: crawl_depth });
                } catch (e) { }
            });

            // Report
            console.log(' Domains crawled:');
            Object.entries(domains).forEach(([domain, urls]) => {
                console.log(`\n   ${domain}: ${urls.length} pages`);
                // Show first few URLs
                urls.slice(0, 3).forEach(({ url, depth }) => {
                    console.log(`      - [Depth ${depth}] ${url.substring(0, 80)}`);
                });
                if (urls.length > 3) {
                    console.log(`      ... and ${urls.length - 3} more`);
                }
            });

            // Check for unwanted domains
            const unwantedDomains = Object.keys(domains).filter(d =>
                !d.includes('nab.com.au')
            );

            if (unwantedDomains.length > 0) {
                console.log('\n  WARNING: Crawler went to unwanted domains:');
                unwantedDomains.forEach(d => console.log(`   - ${d} (${domains[d].length} pages)`));
            }
        }
    } catch (e) {
        console.log(' Could not analyze URLs:', e.message);
    }
}

async function cleanupFailedRun() {
    console.log('\n CLEANUP FAILED RUN');
    console.log('====================\n');

    const cleanup = [
        `${WORKDIR}/crawlstore/mvstore/*.lock`,
        `${WORKDIR}/queue/*.lock`,
        `${WORKDIR}/queue/*failed*`,
        `${WORKDIR}/queue/*error*`
    ];

    cleanup.forEach(pattern => {
        const dir = path.dirname(pattern);
        const filePattern = path.basename(pattern);

        if (fs.existsSync(dir)) {
            const files = fs.readdirSync(dir);
            files.forEach(file => {
                if (filePattern.includes('*')) {
                    const regex = new RegExp(filePattern.replace(/\*/g, '.*'));
                    if (regex.test(file)) {
                        const fullPath = path.join(dir, file);
                        try {
                            fs.unlinkSync(fullPath);
                            console.log(` Removed: ${fullPath}`);
                        } catch (e) {
                            console.log(` Could not remove: ${fullPath}`);
                        }
                    }
                }
            });
        }
    });

    console.log('\n Cleanup complete. You can restart the crawler now.');
}

// Main execution
async function main() {
    console.log(' NORCONEX CRAWLER DEBUGGER');
    console.log('=============================');

    await checkCrawlerStatus();
    await analyzeCrawledUrls();

    // Ask if cleanup is needed
    console.log('\n Do you want to clean up failed runs? (Run with --cleanup flag)');

    if (process.argv.includes('--cleanup')) {
        await cleanupFailedRun();
    }
}

main().catch(console.error);