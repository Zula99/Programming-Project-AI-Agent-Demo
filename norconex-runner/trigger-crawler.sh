#!/bin/bash

# Trigger script for starting crawls via file system
# This script monitors the configs directory for trigger files and executes crawls

TRIGGER_DIR="/opt/norconex/configs"
LOG_FILE="/opt/norconex/logs/trigger.log"

echo "$(date): Starting trigger crawler monitor..." >> "$LOG_FILE"

while true; do
    # Look for trigger files
    for trigger_file in "$TRIGGER_DIR"/trigger-*.json; do
        if [[ -f "$trigger_file" ]]; then
            echo "$(date): Found trigger file: $trigger_file" >> "$LOG_FILE"
            
            # Extract run_id from filename
            run_id=$(basename "$trigger_file" | sed 's/trigger-//' | sed 's/.json//')
            
            # Read the trigger data using simple text extraction
            config_path=$(grep -o "config_path.*xml" "$trigger_file" | cut -d'"' -f3)
            
            echo "$(date): DEBUG - Extracted config_path: [$config_path]" >> "$LOG_FILE"
            
            if [[ -f "$config_path" ]]; then
                echo "$(date): Executing crawl for $run_id with config $config_path" >> "$LOG_FILE"
                
                # Execute the crawler
                java -jar /app/norconex-runner.jar "$config_path" >> "$LOG_FILE" 2>&1
                exit_code=$?
                
                if [[ $exit_code -eq 0 ]]; then
                    echo "$(date): Crawl completed successfully for $run_id" >> "$LOG_FILE"
                    # Create completion file
                    echo '{"status":"completed","run_id":"'$run_id'","completed_at":"'$(date -Iseconds)'"}' > "$TRIGGER_DIR/completed-$run_id.json"
                else
                    echo "$(date): Crawl failed for $run_id with exit code $exit_code" >> "$LOG_FILE"
                    echo '{"status":"failed","run_id":"'$run_id'","error":"Exit code '$exit_code'","failed_at":"'$(date -Iseconds)'"}' > "$TRIGGER_DIR/failed-$run_id.json"
                fi
                
                # Remove trigger file
                rm "$trigger_file"
            else
                echo "$(date): Config file not found: $config_path" >> "$LOG_FILE"
                rm "$trigger_file"
            fi
        fi
    done
    
    sleep 2
done