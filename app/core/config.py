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
    MONGODB_COLLECTION_AGENT_STUDIO: str = os.environ.get("MONGODB_COLLECTION_AGENT_STUDIO")
    MONGODB_COLLECTION_AGENT_CHAT: str = os.environ.get("MONGODB_COLLECTION_AGENT_CHAT")
    MONGODB_COLLECTION_RAG_LOGS: str = os.environ.get("MONGODB_COLLECTION_RAG_LOGS")
    # WhatsApp Settings
    WHATSAPP_ACCESS_TOKEN: str = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

    # Jwt Settings
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM")

    # AWS credentials
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_REGION: str = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_S3_BUCKET: str = os.environ.get("AWS_ACCESS_KEY_ID")

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
        env_file = ".env"


settings = Settings()
