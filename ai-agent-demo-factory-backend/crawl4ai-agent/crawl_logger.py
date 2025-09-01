# Comprehensive Crawl Logging System
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, TextIO
import threading


class CrawlLogger:
    """
    Comprehensive logging system that captures all output during crawl/mirror process.
    Automatically saves logs with domain-based naming and incremental numbering.
    """
    
    def __init__(self, base_url: str, output_dir: str = "./output/logs"):
        self.base_url = base_url
        self.domain = self._extract_domain(base_url)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique log filename
        self.log_filename = self._generate_log_filename()
        self.log_path = self.output_dir / self.log_filename
        
        # Set up logging
        self.logger = None
        self.log_file = None
        self.original_stdout = None
        self.original_stderr = None
        self.start_time = None
        
    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. and clean up
            domain = domain.replace('www.', '').replace('/', '')
            # Handle cases like 'example.com' or 'https://example.com'
            if domain.startswith('http'):
                domain = urlparse(domain).netloc
            return domain
        except:
            return "unknown_domain"
    
    def _generate_log_filename(self) -> str:
        """Generate unique log filename with domain and timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{self.domain}_crawl_{timestamp}"
        
        # Check for existing files and increment
        counter = 1
        filename = f"{base_name}.log"
        
        while (self.output_dir / filename).exists():
            filename = f"{base_name}_{counter:02d}.log"
            counter += 1
            
        return filename
    
    def start_logging(self):
        """Start comprehensive logging of all output"""
        self.start_time = time.time()
        
        # Create file handler
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        
        # Set up logger
        self.logger = logging.getLogger(f'crawl_logger_{self.domain}')
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Log session start
        self.logger.info("="*80)
        self.logger.info(f"CRAWL SESSION STARTED")
        self.logger.info(f"Target URL: {self.base_url}")
        self.logger.info(f"Domain: {self.domain}")
        self.logger.info(f"Log file: {self.log_filename}")
        self.logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*80)
        
        # Capture stdout/stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        sys.stdout = TeeOutput(self.original_stdout, self.log_file)
        sys.stderr = TeeOutput(self.original_stderr, self.log_file)
        
        print(f"🔍 Crawl logging started - saving to: {self.log_path}")
        
    def log_phase(self, phase_name: str, details: str = ""):
        """Log a specific phase of the crawl process"""
        if self.logger:
            self.logger.info(f"PHASE: {phase_name} - {details}")
            print(f"📊 {phase_name}: {details}")
    
    def log_error(self, error: Exception, context: str = ""):
        """Log an error with context"""
        if self.logger:
            self.logger.error(f"ERROR in {context}: {str(error)}")
            self.logger.error(f"Error type: {type(error).__name__}")
    
    def log_metrics(self, metrics: dict):
        """Log quality metrics and stats"""
        if self.logger:
            self.logger.info("QUALITY METRICS:")
            for key, value in metrics.items():
                self.logger.info(f"  {key}: {value}")
    
    def stop_logging(self, success: bool = True, final_message: str = ""):
        """Stop logging and write session summary"""
        if not self.logger:
            return
            
        # Calculate duration
        duration = time.time() - self.start_time if self.start_time else 0
        
        # Log session end
        self.logger.info("="*80)
        self.logger.info(f"CRAWL SESSION ENDED")
        self.logger.info(f"Status: {'SUCCESS' if success else 'FAILED'}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        if final_message:
            self.logger.info(f"Final message: {final_message}")
        self.logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*80)
        
        # Restore stdout/stderr
        if self.original_stdout:
            sys.stdout = self.original_stdout
        if self.original_stderr:
            sys.stderr = self.original_stderr
            
        # Close file handlers
        if self.logger:
            for handler in self.logger.handlers:
                handler.close()
                self.logger.removeHandler(handler)
                
        if self.log_file:
            self.log_file.close()
            
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} Crawl log saved to: {self.log_path}")
        print(f"📊 Session duration: {duration:.1f}s")


class TeeOutput:
    """Helper class to duplicate output to both console and file"""
    
    def __init__(self, original: TextIO, log_file: TextIO):
        self.original = original
        self.log_file = log_file
        self.lock = threading.Lock()
    
    def write(self, text: str):
        with self.lock:
            # Write to original (console)
            self.original.write(text)
            # Write to log file with timestamp prefix for non-empty lines
            if text.strip():
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_file.write(f"[{timestamp}] {text}")
            else:
                self.log_file.write(text)
            self.log_file.flush()
    
    def flush(self):
        self.original.flush()
        self.log_file.flush()
    
    def isatty(self):
        return self.original.isatty()


# Context manager for easy use
class CrawlSession:
    """Context manager for crawl logging"""
    
    def __init__(self, base_url: str, output_dir: str = "./output/logs"):
        self.logger = CrawlLogger(base_url, output_dir)
        self.success = False
        
    def __enter__(self):
        self.logger.start_logging()
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error_msg = str(exc_val) if exc_val else ""
        self.logger.stop_logging(success, error_msg)


# Example usage for integration
async def log_crawl_process(base_url: str, crawl_function):
    """Wrapper function to log any crawl process"""
    
    with CrawlSession(base_url) as logger:
        try:
            logger.log_phase("INITIALIZATION", "Starting crawl process")
            
            # Run the actual crawl
            result = await crawl_function(base_url)
            
            logger.log_phase("COMPLETION", "Crawl process finished")
            
            # Log metrics if available
            if hasattr(result, '__dict__'):
                logger.log_metrics(result.__dict__)
                
            return result
            
        except Exception as e:
            logger.log_error(e, "crawl_process")
            raise