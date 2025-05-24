"""
Configuration module for PDF Watermark Remover.

This module centralizes all configuration parameters used by the application.
It provides a clean interface for accessing configuration values and defaults,
with support for loading configuration from files and environment variables.

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class WatermarkPattern:
    """
    Represents dimensions of a typical watermark image.
    
    Attributes:
        width: Width of the watermark image in pixels
        height: Height of the watermark image in pixels
    """
    width: int
    height: int


class Config:
    """
    Central configuration class for the application.
    
    This class centralizes all configuration parameters used by the application,
    making it easy to modify settings in one place. It supports loading configuration
    from YAML files and environment variables.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Version information
        "VERSION": "2.0.0",
        
        # Logging configuration
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "LOG_FILE": None,  # If set, log to this file
        
        # PDF processing settings
        "MAX_CONCURRENT_PAGES": 8,
        
        # Watermark detection
        "MIN_PATTERN_LENGTH": 30,   # Minimum length for a text pattern to be considered a watermark
        "PATTERN_SEARCH_WINDOW": 300,  # Maximum window size to search for text patterns
        
        # XRef strategy settings
        "WATERMARK_PATTERNS": [
            {"width": 2360, "height": 1640},
            {"width": 1640, "height": 2360}
        ],
        "XREF_PRODUCER_PATTERNS": ["Version"],  # Only "Version" in producer triggers XRef strategy
        
        # Text strategy settings
        "TEXT_PATTERN": b'(',  # Initial byte pattern to search for text watermarks
        "TEXT_PATTERN_LENGTH": 30,  # Length of substring to extract after pattern
        
        # File handling
        "ALLOWED_EXTENSIONS": ["pdf"],
        "MAX_FILE_SIZE": 50 * 1024 * 1024,  # 50 MB
        "TEMP_DIR": "data",
        
        # Server settings
        "SERVER_HOST": "0.0.0.0",
        "SERVER_PORT": 5566,
        "UPLOAD_ENDPOINT": "/upload",
        
        # CLI settings
        "DEFAULT_OUTPUT_SUFFIX": "_no_watermark",
        
        # Batch processing
        "BACKUP_ENABLED": False,
        "OVERWRITE_ENABLED": False,
        "RECURSIVE_ENABLED": False,
        "DEFAULT_PARALLEL_PROCESSES": 1,
    }
    
    # Configuration values that can be overridden by environment variables
    ENV_VARS = {
        "LOG_LEVEL": "PDF_WATERMARK_LOG_LEVEL",
        "LOG_FILE": "PDF_WATERMARK_LOG_FILE",
        "MAX_CONCURRENT_PAGES": "PDF_WATERMARK_MAX_CONCURRENT_PAGES",
        "TEMP_DIR": "PDF_WATERMARK_TEMP_DIR",
        "SERVER_HOST": "PDF_WATERMARK_SERVER_HOST",
        "SERVER_PORT": "PDF_WATERMARK_SERVER_PORT",
        "DEFAULT_PARALLEL_PROCESSES": "PDF_WATERMARK_PARALLEL_PROCESSES",
    }
    
    # Config instance (for singleton pattern)
    _instance = None
    
    # Configuration values
    _config = {}
    
    def __new__(cls, config_file: Optional[str] = None):
        """
        Create a new Config instance (singleton pattern).
        
        Args:
            config_file: Path to YAML configuration file (optional)
        
        Returns:
            Config: Config instance
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._init(config_file)
        return cls._instance
    
    def _init(self, config_file: Optional[str] = None):
        """
        Initialize the configuration.
        
        Args:
            config_file: Path to YAML configuration file (optional)
        """
        # Load default configuration
        self._config = self.DEFAULT_CONFIG.copy()
        
        # Load configuration from file
        if config_file:
            self._load_from_file(config_file)
        
        # Load configuration from environment variables
        self._load_from_env()
        
        # Convert patterns to WatermarkPattern objects
        self._config["WATERMARK_PATTERNS"] = [
            WatermarkPattern(**pattern) if isinstance(pattern, dict) else pattern
            for pattern in self._config["WATERMARK_PATTERNS"]
        ]
        
        # Log configuration
        logger.debug(f"Configuration loaded: {self._config}")
    
    def _load_from_file(self, config_file: str):
        """
        Load configuration from a YAML file.
        
        Args:
            config_file: Path to YAML configuration file
        """
        if not YAML_AVAILABLE:
            logger.warning("YAML support is not available. Install PyYAML to load configuration from files.")
            return
        
        try:
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f)
            
            if file_config and isinstance(file_config, dict):
                # Update configuration with values from file
                for key, value in file_config.items():
                    if key in self._config:
                        self._config[key] = value
                        logger.debug(f"Loaded configuration from file: {key}={value}")
                    else:
                        logger.warning(f"Unknown configuration key in file: {key}")
            
            logger.info(f"Loaded configuration from file: {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from file: {str(e)}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        for key, env_var in self.ENV_VARS.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert value to appropriate type
                if isinstance(self._config[key], int):
                    try:
                        value = int(value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {value}")
                        continue
                elif isinstance(self._config[key], float):
                    try:
                        value = float(value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {env_var}: {value}")
                        continue
                elif isinstance(self._config[key], bool):
                    value = value.lower() in ('true', 'yes', '1')
                
                # Update configuration
                self._config[key] = value
                logger.debug(f"Loaded configuration from environment: {key}={value}")
    
    def __getattr__(self, name):
        """
        Get a configuration value.
        
        Args:
            name: Configuration key
            
        Returns:
            Any: Configuration value
            
        Raises:
            AttributeError: If the configuration key is unknown
        """
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"Unknown configuration key: {name}")
    
    @classmethod
    def get_temp_dir(cls) -> str:
        """
        Get the temporary directory path, creating it if necessary.
        
        Returns:
            str: Path to temporary directory
        """
        temp_dir = cls().TEMP_DIR
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
    @classmethod
    def save_to_file(cls, filename: str):
        """
        Save the current configuration to a YAML file.
        
        Args:
            filename: Path to the output file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not YAML_AVAILABLE:
            logger.warning("YAML support is not available. Install PyYAML to save configuration to files.")
            return False
        
        try:
            # Convert WatermarkPattern objects to dictionaries
            config = cls()._config.copy()
            config["WATERMARK_PATTERNS"] = [
                {"width": pattern.width, "height": pattern.height}
                if isinstance(pattern, WatermarkPattern) else pattern
                for pattern in config["WATERMARK_PATTERNS"]
            ]
            
            # Remove binary data that can't be serialized to YAML
            if "TEXT_PATTERN" in config and isinstance(config["TEXT_PATTERN"], bytes):
                config["TEXT_PATTERN"] = config["TEXT_PATTERN"].decode("latin1")
            
            with open(filename, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Saved configuration to file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration to file: {str(e)}")
            return False
