
# 1 Build an absolute path (handles spaces)
$cfg = (Resolve-Path ".\norconex\nab-config.xml").Path

# 2 Validate the config
.\norconex\collector-http.bat configcheck -config="$cfg"

# 3 (Optional) Render the effective config to a file
.\norconex\collector-http.bat configrender -config="$cfg" > .\norconex\effective-config.xml

# 4 Start the crawler
.\norconex\collector-http.bat start -config="$cfg"

# 5 Gracefully stop later (must use the SAME path as start)
.\norconex\collector-http.bat stop -config="$cfg"

# 6 Clean the crawl store if you want a fresh run
.\norconex\collector-http.bat clean -config="$cfg"