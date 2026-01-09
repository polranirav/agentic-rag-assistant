"""
Graph Retrieval Node: Combines vector search with graph traversal.
Implements hybrid retrieval for richer context.
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


def graph_retrieval_node(state: AgentState) -> AgentState:
    """
    Graph-Enhanced Retrieval Node
    
    Combines vector retrieval results with graph-based context:
    1. Takes entities mentioned in retrieved documents
    2. Queries Neo4j for related entities and relationships
    3. Enriches the context with graph information
    
    This provides richer context than pure vector search alone.
    """
    
    import time
    start_time = time.time()
    
    user_query = state.get("user_query", "")
    retrieved_context = state.get("retrieved_context", [])
    
    logger.info(f"🔗 GRAPH RETRIEVAL: Enriching context with graph data")
    
    # Try to get graph store
    try:
        from core.graph_store import get_graph_store
        graph_store = get_graph_store()
        
        if not graph_store.is_connected:
            logger.info("Graph store not connected, skipping graph enrichment")
            return state
        
        # Query for related entities based on the user query
        related_entities = graph_store.query_related_entities(user_query, limit=10)
        
        if related_entities:
            # Get rich context about these entities
            entity_names = [e["name"] for e in related_entities]
            graph_context = graph_store.get_entity_context(entity_names)
            
            if graph_context:
                # Prepend graph context to retrieved context
                enriched_context = [
                    f"[Graph Knowledge]\n{graph_context}",
                    *retrieved_context
                ]
                
                logger.info(f"🔗 Added graph context with {len(related_entities)} entities")
                
                processing_time = (time.time() - start_time) * 1000
                
                return {
                    **state,
                    "retrieved_context": enriched_context,
                    "graph_entities": related_entities,
                    "reasoning": state.get("reasoning", "") + f"\n[Graph] Found {len(related_entities)} related entities in knowledge graph.",
                }
        
        logger.info("No relevant graph entities found")
        return state
        
    except ImportError:
        logger.warning("Graph store not available")
        return state
    except Exception as e:
        logger.error(f"Graph retrieval error: {e}")
        return state


def should_use_graph_retrieval(state: AgentState) -> bool:
    """
    Determine if graph retrieval should be used.
    
    Returns True if:
    - Intent is knowledge_search
    - Graph store is available and connected
    """
    intent = state.get("intent", "")
    
    if intent != "knowledge_search":
        return False
    
    try:
        from core.graph_store import get_graph_store
        graph_store = get_graph_store()
        return graph_store.is_connected
    except:
        return False
