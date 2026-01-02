"""
Application Configuration
Uses pydantic-settings for environment variable loading
"""
import os
from typing import List
from pathlib import Path
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    
    # API
    api_title: str = "Leitor de Simulados API"
    api_description: str = "REST API for processing exam answer sheets with YOLO detection models"
    api_version: str = "2.0.0"
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Logging
    log_level: str = "INFO"
    
    # Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "/app/uploads"
    
    # Models
    models_path: str = "models"
    
    # Session
    session_timeout_hours: int = 24
    
    # Hardware
    yolo_device: str = "auto"  # "auto", "cpu", "cuda", "cuda:0", etc.
    
    # Paths
    project_root: Path = Path(__file__).parent.parent
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_v = v.upper()
        if upper_v not in valid_levels:
            return "INFO"
        return upper_v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
