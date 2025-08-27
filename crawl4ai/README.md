# Crawl4AI SetUp

In terminal, cd into crawl4ai folder.

### Install Crawl4AI

Run in terminal: 
- pip install crawl4ai
- pip install beautifulsoup4
- pip install beautifulsoup4 aiohttp

### Setup

Run in terminal: 
- crawl4ai-setup

### Test Crawl4AI

Run in terminal: 
- python firstcrawl.py

# NAB Static Clone

### Run NAB crawler
- python crawl_nab.py

Should crawl 80 pages successfully.

### Download assets and build the static mirror
- python build_static_mirror.py

Wait for assets to be downloaded. Should be ~477.

### Deploy static mirror
- cd output\nab
- python -m http.server 8000
- Go to http://localhost:8000/www.nab.com.au/