from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Financial query or question for the RAG assistant")
    ticker: str | None = Field(None, description="Optional stock ticker filter (e.g., AAPL, NVDA)")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of context chunks to retrieve")


class RetrievedContextChunk(BaseModel):
    content: str
    metadata: dict


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    retrieved_context: list[RetrievedContextChunk]


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int