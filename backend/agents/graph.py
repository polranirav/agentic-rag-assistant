"""
LangGraph State Machine Compilation - Corrective RAG Pattern.
Implements self-correcting retrieval with grading, query rewriting, and web search fallback.
"""

import logging
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import router_node, retrieval_node, synthesis_node
from .grader_node import grader_node, rewrite_query_node
from .web_search_node import web_search_node
from .graph_retrieval_node import graph_retrieval_node

logger = logging.getLogger(__name__)

# Maximum iterations to prevent infinite loops
MAX_ITERATIONS = 3


def build_agent_graph():
    """
    Build and compile the LangGraph state machine with Corrective RAG.
    
    Enhanced Workflow (Corrective RAG Pattern):
    ┌──────────────────────────────────────────────────────────────────┐
    │ START → ROUTER → [Intent Check] ─────────────────────────────────┤
    │    │                                                              │
    │    ├── greeting/calculation/unknown → SYNTHESIS → END            │
    │    │                                                              │
    │    └── knowledge_search → RETRIEVAL → GRADER → [Relevance Check] │
    │                              ↑            │                       │
    │                              │            ├── relevant → SYNTHESIS│
    │                              │            │                       │
    │                              │            └── not_relevant ───────┤
    │                              │                     │              │
    │                              │         ┌──────────┴──────────┐   │
    │                              │         │    Iteration < 3?   │   │
    │                              │         └──────────┬──────────┘   │
    │                              │                    │              │
    │                              └── REWRITE ←── yes ─┘              │
    │                                              no → WEB_SEARCH     │
    │                                                        │         │
    │                                                        └→ SYNTH  │
    └──────────────────────────────────────────────────────────────────┘
    """
    
    # Create graph with AgentState schema
    workflow = StateGraph(AgentState)
    
    # ==================== ADD NODES ====================
    workflow.add_node("router", router_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("graph_retrieval", graph_retrieval_node)  # GraphRAG enrichment
    workflow.add_node("grader", grader_node)
    workflow.add_node("rewrite", rewrite_query_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("synthesis", synthesis_node)
    
    # ==================== SET ENTRY POINT ====================
    workflow.set_entry_point("router")
    
    # ==================== ROUTING LOGIC ====================
    
    def route_after_classification(state: AgentState) -> str:
        """Route based on classified intent."""
        intent = state.get("intent", "unknown")
        
        if intent == "greeting":
            logger.info("→ Routing to synthesis (greeting)")
            return "synthesis"
        elif intent == "knowledge_search":
            logger.info("→ Routing to retrieval (knowledge_search)")
            return "retrieval"
        elif intent == "calculation":
            logger.info("→ Routing to synthesis (calculation)")
            return "synthesis"
        elif intent == "api_lookup":
            logger.info("→ Routing to synthesis (api_lookup)")
            return "synthesis"
        else:
            logger.info("→ Routing to synthesis (unknown)")
            return "synthesis"
    
    def route_after_grading(state: AgentState) -> str:
        """
        Route based on document grading result.
        This is the core of Corrective RAG - self-correction capability.
        """
        retrieval_grade = state.get("retrieval_grade", "relevant")
        iteration_count = state.get("iteration_count", 0)
        
        if retrieval_grade == "relevant":
            logger.info("→ Documents relevant, routing to synthesis")
            return "synthesis"
        
        # Not relevant - need corrective action
        if iteration_count < MAX_ITERATIONS:
            logger.info(f"→ Documents not relevant, rewriting query (iteration {iteration_count + 1})")
            return "rewrite"
        else:
            logger.info(f"→ Max iterations ({MAX_ITERATIONS}) reached, trying web search")
            return "web_search"
    
    def route_after_rewrite(state: AgentState) -> str:
        """Route after query rewriting - go back to retrieval."""
        logger.info("→ Query rewritten, retrying retrieval")
        return "retrieval"
    
    # ==================== ADD EDGES ====================
    
    # Router → [conditional]
    workflow.add_conditional_edges(
        "router",
        route_after_classification,
        {
            "synthesis": "synthesis",
            "retrieval": "retrieval"
        }
    )
    
    # Retrieval → Graph Retrieval → Grader
    workflow.add_edge("retrieval", "graph_retrieval")
    workflow.add_edge("graph_retrieval", "grader")
    
    # Grader → [conditional]
    workflow.add_conditional_edges(
        "grader",
        route_after_grading,
        {
            "synthesis": "synthesis",
            "rewrite": "rewrite",
            "web_search": "web_search"
        }
    )
    
    # Rewrite → Retrieval (loop back for retry)
    workflow.add_edge("rewrite", "retrieval")
    
    # Web Search → Synthesis
    workflow.add_edge("web_search", "synthesis")
    
    # Synthesis → END
    workflow.add_edge("synthesis", END)
    
    # ==================== COMPILE ====================
    graph = workflow.compile()
    
    logger.info("✅ LangGraph compiled successfully (Corrective RAG)")
    logger.info("   Nodes: router → retrieval → grader → [rewrite/web_search] → synthesis → END")
    
    return graph


# Test the graph (when run directly)
if __name__ == "__main__":
    import logging
    from dotenv import load_dotenv
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load environment variables
    load_dotenv()
    
    # Build and test graph
    graph = build_agent_graph()
    
    # Test query
    print("\n" + "="*60)
    print("TESTING CORRECTIVE RAG AGENT")
    print("="*60 + "\n")
    
    test_queries = [
        "What is the refund policy?",
        "Hello, how are you?",
        "What is 25 * 47?",
        "Tell me about quantum computing",  # Likely not in knowledge base
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 60)
        
        initial_state = {"user_query": query, "iteration_count": 0, "max_iterations": MAX_ITERATIONS}
        result = graph.invoke(initial_state)
        
        print(f"🎯 Intent: {result.get('intent', 'N/A')} (confidence: {result.get('intent_confidence', 0):.2f})")
        print(f"📋 Grade: {result.get('retrieval_grade', 'N/A')}")
        print(f"🔄 Iterations: {result.get('iteration_count', 0)}")
        print(f"🌐 Web Search Used: {result.get('web_search_used', False)}")
        print(f"📊 Confidence Score: {result.get('confidence_score', 0):.2f}")
        print(f"⏱️  Processing Time: {result.get('processing_time_ms', 0):.0f}ms")
        response = result.get('response', '')
        print(f"💬 Response: {response[:200]}..." if len(response) > 200 else f"💬 Response: {response}")
        print()
