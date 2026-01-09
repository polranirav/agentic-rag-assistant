/**
 * TypeScript type definitions for the application.
 */

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  intent?: string;
  confidence?: number;
  citations?: Citation[];
  reasoning?: string;
  processingTime?: number;
  timestamp: Date;
  // Corrective RAG fields
  retrievalGrade?: string;
  webSearchUsed?: boolean;
  iterationCount?: number;
}

export interface Citation {
  source: string;
  content_preview: string;
  similarity_score: string;
  chunk_id?: number;
}

export interface ChatRequest {
  query: string;
  user_id?: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  intent: string;
  confidence: number;
  citations: Citation[];
  reasoning: string;
  processing_time_ms: number;
  error?: string;
  // Corrective RAG fields
  retrieval_grade?: string;
  web_search_used?: boolean;
  iteration_count?: number;
}

export interface StreamEvent {
  type: 'metadata' | 'token' | 'citations' | 'done' | 'error' | 'step';
  content?: string;
  index?: number;
  total?: number;
  intent?: string;
  confidence?: number;
  reasoning?: string;
  processing_time_ms?: number;
  citations?: Citation[];
  message?: string;
  // Step event fields
  step?: string;
  label?: string;
  // Corrective RAG metadata
  retrieval_grade?: string;
  web_search_used?: boolean;
  iteration_count?: number;
}

