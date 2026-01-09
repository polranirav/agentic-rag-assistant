"""
Configuration management for the Agentic RAG system.
Centralized settings with environment variable support.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", 
        env="OPENAI_EMBEDDING_MODEL"
    )
    
    # Pinecone Configuration
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(
        default="rag-knowledge-base", 
        env="PINECONE_INDEX_NAME"
    )
    
    # Application Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Frontend Configuration
    frontend_url: str = Field(default="http://localhost:5173", env="FRONTEND_URL")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        env="CORS_ORIGINS"
    )
    
    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    # Evaluation & Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    evaluation_threshold: float = Field(default=0.65, env="EVALUATION_THRESHOLD")
    
    # Retrieval Configuration
    similarity_threshold: float = Field(default=0.65, env="SIMILARITY_THRESHOLD")
    retrieval_k: int = Field(default=5, env="RETRIEVAL_K")
    chunk_size: int = Field(default=1500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=300, env="CHUNK_OVERLAP")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
