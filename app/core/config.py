from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Your Project Name"
    
    # MongoDB configuration
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "rag_db"
    MONGODB_USERNAME: str = "underdogcrew33"
    MONGODB_PASSWORD: str = None
    MONGODB_HOST: str = "localhost"
    MONGODB_PORT: int = 27017
    MONGODB_CLUSTER: Optional[str] = None  # For Atlas cluster name
    MONGODB_COLLECTION_RAG_CONFIGS: str = "rag_configs"
    MONGODB_CLUSTER_URL: str = "mongodb+srv://underdogcrew33:RZX6hBaep7SnCc4l@underdog-crew.vwaoz.mongodb.net/?retryWrites=true&w=majority&appName=underdog-crew"
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
        env_file = "/Users/neelpatel/Desktop/UnderdogCrew/project-ai/.env"

settings = Settings() 