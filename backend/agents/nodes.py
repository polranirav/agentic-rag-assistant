"""
LangGraph Nodes: Router, Retrieval, and Synthesis.
Each node is a function that takes AgentState and returns modified AgentState.
"""

import logging
import time
from typing import Any, Dict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_pinecone import PineconeVectorStore

from .state import AgentState
import sys
from pathlib import Path
# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings

logger = logging.getLogger(__name__)

# Constants
SIMILARITY_THRESHOLD = settings.similarity_threshold
RETRIEVAL_K = settings.retrieval_k


def router_node(state: AgentState) -> Dict[str, Any]:
    """
    STEP 1: Intent Classification Node
    
    Analyzes the user query and determines the intent:
    - knowledge_search: Needs retrieval from knowledge base
    - calculation: Math, dates, conversions
    - api_lookup: Needs live data (weather, stocks, etc.)
    - greeting: Hello, how are you, etc.
    - unknown: Anything else
    
    This intelligent routing prevents unnecessary retrieval operations,
    reducing cost and latency.
    """
    
    start_time = time.time()
    user_query = state.get("user_query", "")
    
    try:
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert intent classifier for an AI assistant.
The assistant has access to a knowledge base containing AI research papers, technical documents, and policy information.

Analyze the user's query and classify it into ONE of these categories:

1. "knowledge_search": Questions about documents, research findings, policies, procedures, or any information that might be in the knowledge base. This includes requests to summarize, find key points, or explain concepts based on uploaded files.
   Examples: "What is the refund policy?", "Summarize the key findings of the AI papers", "Explain the transformer architecture from the research", "Tell me about health insurance"

2. "calculation": Math problems, date calculations, unit conversions, or computational tasks.
   Examples: "What is 25 * 47?", "How many days until Christmas?", "Convert 100 USD to EUR"

3. "api_lookup": Requires live/real-time data from external APIs.
   Examples: "What's the weather today?", "Current stock price of AAPL", "Latest news about AI"

4. "greeting": Casual conversation, greetings, or small talk.
   Examples: "Hello", "How are you?", "Thanks", "Goodbye"

5. "unknown": Anything that doesn't fit the above categories or is unclear.

Respond ONLY with valid JSON, no other text:
{{
    "intent": "<one of: knowledge_search, calculation, api_lookup, greeting, unknown>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation of why this intent was chosen>"
}}"""),
            ("human", "User Query: {query}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"query": user_query})
        
        intent = result.get("intent", "unknown")
        intent_confidence = float(result.get("confidence", 0.0))
        intent_reasoning = result.get("reasoning", "")
        reasoning = f"Intent classified as '{intent}' with {intent_confidence:.2%} confidence. {intent_reasoning}"
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(
            f"🎯 Router: Intent={intent}, Confidence={intent_confidence:.2f}, "
            f"Time={processing_time:.0f}ms"
        )
        
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "intent_reasoning": intent_reasoning,
            "reasoning": reasoning,
            "error": ""
        }
        
    except Exception as e:
        logger.error(f"❌ Router error: {e}", exc_info=True)
        return {
            "intent": "unknown",
            "intent_confidence": 0.0,
            "intent_reasoning": "",
            "reasoning": "",
            "error": f"Router classification failed: {str(e)}"
        }


def retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    STEP 2: Knowledge Base Retrieval Node
    
    Searches the Pinecone vector database for relevant context.
    Implements hallucination prevention by checking similarity scores.
    """
    
    start_time = time.time()
    user_query = state.get("user_query", "")
    
    try:
        # Initialize embeddings and vector store
        embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key
        )
        
        vector_store = PineconeVectorStore(
            index_name=settings.pinecone_index_name,
            embedding=embeddings,
            namespace="default"
        )
        
        # Perform similarity search
        logger.info(f"🔍 Searching knowledge base for: {user_query[:50]}...")
        
        results = vector_store.similarity_search_with_score(
            user_query,
            k=RETRIEVAL_K
        )
        
        # Extract results
        retrieved_context = [doc.page_content for doc, score in results]
        retrieval_scores = [float(score) for _, score in results]
        retrieval_metadata = [doc.metadata for doc, _ in results]
        
        # Set confidence score (best match)
        if retrieval_scores:
            # Convert distance to similarity (cosine distance -> similarity)
            # Pinecone cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: similarity = 1 - (distance / 2)
            best_score = retrieval_scores[0]
            confidence_score = max(0.0, 1.0 - (best_score / 2.0))
        else:
            confidence_score = 0.0
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"📚 Retrieved {len(retrieved_context)} chunks. "
            f"Best similarity: {confidence_score:.3f}, "
            f"Time={processing_time:.0f}ms"
        )
        
        # HALLUCINATION PREVENTION: Check similarity threshold
        if confidence_score < SIMILARITY_THRESHOLD:
            logger.warning(
                f"⚠️ Low confidence: {confidence_score:.3f} < {SIMILARITY_THRESHOLD}. "
                f"Declining to answer."
            )
            decline_reason = (
                f"Confidence score ({confidence_score:.2%}) is below threshold "
                f"({SIMILARITY_THRESHOLD:.2%}). The knowledge base doesn't contain "
                f"sufficiently relevant information to answer this query safely."
            )
            response = (
                "I don't have enough information in my knowledge base to answer that question "
                "with sufficient confidence. Please try rephrasing your question or contact "
                "support for assistance."
            )
            return {
                "retrieved_context": retrieved_context,
                "retrieval_scores": retrieval_scores,
                "retrieval_metadata": retrieval_metadata,
                "confidence_score": confidence_score,
                "should_decline": True,
                "decline_reason": decline_reason,
                "response": response
            }
        
        return {
            "retrieved_context": retrieved_context,
            "retrieval_scores": retrieval_scores,
            "retrieval_metadata": retrieval_metadata,
            "confidence_score": confidence_score,
            "should_decline": False,
            "decline_reason": "",
            "error": ""
        }
        
    except Exception as e:
        logger.error(f"❌ Retrieval error: {e}", exc_info=True)
        return {
            "retrieved_context": [],
            "retrieval_scores": [],
            "retrieval_metadata": [],
            "confidence_score": 0.0,
            "should_decline": True,
            "decline_reason": f"Error during retrieval: {str(e)}",
            "error": f"Retrieval failed: {str(e)}"
        }


def synthesis_node(state: AgentState) -> Dict[str, Any]:
    """
    STEP 3: Response Synthesis Node
    
    Generates the final response using retrieved context, calculations, or direct answers.
    Implements strict grounding to prevent hallucinations.
    """
    
    start_time = time.time()
    
    intent = state.get("intent", "unknown")
    user_query = state.get("user_query", "")
    retrieved_context = state.get("retrieved_context", [])
    should_decline = state.get("should_decline", False)
    calculation_result = state.get("calculation_result")
    error = state.get("error", "")
    
    try:
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key
        )
        
        if should_decline:
            # Already set response in retrieval node
            logger.info("⛔ Response declined due to low confidence")
            return {
                "response": state.get("response", "I cannot answer that question with sufficient confidence."),
                "citations": [],
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        if intent == "knowledge_search" and retrieved_context:
            # RAG: Answer from retrieved context
            context_text = "\n\n---\n\n".join([
                f"[Source {i+1}]\n{ctx}" 
                for i, ctx in enumerate(retrieved_context[:3])  # Use top 3
            ])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI assistant with access to a knowledge base of research papers and technical documents.

CRITICAL RULES:
1. Answer ONLY using the provided context below.
2. If the context doesn't contain enough information to answer, say so clearly.
3. Do NOT make up, invent, or assume any information not in the context.
4. If you're uncertain, acknowledge the uncertainty.
5. Always cite which source(s) you used (e.g., [Source 1]).
6. If the user asks for a summary, synthesize the most important points from all relevant sources.

Context from Knowledge Base:
{context}"""),
                ("human", "{query}")
            ])
            
            response = (prompt | llm).invoke({
                "query": user_query,
                "context": context_text
            })
            
            response_text = response.content
            
            # Extract citations
            retrieval_metadata = state.get("retrieval_metadata", [])
            retrieval_scores = state.get("retrieval_scores", [])
            citations = [
                {
                    "source": metadata.get("source", f"Document {i+1}"),
                    "content_preview": ctx[:150] + "..." if len(ctx) > 150 else ctx,
                    "similarity_score": f"{retrieval_scores[i]:.3f}",
                    "chunk_id": metadata.get("chunk_id", i)
                }
                for i, (ctx, metadata) in enumerate(
                    zip(retrieved_context[:3], retrieval_metadata[:3])
                )
            ]
            
            return {
                "response": response_text,
                "citations": citations,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        elif intent == "calculation" and calculation_result is not None:
            # Direct calculation result
            calculation_steps = state.get("calculation_steps", [])
            response_text = f"The result is: {calculation_result}"
            if calculation_steps:
                response_text += f"\n\nCalculation steps:\n" + "\n".join(calculation_steps)
            
            return {
                "response": response_text,
                "citations": [],
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        elif intent == "greeting":
            # Direct greeting response
            response_text = (
                "Hello! I'm your agentic AI assistant. I can help you with:\n"
                "- Answering questions from the knowledge base\n"
                "- Performing calculations\n"
                "- And more!\n\n"
                "What would you like to know?"
            )
            
            return {
                "response": response_text,
                "citations": [],
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        elif error:
            # Error response
            return {
                "response": f"I encountered an error: {error}. Please try again.",
                "citations": [],
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        else:
            # Unknown intent or no context
            response_text = (
                "I'm not sure how to help with that. Could you rephrase your question? "
                "I can answer questions about the knowledge base, perform calculations, "
                "or have a casual conversation."
            )
            
            return {
                "response": response_text,
                "citations": [],
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
    except Exception as e:
        logger.error(f"❌ Synthesis error: {e}", exc_info=True)
        return {
            "response": "I encountered an error generating a response. Please try again.",
            "citations": [],
            "error": f"Synthesis failed: {str(e)}",
            "processing_time_ms": (time.time() - start_time) * 1000
        }
