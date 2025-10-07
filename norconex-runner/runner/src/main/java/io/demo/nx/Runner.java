package io.demo.nx;

import com.norconex.collector.http.HttpCollector;
import com.norconex.collector.http.HttpCollectorConfig;
import com.norconex.commons.lang.xml.XML;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.atomic.AtomicReference;

public class Runner {
    
    private static final Logger logger = LoggerFactory.getLogger(Runner.class);
    private static final AtomicReference<HttpCollector> currentCollector = new AtomicReference<>();
    
    public static void main(String[] args) {
        logger.info("Norconex Runner starting with {} arguments", args.length);
        
        if (args.length == 0) {
            logger.error("Usage: java -jar runner.jar <config-file>");
            System.exit(1);
        }
        
        String configFile = args[0];
        logger.info("Using config file: {}", configFile);
        
        try {
            runCrawler(configFile);
        } catch (Exception e) {
            logger.error("Crawler execution failed", e);
            System.exit(1);
        }
        
        logger.info("Norconex Runner completed successfully");
    }
    
    private static void runCrawler(String configFile) throws Exception {
        logger.info("Starting crawler with config: {}", configFile);
        
        // Verify config file exists
        Path configPath = Paths.get(configFile);
        File configFileObj = configPath.toFile();
        if (!configFileObj.exists()) {
            throw new IllegalArgumentException("Config file not found: " + configFile);
        }
        
        logger.info("Config file exists: {} ({} bytes)", configFile, configFileObj.length());
        
        try {
            // Load configuration
            XML xml = XML.of(configFileObj).create();
            HttpCollectorConfig config = new HttpCollectorConfig();
            config.loadFromXML(xml);
            
            logger.info("Configuration loaded successfully");
            
            // Create and run collector
            HttpCollector collector = new HttpCollector(config);
            currentCollector.set(collector);
            
            // Add shutdown hook to clean up gracefully
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                HttpCollector col = currentCollector.get();
                if (col != null) {
                    logger.info("Shutting down collector gracefully...");
                    col.stop();
                }
            }));
            
            logger.info("Starting crawl operation...");
            collector.start();
            
            logger.info("Crawl operation completed");
            
        } catch (Exception e) {
            logger.error("Error during crawl execution", e);
            throw e;
        } finally {
            currentCollector.set(null);
        }
        
        logger.info("Crawler completed successfully");
    }
}