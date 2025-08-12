from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class DataSourceType(str, Enum):
    """Enum for different types of data sources"""
    FILE = "file"
    WEBSITE = "website"
    RAW_TEXT = "raw_text"

class DataStatus(str, Enum):
    """Enum for data processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class CreateManageDataSchema(BaseModel):
    """Schema for creating a new data management request"""
    rag_id: str = Field(..., description="ID of the RAG configuration")
    files: Optional[List[str]] = Field(default=None, description="List of files to process")
    website_url: Optional[str] = Field(default=None, description="URL of the website to crawl")
    max_crawl_page: Optional[int] = Field(
        default=1,
        ge=1,
        description="Maximum number of pages to crawl"
    )
    max_crawl_depth: Optional[int] = Field(
        default=1,
        ge=1,
        description="Maximum depth for web crawling"
    )
    dynamic_wait: Optional[int] = Field(
        default=5,
        ge=0,
        description="Wait time in seconds for dynamic content loading"
    )
    raw_text: Optional[str] = Field(default=None, description="Raw text input for processing")

    class Config:
        from_attributes = True

class ManageDataResponse(BaseModel):
    """Schema for data management response"""
    id: str = Field(..., description="Unique identifier for the data management request")
    rag_id: str
    source_type: DataSourceType
    status: DataStatus = Field(default=DataStatus.PENDING)
    files: Optional[List[str]] = None
    website_url: Optional[str] = None
    max_crawl_page: Optional[int] = None
    max_crawl_depth: Optional[int] = None
    dynamic_wait: Optional[int] = None
    raw_text: Optional[str] = None
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True

class ManageDataListResponse(BaseModel):
    """Schema for listing multiple data management requests"""
    total: int
    items: List[ManageDataResponse]

    class Config:
        from_attributes = True

class UpdateManageDataSchema(BaseModel):
    """Schema for updating an existing data management request"""
    data_id: str = Field(..., description="ID of the data management request to update")
    rag_id: Optional[str] = Field(default=None, description="ID of the RAG configuration")
    files: Optional[List[str]] = Field(default=None, description="List of files to process")
    website_url: Optional[str] = Field(default=None, description="URL of the website to crawl")
    max_crawl_page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of pages to crawl"
    )
    max_crawl_depth: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum depth for web crawling"
    )
    dynamic_wait: Optional[int] = Field(
        default=None,
        ge=0,
        description="Wait time in seconds for dynamic content loading"
    )
    raw_text: Optional[str] = Field(default=None, description="Raw text input for processing")

    class Config:
        from_attributes = True 