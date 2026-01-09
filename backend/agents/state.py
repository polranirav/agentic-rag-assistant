"""
Agent State Schema for LangGraph.
This defines the "working memory" that flows through the agent workflow.
"""

from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime


class AgentState(TypedDict, total=False):
    """
    State container for LangGraph agent workflow.
    
    This state object is passed between nodes and contains all information
    needed for the agent to make decisions and generate responses.
    """
    
    # ==================== INPUT ====================
    user_query: str  # Original user query
    
    # ==================== CLASSIFICATION (Router Output) ====================
    intent: str  # "knowledge_search", "calculation", "api_lookup", "greeting", "unknown"
    intent_confidence: float  # 0.0 to 1.0
    intent_reasoning: str  # Why this intent was chosen
    
    # ==================== RETRIEVAL (RAG Tool Output) ====================
    retrieved_context: List[str]  # Retrieved document chunks
    retrieval_scores: List[float]  # Similarity scores
    retrieval_metadata: List[Dict[str, Any]]  # Source metadata
    
    # ==================== CALCULATION (Calculator Tool Output) ====================
    calculation_result: Optional[Any]
    calculation_steps: List[str]
    
    # ==================== FINAL OUTPUT ====================
    response: str  # Final generated response
    citations: List[Dict[str, str]]  # Source citations
    
    # ==================== CONFIDENCE & SAFETY ====================
    confidence_score: float  # Overall confidence (0-1), used for hallucination prevention
    should_decline: bool  # Whether to decline answering (low confidence)
    decline_reason: str  # Reason for declining
    
    # ==================== METADATA ====================
    reasoning: str  # Agent's reasoning chain
    error: str  # Any errors encountered
    created_at: str
    processing_time_ms: float  # Time taken to process
    
    # ==================== CONVERSATION CONTEXT ====================
    conversation_history: List[Dict[str, str]]  # Multi-turn context
    session_id: Optional[str]
    user_id: Optional[str]
    
    # ==================== CORRECTIVE RAG (Grader & Rewriter) ====================
    retrieval_grade: str  # "relevant" or "not_relevant"
    grade_reasoning: str  # Why documents were graded this way
    should_rewrite: bool  # Whether to rewrite the query
    rewritten_query: str  # Transformed query for retry
    
    # ==================== WEB SEARCH FALLBACK ====================
    web_search_results: List[Dict[str, Any]]  # Results from web search
    web_search_used: bool  # Whether web search was triggered
    
    # ==================== LOOP PROTECTION ====================
    iteration_count: int  # Current iteration (max 3)
    max_iterations: int  # Maximum allowed iterations (default: 3)
    
    # ==================== GRAPH RAG (Future) ====================
    graph_entities: List[Dict[str, Any]]  # Entities from Neo4j
    graph_relationships: List[Dict[str, Any]]  # Relationships from graph traversal
