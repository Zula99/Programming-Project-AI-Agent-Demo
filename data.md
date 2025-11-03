AI AGENT DEMO FACTORY - DATABASE INFORMATION
==============================================

TEAM: RMIT Team BLUE (AA-661A)

DATABASE TYPE & VERSION
-----------------------
Primary Database: OpenSearch 2.11.0
Alternative: Elasticsearch-compatible

DEPLOYMENT ENVIRONMENT
----------------------
Environment: Docker Containerized
Container Name: opensearch-demo (Crawl4AI) / opensearch (Norconex)
Network: Bridge network (Docker Compose managed)

CONNECTION DETAILS
------------------

OpenSearch Instance:
  Host: localhost (external) / opensearch-demo (internal Docker network)
  Port: 9200
  Protocol: HTTP
  Scheme: http://

  Full Connection String:
    - External: http://localhost:9200
    - Internal (from backend containers): http://opensearch-demo:9200

OpenSearch Dashboards (UI):
  Host: localhost
  Port: 5601
  URL: http://localhost:5601

AUTHENTICATION
--------------
OpenSearch Admin:
  Username: admin
  Password: admin

  Note: Security plugin is DISABLED in development (plugins.security.disabled=true)
        For production deployment, enable security and change credentials.

API Authentication:
  Backend APIs: No authentication (development only)
  Crawl4AI API: http://localhost:8000 (no auth)
  Norconex API: http://localhost:5000 (no auth)

INDEXES & SCHEMA
----------------

Index 1: demo_factory_raw
  Purpose: Raw crawl data from Norconex collector
  Documents: Variable (depends on crawl)
  Mapping: Dynamic mapping with Norconex metadata
  Shards: 1
  Replicas: 0

Index 2: demo_factory
  Purpose: Enriched data with Search365 schema
  Documents: Processed from demo_factory_raw
  Schema Coverage: All critical fields populated from 229-field schema (title, content, metadata, HTML structure)
  Fields Include:
    - Core: id, url, title, content, description
    - Metadata: contenttype, encoding, docsize
    - Social: Open Graph, Twitter cards
    - Dates: crawltime, lastmodified, created
    - HTML: h2 headings, extracted elements
    - Location: state, suburb, postcode
    - Contact: email, phone, address

Index 3: demo-{domain}_{run_id}
  Purpose: Crawl4AI per-domain indexed content
  Example: demo-nab_com_au-abc123
  Documents: Crawled pages with full-text search
  Fields:
    - url, title, content_md (markdown)
    - meta_desc, h1, h2, h3, tags
    - fetched_at, indexed_at

Index 4: crawl_logs
  Purpose: Crawl execution logs and status tracking
  Documents: Log entries per crawl run

ADDITIONAL DATA STORAGE
-----------------------

Norconex Working Directory:
  Location: norconex-runner/data/workdir/
  Contents: MD5 checksums, crawl state, queues
  Persistence: Docker volume or bind mount

Crawl4AI Output:
  Location: ai-agent-demo-factory-backend/output/
  Structure:
    output/
    ├── agent_crawls/{domain}/{run_id}/
    │   ├── run_metadata.json
    │   └── {domain}/
    │       └── {url_hash}/
    │           ├── index.md
    │           ├── meta.json
    │           └── raw.html
    └── cost_logs/
        └── cost_session_{domain}_{timestamp}.json

AI Classification Cache:
  Location: output/{domain}/ai_cache/
  Files:
    - classification_cache.json (URL classifications)
    - domain_site_type.json (Site type detection)

EXTERNAL API DEPENDENCIES
--------------------------

OpenAI API:
  Service: Content classification
  Model: gpt-4o-mini
  Authentication: API key via OPENAI_API_KEY environment variable
  Cost: ~$0.0002 per URL classification
  Purpose: AI-powered URL and content worthiness assessment

BACKUP & PERSISTENCE
---------------------

Docker Volumes:
  opensearch-data: Persists all OpenSearch indexes
  Location: Managed by Docker (use 'docker volume inspect opensearch-data')

Manual Backup:
  # Export OpenSearch index
  curl -XGET "http://localhost:9200/demo_factory/_search?scroll=1m&size=1000" > backup.json

  # Backup Norconex workdir
  docker exec norconex-maven tar czf /tmp/workdir-backup.tar.gz /opt/norconex/data/workdir
  docker cp norconex-maven:/tmp/workdir-backup.tar.gz ./backups/

Restore:
  # Re-index from backup
  curl -XPOST "http://localhost:9200/_bulk" -H 'Content-Type: application/json' --data-binary @backup.json

HEALTH CHECKS
-------------

OpenSearch Health:
  curl http://localhost:9200/_cluster/health

Index Statistics:
  curl http://localhost:9200/_cat/indices?v

Document Count:
  curl http://localhost:9200/demo_factory/_count

PERFORMANCE CONFIGURATION
--------------------------

OpenSearch JVM Heap:
  Min Heap: 512m
  Max Heap: 512m
  Setting: OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m

Crawler Settings:
  Norconex Threads: 2
  Crawl4AI Concurrent: 1
  Request Gap: 0.8s (Crawl4AI), 2s (Norconex)

KNOWN LIMITATIONS
-----------------

1. Single-node OpenSearch (no replication)
2. No SSL/TLS encryption (HTTP only)
3. Default admin credentials (security disabled)
4. Limited to local development deployment
5. No automated backup scheduling

PRODUCTION DEPLOYMENT NOTES
----------------------------

For production deployment, implement:
- Enable OpenSearch security plugin
- Change default admin credentials
- Configure SSL/TLS certificates
- Set up multi-node cluster for high availability
- Implement automated backups
- Add firewall rules and network security
- Enable authentication on backend APIs
- Configure proper CORS policies

SUPPORT RESOURCES
-----------------

OpenSearch Documentation: https://opensearch.org/docs/latest/
OpenSearch Dashboards: http://localhost:5601 (when running)
API Documentation: http://localhost:8000/docs (Crawl4AI), http://localhost:5000/docs (Norconex)
