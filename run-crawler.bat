@echo off
REM Run Norconex Crawler on Windows with optimized settings

echo Starting NAB Crawler with optimized settings...
echo ==============================================

REM Set Java heap size and garbage collection
set JAVA_OPTS=-Xmx2048m -Xms512m -XX:+UseG1GC -XX:MaxGCPauseMillis=200

REM Clean previous failed runs
echo Cleaning previous queue failures...
del /Q ".\norconex\workdir\nab-banking-collector\crawlstore\mvstore\*.lock" 2>nul
del /Q ".\norconex\workdir\nab-banking-collector\queue\*.lock" 2>nul

REM Create necessary directories
if not exist ".\norconex\out\xml" mkdir ".\norconex\out\xml"
if not exist ".\norconex\logs" mkdir ".\norconex\logs"
if not exist ".\norconex\progress" mkdir ".\norconex\progress"

REM Navigate to norconex folder and run crawler
echo Starting crawler...
cd norconex
call collector-http.bat start -clean -config="nab-crawlerv2.xml"
cd ..

echo.
echo Crawler completed. Check logs for details.
echo Output: .\norconex\out\xml\
echo Logs: .\norconex\logs\
pause