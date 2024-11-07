from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class RAGConfigCreate(BaseModel):
    """Schema for creating a new RAG configuration"""
    rag_name: str = Field(..., description="Unique name for the RAG configuration")
    vector_store: str = Field(..., description="Name of the vector store service")
    vector_store_url: str = Field(..., description="URL endpoint for the vector store")
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

class RAGConfigResponse(BaseModel):
    """Schema for RAG configuration response"""
    id: str = Field(..., description="Unique identifier for the RAG configuration")
    rag_name: str
    vector_store: str
    vector_store_url: str
    llm_embedding_model: str
    top_k_similarity: int
    created_at: str = Field(..., description="Timestamp when the configuration was created")

    class Config:
        from_attributes = True
