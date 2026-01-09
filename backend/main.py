"""
FastAPI Application: Agentic RAG Knowledge Assistant API

Provides RESTful API endpoints with streaming support for real-time responses.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agents.state import AgentState
from agents.graph import build_agent_graph
from core.config import settings
from api.analytics import router as analytics_router
from api.upload import router as upload_router

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agentic RAG Knowledge Assistant",
    version="2.0.0",
    description="Advanced AI-powered RAG system for document analysis and intelligent querying. Upload any documents (PDF, TXT, MD, etc.) and get intelligent answers.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
try:
    from api.analytics import router as analytics_router
    app.include_router(analytics_router)
    logger.info("✅ Analytics API loaded")
except Exception as e:
    logger.warning(f"Analytics API not available: {e}")

try:
    from api.upload import router as upload_router
    app.include_router(upload_router)
    logger.info("✅ Upload API loaded")
except Exception as e:
    logger.warning(f"Upload API not available: {e}")

# CORS middleware (allow frontend to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list() + ["*"],  # Allow all in dev, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load agent graph
try:
    graph = build_agent_graph()
    logger.info("✅ Agent graph loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load graph: {e}", exc_info=True)
    graph = None

# Metrics tracking
metrics = {
    "total_queries": 0,
    "successful_queries": 0,
    "failed_queries": 0,
    "avg_latency_ms": 0.0,
    "intent_distribution": {
        "knowledge_search": 0,
        "calculation": 0,
        "greeting": 0,
        "unknown": 0
    }
}


# ==================== REQUEST/RESPONSE MODELS ====================

class ChatRequest(BaseModel):
    """Incoming chat request."""
    query: str = Field(..., description="User query", min_length=1, max_length=2000)
    user_id: Optional[str] = Field(default="default", description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier for multi-turn conversations")


class ChatResponse(BaseModel):
    """Outgoing chat response."""
    response: str = Field(..., description="Generated response")
    intent: str = Field(..., description="Classified intent")
    confidence: float = Field(..., description="Confidence score (0-1)")
    citations: list = Field(default_factory=list, description="Source citations")
    reasoning: str = Field(default="", description="Agent reasoning")
    processing_time_ms: float = Field(default=0.0, description="Processing time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if any")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    agent_loaded: bool
    version: str = "1.0.0"


# ==================== ENDPOINTS ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agentic RAG Knowledge Assistant",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy" if graph is not None else "degraded",
        timestamp=datetime.now().isoformat(),
        agent_loaded=graph is not None
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Non-streaming chat endpoint.
    
    Returns complete response immediately after processing.
    Best for simple integrations or when streaming is not needed.
    """
    
    if not graph:
        raise HTTPException(status_code=503, detail="Agent not loaded. Please check server logs.")
    
    start = time.time()
    metrics["total_queries"] += 1
    
    try:
        # Create initial state with Corrective RAG fields
        state: AgentState = {
            "user_query": request.query,
            "user_id": request.user_id or "default",
            "session_id": request.session_id or f"session-{int(time.time())}",
            "intent": "",
            "intent_confidence": 0.0,
            "intent_reasoning": "",
            "retrieved_context": [],
            "retrieval_scores": [],
            "retrieval_metadata": [],
            "calculation_result": None,
            "calculation_steps": [],
            "response": "",
            "citations": [],
            "confidence_score": 0.0,
            "should_decline": False,
            "decline_reason": "",
            "reasoning": "",
            "error": "",
            "created_at": datetime.now().isoformat(),
            "processing_time_ms": 0.0,
            "conversation_history": [],
            # Corrective RAG fields
            "retrieval_grade": "",
            "grade_reasoning": "",
            "should_rewrite": False,
            "rewritten_query": "",
            "web_search_results": [],
            "web_search_used": False,
            "iteration_count": 0,
            "max_iterations": 3,
            "graph_entities": [],
            "graph_relationships": [],
        }
        
        # Run agent graph
        result = graph.invoke(state)
        
        # Update metrics
        latency = (time.time() - start) * 1000
        metrics["successful_queries"] += 1
        intent = result.get("intent", "unknown")
        metrics["intent_distribution"][intent] = metrics["intent_distribution"].get(intent, 0) + 1
        
        # Calculate average latency
        total = metrics["successful_queries"]
        metrics["avg_latency_ms"] = (
            (metrics["avg_latency_ms"] * (total - 1) + latency) / total
        )
        
        logger.info(
            f"✅ Query processed | Intent: {result.get('intent', 'unknown')} | "
            f"Confidence: {result.get('confidence_score', 0.0):.2f} | "
            f"Latency: {latency:.0f}ms"
        )
        
        return ChatResponse(
            response=result.get("response", ""),
            intent=result.get("intent", "unknown"),
            confidence=result.get("confidence_score", 0.0),
            citations=result.get("citations", []),
            reasoning=result.get("reasoning", ""),
            processing_time_ms=latency,
            error=result.get("error") if result.get("error") else None
        )
    
    except Exception as e:
        logger.error(f"❌ Chat error: {e}", exc_info=True)
        metrics["failed_queries"] += 1
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    
    Sends response token-by-token for real-time user experience.
    Similar to ChatGPT's streaming interface.
    """
    
    if not graph:
        raise HTTPException(status_code=503, detail="Agent not loaded")
    
    async def generate() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        start = time.time()
        metrics["total_queries"] += 1
        
        try:
            # Create initial state
            state: AgentState = {
                "user_query": request.query,
                "user_id": request.user_id or "default",
                "session_id": request.session_id or f"session-{int(time.time())}",
                "intent": "",
                "intent_confidence": 0.0,
                "intent_reasoning": "",
                "retrieved_context": [],
                "retrieval_scores": [],
                "retrieval_metadata": [],
                "calculation_result": None,
                "calculation_steps": [],
                "response": "",
                "citations": [],
                "confidence_score": 0.0,
                "should_decline": False,
                "decline_reason": "",
                "reasoning": "",
                "error": "",
                "created_at": datetime.now().isoformat(),
                "processing_time_ms": 0.0,
                "conversation_history": []
            }
            
            # Send agent step events for UX transparency
            steps = [
                {"step": "router", "label": "Classifying intent..."},
                {"step": "retrieval", "label": "Searching knowledge base..."},
                {"step": "grader", "label": "Evaluating document relevance..."},
                {"step": "synthesis", "label": "Generating response..."},
            ]
            
            for step_info in steps:
                step_event = {"type": "step", "step": step_info["step"], "label": step_info["label"]}
                yield f"data: {json.dumps(step_event)}\n\n"
                await asyncio.sleep(0.15)  # Brief delay for UX
            
            # Run agent graph
            result = graph.invoke(state)
            
            # Send metadata with Corrective RAG info
            metadata = {
                "type": "metadata",
                "intent": result.get("intent", "unknown"),
                "confidence": result.get("confidence_score", 0.0),
                "reasoning": result.get("reasoning", ""),
                "processing_time_ms": result.get("processing_time_ms", 0.0),
                "retrieval_grade": result.get("retrieval_grade", ""),
                "web_search_used": result.get("web_search_used", False),
                "iteration_count": result.get("iteration_count", 0),
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            await asyncio.sleep(0.01)
            
            # Stream response tokens (word-by-word for smooth UX)
            response_text = result.get("response", "")
            words = response_text.split()
            for i, word in enumerate(words):
                msg = {
                    "type": "token",
                    "content": word + (" " if i < len(words) - 1 else ""),
                    "index": i,
                    "total": len(words)
                }
                yield f"data: {json.dumps(msg)}\n\n"
                await asyncio.sleep(0.02)  # Simulate streaming delay
            
            # Send citations
            citations = result.get("citations", [])
            if citations:
                citations_msg = {
                    "type": "citations",
                    "citations": citations
                }
                yield f"data: {json.dumps(citations_msg)}\n\n"
            
            # Send completion
            completion = {
                "type": "done",
                "total_tokens": len(words)
            }
            yield f"data: {json.dumps(completion)}\n\n"
            
            # Update metrics
            latency = (time.time() - start) * 1000
            metrics["successful_queries"] += 1
            intent = result.get("intent", "unknown")
            metrics["intent_distribution"][intent] = metrics["intent_distribution"].get(intent, 0) + 1
            
            logger.info(
                f"✅ Stream completed | Intent: {intent} | "
                f"Latency: {latency:.0f}ms"
            )
        
        except Exception as e:
            logger.error(f"❌ Stream error: {e}", exc_info=True)
            metrics["failed_queries"] += 1
            error_msg = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_msg)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Return system metrics for monitoring.
    
    Useful for observability and performance tracking.
    """
    return {
        **metrics,
        "uptime_seconds": time.time(),  # Would track actual uptime in production
        "timestamp": datetime.now().isoformat()
    }


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("🚀 Starting Agentic RAG Knowledge Assistant API")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   API running on: http://{settings.api_host}:{settings.api_port}")
    
    # Initialize Phoenix tracing (if available)
    try:
        from core.tracing import initialize_tracing, get_phoenix_url
        if initialize_tracing(enable=True):
            phoenix_url = get_phoenix_url()
            if phoenix_url:
                logger.info(f"📊 Phoenix Dashboard: {phoenix_url}")
    except Exception as e:
        logger.warning(f"Phoenix tracing not available: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("🛑 Shutting down API")


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,  # Disable reload for direct execution
        log_level=settings.log_level.lower()
    )
