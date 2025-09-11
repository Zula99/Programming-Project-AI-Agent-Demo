"""
AI Configuration Management
Handles API keys, model selection, and AI service settings.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import json

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file from current directory or parent directories
except ImportError:
    # dotenv not available, will just use system environment variables
    pass

@dataclass
class AIConfig:
    """Configuration for AI services"""
    # API Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Model Selection
    preferred_model: str = "gpt-4o-mini"  # or "claude-3-haiku", "local"
    fallback_model: str = "heuristic"
    
    # Rate Limiting
    requests_per_minute: int = 20
    min_request_interval: float = 1.0  # seconds
    
    # Cost Controls
    max_monthly_cost: float = 50.0  # USD
    max_tokens_per_request: int = 1000
    
    # Caching
    enable_caching: bool = True
    cache_ttl_days: int = 30
    
    # Fallback Settings
    heuristic_threshold: float = 0.6
    confidence_threshold: float = 0.7
    
    # Logging
    log_ai_decisions: bool = True
    save_prompts: bool = False  # For debugging

class AIConfigManager:
    """Manages AI configuration from environment and config files"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("output/ai_config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> AIConfig:
        """Load configuration from file and environment"""
        config_data = {}
        
        # Load from config file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load AI config file: {e}")
        
        # Override with environment variables
        env_config = {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
            'preferred_model': os.getenv('AI_MODEL', config_data.get('preferred_model', 'gpt-4o-mini')),
            'requests_per_minute': int(os.getenv('AI_RATE_LIMIT', config_data.get('requests_per_minute', 20))),
            'max_monthly_cost': float(os.getenv('AI_MAX_COST', config_data.get('max_monthly_cost', 50.0))),
            'enable_caching': os.getenv('AI_CACHING', '').lower() != 'false',
        }
        
        # Merge config_data with env_config (env takes precedence)
        merged_config = {**config_data, **{k: v for k, v in env_config.items() if v is not None}}
        
        return AIConfig(**merged_config)
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            self.config_file.parent.mkdir(exist_ok=True, parents=True)
            
            # Convert dataclass to dict, excluding None values for API keys
            config_dict = {}
            for field_name, field_value in self.config.__dict__.items():
                if field_name.endswith('_api_key') and field_value is None:
                    continue  # Don't save None API keys
                config_dict[field_name] = field_value
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save AI config: {e}")
    
    def get_available_models(self) -> Dict[str, bool]:
        """Check which AI models are available based on API keys"""
        available = {
            'heuristic': True,  # Always available
            'gpt-4o-mini': bool(self.config.openai_api_key),
            'gpt-3.5-turbo': bool(self.config.openai_api_key),
            'gpt-4': bool(self.config.openai_api_key),
            'claude-3-haiku': bool(self.config.anthropic_api_key),
            'claude-3-sonnet': bool(self.config.anthropic_api_key),
        }
        return available
    
    def get_best_available_model(self) -> str:
        """Get the best available model based on API keys and preferences"""
        available = self.get_available_models()
        
        # Try preferred model first
        if available.get(self.config.preferred_model, False):
            return self.config.preferred_model
        
        # Try fallback model
        if available.get(self.config.fallback_model, False):
            return self.config.fallback_model
        
        # Default to heuristic
        return 'heuristic'
    
    def create_sample_config(self) -> str:
        """Create a sample configuration file and return instructions"""
        sample_config = {
            "preferred_model": "gpt-4o-mini",
            "fallback_model": "heuristic", 
            "requests_per_minute": 20,
            "max_monthly_cost": 50.0,
            "enable_caching": True,
            "cache_ttl_days": 30,
            "heuristic_threshold": 0.6,
            "confidence_threshold": 0.7,
            "log_ai_decisions": True,
            "save_prompts": False
        }
        
        sample_file = self.config_file.parent / "ai_config_sample.json"
        sample_file.parent.mkdir(exist_ok=True, parents=True)
        
        with open(sample_file, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        instructions = f"""
AI Configuration Setup:

1. Copy the sample config:
   cp {sample_file} {self.config_file}

2. Set your API keys (choose one):
   
   Option A - Environment variables (recommended):
   export OPENAI_API_KEY="your-openai-key-here"
   export ANTHROPIC_API_KEY="your-anthropic-key-here"
   
   Option B - Docker environment:
   Add to docker-compose.yml:
   environment:
     - OPENAI_API_KEY=your-openai-key-here
     - ANTHROPIC_API_KEY=your-anthropic-key-here
   
   Option C - Config file (less secure):
   Edit {self.config_file} and add:
   "openai_api_key": "your-key-here"

3. Adjust settings in {self.config_file} as needed

Current status: {self.get_best_available_model()} model will be used
"""
        return instructions

# Global config instance
_config_manager = None

def get_ai_config() -> AIConfig:
    """Get the global AI configuration"""
    global _config_manager
    if _config_manager is None:
        _config_manager = AIConfigManager()
    return _config_manager.config

def get_config_manager() -> AIConfigManager:
    """Get the global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = AIConfigManager()
    return _config_manager

def setup_ai_config() -> str:
    """Setup AI configuration and return instructions"""
    config_manager = get_config_manager()
    return config_manager.create_sample_config()