package io.demo.nx;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Runner {
    
    private static final Logger logger = LoggerFactory.getLogger(Runner.class);
    
    public static void main(String[] args) {
        logger.info("Norconex Runner starting with {} arguments", args.length);
        
        if (args.length > 0) {
            logger.info("Arguments received:");
            for (int i = 0; i < args.length; i++) {
                logger.info("  [{}]: {}", i, args[i]);
            }
        }
        
        System.out.println("OK");
        
        logger.info("Norconex Runner completed successfully");
    }
}