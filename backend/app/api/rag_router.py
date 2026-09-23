from fastapi import APIRouter, Depends, HTTPException, status
from app.db.models import User
from app.core.security import get_current_user
from app.schemas.rag_schemas import RAGQueryRequest, RAGQueryResponse, IngestResponse
from app.services.rag_services import query_rag_pipeline, ingest_documents_from_directory

# Initialize APIRouter with prefix and OpenAPI tags
rag_router = APIRouter(prefix="/rag", tags=["RAG Assistant"])


@rag_router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
def trigger_document_ingestion(current_user: User = Depends(get_current_user)):
    """
    Triggers ingestion of text/markdown financial filings in the ./docs directory into ChromaDB.
    Protected endpoint requiring JWT authentication.
    """
    try:
        # Updated directory path to point to './docs'
        chunks = ingest_documents_from_directory("./docs")
        return {"status": "success", "chunks_ingested": chunks}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest documents: {str(e)}"
        )


@rag_router.post("/query", response_model=RAGQueryResponse, status_code=status.HTTP_200_OK)
def query_financial_rag(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Query financial filings and earnings notes stored in ChromaDB using Gemini AI.
    Protected endpoint requiring JWT authentication.
    """
    try:
        rag_result = query_rag_pipeline(
            query=request.query,
            ticker=request.ticker,
            top_k=request.top_k
        )
        return rag_result
    except ValueError as ve:
        # Catch configuration or key-related errors cleanly (HTTP 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        # Catch unexpected pipeline runtime errors (HTTP 500)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG execution error: {str(e)}"
        )