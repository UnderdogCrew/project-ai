from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv
from os.path import join, dirname


env_path = join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")), '.env')
print("env_path: ", env_path)
load_dotenv(dotenv_path=env_path)



class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Underdog AI"
    # MongoDB configuration
    MONGODB_URL: str = os.environ.get("MONGODB_URL")
    MONGODB_DB_NAME: str = os.environ.get("MONGODB_DB_NAME")
    MONGODB_USERNAME: str = os.environ.get("MONGODB_USERNAME")
    MONGODB_PASSWORD: str = os.environ.get("MONGODB_PASSWORD")
    MONGODB_HOST: str = os.environ.get("MONGODB_HOST")
    MONGODB_PORT: int = os.environ.get("MONGODB_PORT")
    MONGODB_CLUSTER: Optional[str] = None  # For Atlas cluster name
    MONGODB_COLLECTION_RAG_CONFIGS: str = os.environ.get("MONGODB_COLLECTION_RAG_CONFIGS")
    MONGODB_CLUSTER_URL: str = os.environ.get("MONGODB_CLUSTER_URL")
    QDRANT_API_URL: str = os.environ.get("QDRANT_API_URL")
    QDRANT_API_KEY: str = os.environ.get("QDRANT_API_KEY")
    LLAMA_CLOUD_API_KEY: str = os.environ.get("LLAMA_CLOUD_API_KEY")
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")
    MONGODB_COLLECTION_DATA_MANAGEMENT: str = os.environ.get("MONGODB_COLLECTION_DATA_MANAGEMENT")

    # If you need to construct the full URL with authentication
    @property
    def mongodb_connection_string(self) -> str:
        if self.MONGODB_CLUSTER:  # Atlas connection
            return self.MONGODB_CLUSTER_URL
        elif self.MONGODB_USERNAME and self.MONGODB_PASSWORD:  # Standard auth connection
            return f"mongodb://{self.MONGODB_USERNAME}:{self.MONGODB_PASSWORD}@{self.MONGODB_HOST}:{self.MONGODB_PORT}"
        return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}"  # Local connection

    class Config:
        case_sensitive = True

settings = Settings() 