from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Your Project Name"
    
    # Database configuration
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    
    # Add more settings as needed
    
    class Config:
        case_sensitive = True

settings = Settings() 