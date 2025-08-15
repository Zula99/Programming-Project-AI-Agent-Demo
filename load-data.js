const fs = require('fs');
const path = require('path');

// Simple HTTP request function (no dependencies needed)
async function makeRequest(url, options = {}) {
    const http = require('http');
    const https = require('https');
    const urlModule = require('url');

    return new Promise((resolve, reject) => {
        const parsedUrl = urlModule.parse(url);
        const lib = parsedUrl.protocol === 'https:' ? https : http;

        const req = lib.request({
            hostname: parsedUrl.hostname,
            port: parsedUrl.port,
            path: parsedUrl.path,
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
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

async function loadDataToOpenSearch() {
    const OPENSEARCH_URL = 'http://localhost:9200';
    const INDEX_NAME = 'nab_search';

    console.log('🔍 Loading NAB data into OpenSearch...');

    try {
        // Test connection
        console.log('Testing OpenSearch connection...');
        const healthCheck = await makeRequest(OPENSEARCH_URL);
        console.log('✅ OpenSearch is running:', healthCheck.data.cluster_name);

        // Create index with proper mapping
        console.log('Creating index with mapping...');
        const indexMapping = {
            mappings: {
                properties: {
                    title: { type: 'text', analyzer: 'standard' },
                    content: { type: 'text', analyzer: 'standard' },
                    url: { type: 'keyword' },
                    description: { type: 'text' },
                    'og:description': { type: 'text' },
                    'dc:title': { type: 'text' },
                    's365:title': { type: 'text' },
                    metadata: { type: 'object', enabled: false }
                }
            }
        };

        await makeRequest(`${OPENSEARCH_URL}/${INDEX_NAME}`, {
            method: 'PUT',
            body: indexMapping
        });
        console.log('✅ Index created with mapping');

        // Read your exported data
        const dataFiles = [
            './demo-results/search-proof/all-docs.json',
            './demo-results/search-proof/full-index-export.json'
        ];

        let totalDocs = 0;

        for (const filePath of dataFiles) {
            if (!fs.existsSync(filePath)) {
                console.log(`⏭️  Skipping ${filePath} - file not found`);
                continue;
            }

            console.log(`📄 Processing ${filePath}...`);

            try {
                // Read file with UTF-16 LE encoding (your files are UTF-16)
                let rawData = fs.readFileSync(filePath, 'utf16le');

                // Remove BOM if present
                if (rawData.charCodeAt(0) === 0xFEFF) {
                    rawData = rawData.slice(1);
                    console.log('✅ BOM removed from', filePath);
                }

                // Check first few characters
                console.log(`First 50 characters: ${rawData.substring(0, 50)}`);

                const elasticsearchResponse = JSON.parse(rawData);

                // Extract documents from Elasticsearch export format
                const documents = elasticsearchResponse.hits.hits;
                console.log(`Found ${documents.length} documents in ${filePath}`);

                // Prepare bulk index operations
                const bulkOps = [];

                documents.forEach(doc => {
                    const source = doc._source;

                    // Create a clean document for OpenSearch
                    const cleanDoc = {
                        url: source['Content-Location'] || doc._id,
                        title: source['s365:title'] || source['dc:title'] || 'Untitled',
                        description: source['og:description'] || '',
                        content: source.content || source['og:description'] || '',
                        metadata: {
                            depth: source['collector.depth'],
                            contentType: source['document.contentType'],
                            sitemap: {
                                changefreq: source['collector.sitemap-changefreq'],
                                priority: source['collector.sitemap-priority']
                            }
                        }
                    };

                    // Add index operation
                    bulkOps.push({ index: { _index: INDEX_NAME, _id: doc._id } });
                    bulkOps.push(cleanDoc);
                });

                // Bulk index to OpenSearch
                if (bulkOps.length > 0) {
                    console.log(`📤 Bulk indexing ${documents.length} documents...`);
                    const bulkBody = bulkOps.map(op => JSON.stringify(op)).join('\n') + '\n';

                    const bulkResponse = await makeRequest(`${OPENSEARCH_URL}/_bulk`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-ndjson' },
                        body: bulkBody
                    });

                    if (bulkResponse.data.errors) {
                        console.log('⚠️  Some indexing errors occurred');
                        console.log(bulkResponse.data.items.filter(item => item.index.error));
                    } else {
                        console.log(`✅ Successfully indexed ${documents.length} documents`);
                        totalDocs += documents.length;
                    }
                }

            } catch (parseError) {
                console.error(`❌ Failed to parse ${filePath}:`, parseError.message);
                console.log('File size:', fs.statSync(filePath).size, 'bytes');

                // Try to read as buffer and show encoding info
                const buffer = fs.readFileSync(filePath);
                console.log('First 20 bytes as hex:', buffer.slice(0, 20).toString('hex'));
                console.log('First 100 chars as latin1:', buffer.slice(0, 100).toString('latin1'));

                continue;
            }
        }

        // Refresh index
        await makeRequest(`${OPENSEARCH_URL}/${INDEX_NAME}/_refresh`, {
            method: 'POST'
        });

        console.log(`\n🎉 Data loading complete! Total documents: ${totalDocs}`);
        console.log(`\n🔍 Test your search:`);
        console.log(`curl "${OPENSEARCH_URL}/${INDEX_NAME}/_search?q=banking"`);
        console.log(`\n📊 View all documents:`);
        console.log(`curl "${OPENSEARCH_URL}/${INDEX_NAME}/_search?size=20"`);

    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
}

// Run the loader
loadDataToOpenSearch();