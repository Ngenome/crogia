"""Configuration management for the FastAPI backend"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # OpenAI Configuration
    openai_api_key: str = ""
    model_name: str = "o4-mini"
    
    # Agent Configuration
    base_directory: Path = Path.home() / "agent_workspaces"
    docker_base_image: str = "frdel/agent-zero-run:latest"
    
    # FastAPI Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # CORS Configuration
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Ensure base directory exists
settings.base_directory.mkdir(parents=True, exist_ok=True) 