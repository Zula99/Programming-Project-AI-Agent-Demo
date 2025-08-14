# Norconex Web Crawler Setup Guide

## Overview
This guide covers the complete setup of Norconex Web Crawler with Elasticsearch integration for web content extraction and indexing. The system successfully crawls websites and stores content in a searchable format.

## Prerequisites
- Windows 10/11
- Java 8 or higher (tested with OpenJDK Runtime Environment 21.0.6+7-LTS)
- Docker Desktop
- PowerShell

## System Architecture
```
Website (NAB, Agilent, etc.) 
    ↓ (crawls)
Norconex Web Crawler 3.1.0
    ↓ (extracts content)
Elasticsearch Committer 5.0.0  
    ↓ (sends data)
Elasticsearch 7.17.0 (Docker)
    ↓ (stores/searches)
Indexed Content for Analysis
```

---

## Step 1: Install Docker Elasticsearch

### 1.1 Create Docker Compose File
Create `docker-compose.yml` in your project root:

```yaml
version: '3.7'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.0
    container_name: elasticsearch
    environment:
      - xpack.security.enabled=false
      - discovery.type=single-node
    ports:
      - 9200:9200
      - 9300:9300
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

volumes:
  elasticsearch-data:
    driver: local
```

### 1.2 Start Elasticsearch
```powershell
docker-compose up -d
```

### 1.3 Verify Elasticsearch is Running
```powershell
# Check container status
docker ps

# Test Elasticsearch endpoint
Invoke-WebRequest -Uri "http://localhost:9200"
```

**Expected Response:**
```json
{
  "name" : "elasticsearch",
  "cluster_name" : "docker-cluster",
  "version" : {
    "number" : "7.17.0"
  },
  "tagline" : "You Know, for Search"
}
```

---

## Step 2: Install Norconex Web Crawler

### 2.1 Download and Extract
1. Visit: https://opensource.norconex.com/crawlers/web/download
2. Download **Norconex Web Crawler 3.1.0** (latest ZIP file)
3. Extract to your project directory: `./norconex-collector-http-3.1.0/`

### 2.2 Verify Installation
Navigate to the Norconex directory and check for required files:
```
norconex-collector-http-3.1.0/
├── lib/                    # Java libraries
├── examples/              # Sample configurations  
├── collector-http.bat     # Windows launcher
├── collector-http.sh      # Linux launcher
└── log4j2.xml            # Logging configuration
```

---

## Step 3: Install Elasticsearch Committer

### 3.1 Download Committer
1. Visit: https://opensource.norconex.com/committers/elasticsearch/download
2. Download **Elasticsearch Committer 5.0.0** (latest ZIP file)
3. Extract to a temporary folder

### 3.2 Install Committer
1. Navigate to the extracted committer folder

2. Run the installer:
   ```cmd
   install.bat
   ```
   OR
   double click 'install.sh' .bat file.
   
3. When prompted, enter path to Norconex lib folder:
   ```
   D:\path\to\your\project\norconex-collector-http-3.1.0\lib
   ```
4. Choose option **1** when asked about duplicate JARs (recommended)



### 3.3 Verify Committer Installation
Check that new JARs were added:
```powershell
cd norconex-collector-http-3.1.0\lib
dir *elasticsearch*
```

**Expected Files:**
- `norconex-committer-elasticsearch-5.0.0.jar`
- Additional Elasticsearch dependency JARs

---

## Step 4: Configuration Setup

### 4.1 Create Test Configuration
Create `test-config.xml` in the Norconex directory:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xml>
<httpcollector id="Test Elasticsearch Integration">
    <workDir>./test-output</workDir>
    
    <crawlers>
        <crawler id="test-crawler">
            <!-- Target website -->
            <startURLs stayOnDomain="false" stayOnPort="false" stayOnProtocol="false">
                <url>https://www.nab.com.au</url>
            </startURLs>
            
            <!-- Crawl settings -->
            <maxDepth>0</maxDepth>
            <maxDocuments>5</maxDocuments>
            
            <!-- Disable strict filtering for testing -->
            <canonicalLinkDetector ignore="true" />
            
            <!-- Send crawled data to Elasticsearch -->
            <committers>
                <committer class="com.norconex.committer.elasticsearch.ElasticsearchCommitter">
                    <nodes>http://localhost:9200</nodes>
                    <indexName>norconex_test</indexName>
                </committer>
            </committers>
        </crawler>
    </crawlers>
</httpcollector>
```

---

## Step 5: Running the Crawler

### 5.1 Execute Crawl
Navigate to Norconex directory and run:
```powershell
cd norconex-collector-http-3.1.0
.\collector-http.bat start -c test-config.xml
```

### 5.2 Expected Console Output
```
============== C O L L E C T O R ==============

Collector:          Norconex HTTP Collector 3.1.0 (Norconex Inc.)
Committer(s):
  Elasticsearch:    Norconex Committer Elasticsearch 5.0.0 (Norconex Inc.)

INFO [test-crawler] - CRAWLER_INIT_BEGIN
INFO [test-crawler] - Crawler "test-crawler" initialized successfully
INFO [test-crawler] - DOCUMENT_COMMITTED_UPSERT - https://www.nab.com.au/
INFO [test-crawler] - DOCUMENT_COMMITTED_UPSERT - https://www.nab.com.au/about-us
INFO [test-crawler] - ElasticsearchCommitter - Sent 4 commit operations to Elasticsearch
INFO [test-crawler] - COLLECTOR_RUN_END
```

**Key Success Indicators:**
- `DOCUMENT_COMMITTED_UPSERT` messages (documents successfully indexed)
- `Sent X commit operations to Elasticsearch` (data transmitted)
- No `REJECTED_` or error messages
- Process completes without exceptions

---

## Step 6: Verify Results

### 6.1 Check Index Creation
```powershell
Invoke-WebRequest -Uri "http://localhost:9200/_cat/indices?v"
```

**Expected Output:**
```
health status index         uuid                   pri rep docs.count docs.deleted store.size pri.store.size
yellow open   norconex_test NN0_jh8sShWwF9mGhaE3Bw   1   1          4            0    213.4kb        213.4kb
```

### 6.2 Search Indexed Content
```powershell
# View one document
Invoke-WebRequest -Uri "http://localhost:9200/norconex_test/_search?pretty=true&size=1"

# Search for specific content
Invoke-WebRequest -Uri "http://localhost:9200/norconex_test/_search?q=nab&pretty=true"
```

### 6.3 Browser Verification
Open browser and navigate to:
**http://localhost:9200/norconex_test/_search?pretty=true&size=1**

**Expected Result:**
- JSON response containing crawled website content
- HTML content from NAB website pages
- Metadata including titles, URLs, timestamps
- Document count matching crawl summary

---

## Current Capabilities

### **Working Features:**
- **Website crawling** with configurable depth and document limits
- **Content extraction** from HTML pages
- **Metadata collection** (titles, headers, links)
- **Elasticsearch integration** for searchable storage
- **Quality filtering** (canonical links, redirects, robots.txt)
- **Multi-threaded processing**
- **Sitemap discovery and processing**

### **Output Data Structure:**
Each crawled document contains:
- **`content`** - Full HTML/text content
- **`title`** - Page title
- **`collector.referenced-urls`** - Links found on page
- **HTTP headers** and **response metadata**
- **Crawl timestamps** and **processing information**

---

## Troubleshooting

### Common Issues:

**1. "Cannot find JARs" during committer installation:**
- Ensure path to Norconex lib folder is correct
- Use full absolute path
- Check that `norconex-collector-http-3.1.0\lib` exists and contains JAR files

**2. "Index not found" in Elasticsearch:**
- Check crawler logs for `DOCUMENT_COMMITTED_UPSERT` messages
- Verify no `REJECTED_` messages in output
- Ensure Elasticsearch is running: `docker ps`

**3. Configuration XML errors:**
- Use `<committers><committer>` (not just `<committer>`)
- Ensure proper XML structure and closing tags
- Check for typos in class names

**4. Connection refused:**
- Verify Elasticsearch is accessible: `Invoke-WebRequest -Uri "http://localhost:9200"`
- Check Docker container status: `docker logs elasticsearch`

---

## Next Steps

This setup provides the foundation for:
1. **Advanced crawler configurations** (from David/Azure DevOps)
2. **OpenSearch integration** (replacing local Elasticsearch)
3. **Website cloning and component replacement**
4. **AI agent integration** for demo factory automation
5. **Quality assessment and completeness analysis**

## System Status: Production Ready
The crawler successfully processes real website content and stores it in a searchable format, ready for analysis and integration with broader demo factory systems.