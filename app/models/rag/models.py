from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class RAGConfig(BaseModel):
    """
    Configuration model for Retrieval-Augmented Generation (RAG) system.
    
    This class defines the necessary parameters and settings for setting up and
    running a RAG system, including vector store configurations, LLM settings,
    and retrieval parameters.
    
    Attributes:
        user_id (str): ID of the user who owns this configuration
        rag_name (str): Unique name for the RAG configuration
        vector_store (str): Name of the vector store service
        vector_store_url (HttpUrl): URL endpoint for the vector store
        vector_store_api_key (str): API key for vector store authentication
        llm_embedding_model (str): LLM model used for text embeddings
        llm_api_key (str): API key for LLM service
        top_k_similarity (int): Number of top similar documents to retrieve
    """
    
    user_id: str = Field(..., description="ID of the user who owns this configuration")
    rag_name: str = Field(..., description="Unique name for the RAG configuration")
    vector_store: str = Field(..., description="Name of the vector store service")
    vector_store_url: HttpUrl = Field(..., description="URL endpoint for the vector store")
    vector_store_api_key: str = Field(..., description="API key for vector store authentication")
    llm_embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="LLM model used for text embeddings"
    )
    llm_api_key: str = Field(..., description="API key for LLM service")
    top_k_similarity: int = Field(
        default=10,
        ge=1,
        description="Number of top similar documents to retrieve"
    )

    class Config:
        from_attributes = True

class CreateManageDataSchema(BaseModel):
    """
    Schema for managing data ingestion into RAG system.
    
    This class defines the parameters needed for ingesting data from various sources
    like files, websites, or raw text into the RAG system.
    
    Attributes:
        rag_id (str): ID of the RAG configuration
        files (Optional[list]): List of files to process
        website_url (Optional[str]): URL of the website to crawl
        max_crawl_page (Optional[int]): Maximum number of pages to crawl
        max_crawl_depth (Optional[int]): Maximum depth for web crawling
        dynamic_wait (Optional[int]): Wait time for dynamic content loading
        raw_text (Optional[str]): Raw text input for processing
    """
    rag_id: str = Field(..., description="ID of the RAG configuration")
    files: Optional[list] = Field(default=None, description="List of files to process")
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
