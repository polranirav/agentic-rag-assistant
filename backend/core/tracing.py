"""
Arize Phoenix Tracing Module.
Provides LLMOps observability for the Agentic RAG system.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global flag to track if tracing is initialized
_tracing_initialized = False


def initialize_tracing(enable: bool = True) -> bool:
    """
    Initialize Arize Phoenix tracing for LangChain/LangGraph.
    
    Phoenix provides:
    - Automatic trace capture for all LLM calls
    - Latency breakdown by node
    - Token usage tracking
    - Error analysis
    
    Returns True if tracing was successfully initialized.
    """
    global _tracing_initialized
    
    if not enable:
        logger.info("Phoenix tracing disabled")
        return False
    
    if _tracing_initialized:
        logger.info("Phoenix tracing already initialized")
        return True
    
    try:
        import phoenix as px
        from openinference.instrumentation.langchain import LangChainInstrumentor
        
        # Launch Phoenix in background
        # Note: In production, you'd connect to an external Phoenix server
        session = px.launch_app()
        
        # Instrument LangChain (which includes LangGraph)
        LangChainInstrumentor().instrument()
        
        _tracing_initialized = True
        logger.info(f"✅ Phoenix tracing initialized")
        logger.info(f"   Dashboard: {session.url}")
        
        return True
        
    except ImportError as e:
        logger.warning(f"Phoenix tracing not available: {e}")
        logger.warning("Install with: pip install arize-phoenix openinference-instrumentation-langchain")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Phoenix tracing: {e}")
        return False


def get_phoenix_url() -> Optional[str]:
    """Get the Phoenix dashboard URL if tracing is initialized."""
    if not _tracing_initialized:
        return None
    
    try:
        import phoenix as px
        return px.active_session().url if px.active_session() else None
    except:
        return None


def create_trace_context(query: str, session_id: str = None, user_id: str = None) -> dict:
    """
    Create context metadata for tracing a query.
    
    This metadata is attached to traces for filtering and analysis.
    """
    return {
        "query": query[:100],  # Truncate for logging
        "session_id": session_id or "default",
        "user_id": user_id or "anonymous",
        "timestamp": __import__('datetime').datetime.now().isoformat(),
    }


class TracingMiddleware:
    """
    Middleware for adding tracing context to FastAPI requests.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add trace context to request
            scope["trace_context"] = create_trace_context(
                query="",
                session_id=scope.get("session", {}).get("id"),
                user_id=scope.get("user", {}).get("id"),
            )
        
        await self.app(scope, receive, send)
