"""
Evaluation Pipeline: RAGAS Metrics + LLM-as-Judge

Evaluates the RAG system on test queries and computes metrics.
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

from agents.state import AgentState
from agents.graph import build_agent_graph
from core.config import settings

load_dotenv()


def evaluate_faithfulness(
    response: str,
    context: List[str],
    model: str = "gpt-4o"
) -> Dict:
    """
    LLM-as-Judge: Is the response faithful to the context?
    
    This prevents hallucinations by validating that all claims in the response
    are grounded in the retrieved context.
    """
    
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=settings.openai_api_key
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert evaluator of AI responses.

Evaluate if the RESPONSE is faithful to the CONTEXT provided.

A faithful response:
- All facts and claims are directly supported by the context
- No invented or assumed information
- No meaning distortion or exaggeration
- If context is insufficient, response acknowledges this

An unfaithful response:
- Contains claims not in the context
- Makes assumptions beyond what context supports
- Distorts or exaggerates information from context

Return ONLY valid JSON, no other text:
{{
    "is_faithful": <true/false>,
    "score": <0.0 to 1.0>,
    "hallucinated_claims": [<list of any invented claims>],
    "reasoning": "<explanation of your evaluation>"
}}"""),
        ("human", """CONTEXT:
{context}

RESPONSE:
{response}

Evaluate faithfulness:""")
    ])
    
    try:
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "context": "\n\n---\n\n".join(context),
            "response": response
        })
        return result
    except Exception as e:
        return {
            "is_faithful": False,
            "score": 0.0,
            "error": str(e)
        }


def evaluate_answer_relevancy(
    query: str,
    response: str,
    model: str = "gpt-4o"
) -> Dict:
    """
    LLM-as-Judge: Is the response relevant to the query?
    """
    
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=settings.openai_api_key
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Evaluate if the RESPONSE is relevant to the QUERY.

A relevant response:
- Directly addresses the query
- Provides useful information related to the query
- Doesn't go off-topic

Return ONLY valid JSON:
{{
    "is_relevant": <true/false>,
    "score": <0.0 to 1.0>,
    "reasoning": "<explanation>"
}}"""),
        ("human", """QUERY: {query}

RESPONSE: {response}

Evaluate relevancy:""")
    ])
    
    try:
        chain = prompt | llm | JsonOutputParser()
        return chain.invoke({"query": query, "response": response})
    except Exception as e:
        return {
            "is_relevant": False,
            "score": 0.0,
            "error": str(e)
        }


def run_evaluation(test_queries: List[str]) -> Dict:
    """
    Run evaluation on all test queries and compute metrics.
    """
    
    print("\n" + "="*60)
    print("EVALUATING AGENTIC RAG SYSTEM")
    print("="*60 + "\n")
    
    graph = build_agent_graph()
    
    results = {
        "total": len(test_queries),
        "passed": 0,
        "hallucinations": 0,
        "low_relevancy": 0,
        "avg_confidence": 0.0,
        "avg_latency_ms": 0.0,
        "avg_faithfulness": 0.0,
        "avg_relevancy": 0.0,
        "details": []
    }
    
    confidences = []
    latencies = []
    faithfulness_scores = []
    relevancy_scores = []
    
    for i, query in enumerate(test_queries):
        print(f"\n📝 Test {i+1}/{len(test_queries)}: {query[:60]}...")
        print("-" * 60)
        
        start = time.time()
        
        # Run agent
        state = AgentState(user_query=query)
        result = graph.invoke(state)
        
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        confidences.append(result.confidence_score)
        
        # Evaluate faithfulness (if context retrieved)
        faithfulness_score = 1.0
        is_faithful = True
        
        if result.retrieved_context:
            faith_eval = evaluate_faithfulness(
                result.response,
                result.retrieved_context
            )
            is_faithful = faith_eval.get("is_faithful", False)
            faithfulness_score = faith_eval.get("score", 0.0)
            faithfulness_scores.append(faithfulness_score)
        
        # Evaluate relevancy
        relevancy_eval = evaluate_answer_relevancy(query, result.response)
        is_relevant = relevancy_eval.get("is_relevant", False)
        relevancy_score = relevancy_eval.get("score", 0.0)
        relevancy_scores.append(relevancy_score)
        
        # Determine if test passed
        passed = (
            is_faithful and
            is_relevant and
            result.confidence_score > settings.evaluation_threshold
        )
        
        if passed:
            results["passed"] += 1
        else:
            if not is_faithful:
                results["hallucinations"] += 1
            if not is_relevant:
                results["low_relevancy"] += 1
        
        # Store details
        results["details"].append({
            "query": query,
            "intent": result.intent,
            "confidence": result.confidence_score,
            "faithful": is_faithful,
            "faithfulness_score": faithfulness_score,
            "relevant": is_relevant,
            "relevancy_score": relevancy_score,
            "latency_ms": latency,
            "passed": passed
        })
        
        # Print result
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}")
        print(f"  Intent: {result.intent}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Faithfulness: {faithfulness_score:.2f}")
        print(f"  Relevancy: {relevancy_score:.2f}")
        print(f"  Latency: {latency:.0f}ms")
    
    # Calculate averages
    if confidences:
        results["avg_confidence"] = sum(confidences) / len(confidences)
    if latencies:
        results["avg_latency_ms"] = sum(latencies) / len(latencies)
    if faithfulness_scores:
        results["avg_faithfulness"] = sum(faithfulness_scores) / len(faithfulness_scores)
    if relevancy_scores:
        results["avg_relevancy"] = sum(relevancy_scores) / len(relevancy_scores)
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"✅ Passed: {results['passed']}/{results['total']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"❌ Hallucinations: {results['hallucinations']}/{results['total']}")
    print(f"⚠️  Low Relevancy: {results['low_relevancy']}/{results['total']}")
    print(f"📊 Avg Confidence: {results['avg_confidence']:.2f}")
    print(f"📊 Avg Faithfulness: {results['avg_faithfulness']:.2f}")
    print(f"📊 Avg Relevancy: {results['avg_relevancy']:.2f}")
    print(f"⏱️  Avg Latency: {results['avg_latency_ms']:.0f}ms")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    # Test queries (customize based on your knowledge base)
    test_queries = [
        "What is the refund policy?",
        "How do I request time off?",
        "Tell me about health insurance benefits",
        "What are the working hours?",
        "How can I contact HR?",
    ]
    
    # You can also load from a file
    # with open("test_queries.json", "r") as f:
    #     test_queries = json.load(f)
    
    results = run_evaluation(test_queries)
    
    # Save results
    output_file = Path(__file__).parent.parent.parent / "evaluation-results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"📄 Results saved to: {output_file}")
