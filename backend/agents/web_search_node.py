"""
Web Search Node: Fallback when vector retrieval fails.
Uses DuckDuckGo (free) or Tavily (paid) for web search.
"""

import logging
from typing import Dict, Any, List

from .state import AgentState

# Import settings
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings

logger = logging.getLogger(__name__)


def web_search_node(state: AgentState) -> AgentState:
    """
    Web Search Fallback Node
    
    Triggered when:
    1. Vector retrieval returns no results
    2. Grader determines documents are not relevant
    3. Max iterations reached without good results
    
    Uses DuckDuckGo (free) as default, Tavily if API key provided.
    """
    
    import time
    start_time = time.time()
    
    user_query = state.get("user_query", "")
    rewritten_query = state.get("rewritten_query", "")
    
    # Use rewritten query if available
    search_query = rewritten_query if rewritten_query else user_query
    
    logger.info(f"🌐 WEB SEARCH NODE: Searching for '{search_query}'")
    
    web_results = []
    
    # Try Tavily first if API key is available
    tavily_key = getattr(settings, 'tavily_api_key', None)
    
    if tavily_key:
        try:
            web_results = _search_tavily(search_query, tavily_key)
            logger.info(f"🌐 Tavily returned {len(web_results)} results")
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}, falling back to DuckDuckGo")
    
    # Fallback to DuckDuckGo (free, no API key needed)
    if not web_results:
        try:
            web_results = _search_duckduckgo(search_query)
            logger.info(f"🌐 DuckDuckGo returned {len(web_results)} results")
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
    
    processing_time = (time.time() - start_time) * 1000
    
    # Format results for context
    formatted_results = []
    for result in web_results[:5]:  # Limit to top 5
        formatted_results.append({
            "title": result.get("title", ""),
            "snippet": result.get("snippet", result.get("body", "")),
            "url": result.get("url", result.get("href", "")),
            "source": "web_search"
        })
    
    # Add web results to context
    web_context = [
        f"[Web Source: {r['title']}]\n{r['snippet']}\nURL: {r['url']}"
        for r in formatted_results
    ]
    
    return {
        **state,
        "web_search_results": formatted_results,
        "web_search_used": True,
        "retrieved_context": state.get("retrieved_context", []) + web_context,
        "reasoning": state.get("reasoning", "") + f"\n[Web Search] Found {len(formatted_results)} web results to supplement knowledge base.",
    }


def _search_tavily(query: str, api_key: str) -> List[Dict[str, Any]]:
    """Search using Tavily API (paid, high quality)."""
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5
        )
        
        return response.get("results", [])
    except ImportError:
        logger.warning("Tavily not installed. Install with: pip install tavily-python")
        return []


def _search_duckduckgo(query: str) -> List[Dict[str, Any]]:
    """Search using DuckDuckGo (free, no API key)."""
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        
        return results
    except ImportError:
        logger.warning("DuckDuckGo search not installed. Install with: pip install duckduckgo-search")
        return []
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return []


def should_use_web_search(state: AgentState) -> bool:
    """
    Utility function to determine if web search should be triggered.
    
    Returns True if:
    - No documents retrieved
    - Documents graded as not relevant
    - Confidence score below threshold
    - Max iterations not exceeded
    """
    
    retrieval_grade = state.get("retrieval_grade", "")
    retrieved_context = state.get("retrieved_context", [])
    confidence_score = state.get("confidence_score", 1.0)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    web_search_used = state.get("web_search_used", False)
    
    # Don't use web search if already used
    if web_search_used:
        return False
    
    # Don't exceed max iterations
    if iteration_count >= max_iterations:
        return False
    
    # Trigger web search conditions
    if not retrieved_context:
        return True
    
    if retrieval_grade == "not_relevant":
        return True
    
    if confidence_score < 0.3:
        return True
    
    return False
