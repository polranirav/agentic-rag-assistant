"""
Grader Node: Evaluates retrieved document relevance.
Part of the Corrective RAG pattern - determines if documents answer the query.
"""

import logging
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .state import AgentState

# Import settings
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings

logger = logging.getLogger(__name__)


def grader_node(state: AgentState) -> AgentState:
    """
    STEP 2.5: Document Grader Node (Corrective RAG)
    
    Evaluates if retrieved documents are relevant to the query.
    If documents are NOT relevant, triggers query rewriting or web search.
    
    This is the "self-correction" capability that distinguishes
    Agentic RAG from naive RAG systems.
    """
    
    start_time = __import__('time').time()
    user_query = state.get("user_query", "")
    retrieved_context = state.get("retrieved_context", [])
    retrieval_scores = state.get("retrieval_scores", [])
    
    logger.info(f"📋 GRADER NODE: Evaluating {len(retrieved_context)} documents")
    
    # If no documents retrieved, mark as not relevant
    if not retrieved_context:
        logger.warning("No documents to grade - marking as not relevant")
        return {
            **state,
            "retrieval_grade": "not_relevant",
            "grade_reasoning": "No documents were retrieved from the knowledge base.",
            "should_rewrite": True,
        }
    
    # Check similarity scores first (fast path)
    avg_score = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0
    if avg_score < settings.similarity_threshold:
        logger.info(f"Low similarity score ({avg_score:.3f}) - documents likely not relevant")
        return {
            **state,
            "retrieval_grade": "not_relevant",
            "grade_reasoning": f"Retrieved documents have low similarity scores (avg: {avg_score:.3f}). Query may need rewriting.",
            "should_rewrite": True,
        }
    
    # Use LLM to grade document relevance
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",  # Use smaller model for grading (cost optimization)
            temperature=0,
            api_key=settings.openai_api_key
        )
        
        grading_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a grader assessing relevance of retrieved documents to a user question.

Your task: Determine if the documents contain information that can answer the user's question.

Rules:
- If documents contain relevant information (even partial), answer "relevant"
- If documents are completely off-topic or don't help answer the question, answer "not_relevant"
- Be lenient - if there's any useful information, mark as relevant

Respond with ONLY one word: "relevant" or "not_relevant"
"""),
            ("human", """User Question: {question}

Retrieved Documents:
{documents}

Grade (relevant/not_relevant):""")
        ])
        
        # Combine documents for grading
        docs_text = "\n\n---\n\n".join(retrieved_context[:3])  # Grade top 3 docs
        
        chain = grading_prompt | llm | StrOutputParser()
        grade = chain.invoke({
            "question": user_query,
            "documents": docs_text
        }).strip().lower()
        
        is_relevant = "relevant" in grade and "not_relevant" not in grade
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"📋 Grade: {'✅ RELEVANT' if is_relevant else '❌ NOT RELEVANT'}")
        
        return {
            **state,
            "retrieval_grade": "relevant" if is_relevant else "not_relevant",
            "grade_reasoning": f"LLM grader determined documents are {'relevant' if is_relevant else 'not relevant'} to the query.",
            "should_rewrite": not is_relevant,
        }
        
    except Exception as e:
        logger.error(f"Grading failed: {e}")
        # On error, assume relevant to avoid blocking (fail-open)
        return {
            **state,
            "retrieval_grade": "relevant",
            "grade_reasoning": f"Grading error (defaulting to relevant): {str(e)}",
            "should_rewrite": False,
        }


def rewrite_query_node(state: AgentState) -> AgentState:
    """
    Query Rewriter Node: Transforms the original query for better retrieval.
    
    Triggered when the grader determines documents are not relevant.
    Uses LLM to rephrase the query to improve retrieval results.
    """
    
    import time
    start_time = time.time()
    
    user_query = state.get("user_query", "")
    rewritten_query = state.get("rewritten_query", "")
    iteration_count = state.get("iteration_count", 0)
    
    # Use rewritten query if this is a retry
    current_query = rewritten_query if rewritten_query else user_query
    
    logger.info(f"🔄 REWRITE NODE: Transforming query (iteration {iteration_count + 1})")
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,  # Slight creativity for rephrasing
            api_key=settings.openai_api_key
        )
        
        rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query rewriter for a RAG system.

Your task: Rewrite the user's question to improve document retrieval.

Strategies:
1. Add relevant keywords that might appear in documents
2. Make implicit concepts explicit
3. Rephrase ambiguous terms
4. Break down complex questions
5. Use alternative phrasings

Output ONLY the rewritten query, nothing else."""),
            ("human", """Original Query: {query}

Rewritten Query:""")
        ])
        
        chain = rewrite_prompt | llm | StrOutputParser()
        new_query = chain.invoke({"query": current_query}).strip()
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"🔄 Rewritten: '{current_query}' → '{new_query}'")
        
        return {
            **state,
            "rewritten_query": new_query,
            "iteration_count": iteration_count + 1,
            "reasoning": state.get("reasoning", "") + f"\n[Rewriter] Query transformed for better retrieval.",
        }
        
    except Exception as e:
        logger.error(f"Query rewriting failed: {e}")
        return {
            **state,
            "rewritten_query": current_query,  # Keep original on error
            "iteration_count": iteration_count + 1,
            "error": str(e),
        }
