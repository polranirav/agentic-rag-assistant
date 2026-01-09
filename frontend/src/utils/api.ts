/**
 * API utility functions for communicating with the backend.
 */

import axios from 'axios';
import type { ChatRequest, ChatResponse, StreamEvent } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Send a non-streaming chat request.
 */
export async function sendChatRequest(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat', request);
  return response.data;
}

/**
 * Send a streaming chat request.
 * Returns an async generator of stream events.
 */
export async function* sendStreamingChatRequest(
  request: ChatRequest
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: StreamEvent = JSON.parse(line.slice(6));
            yield event;
          } catch (e) {
            console.error('Failed to parse event:', e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<{ status: string; agent_loaded: boolean }> {
  const response = await api.get('/health');
  return response.data;
}

/**
 * Get dashboard statistics.
 */
export async function getDashboardStats() {
  const response = await api.get('/api/analytics/dashboard');
  return response.data;
}

/**
 * Compare resumes.
 */
export async function compareResumes(resumeIds: string[]) {
  const response = await api.post('/api/analytics/compare', { resume_ids: resumeIds });
  return response.data;
}

/**
 * Get career insights.
 */
export async function getCareerInsights() {
  const response = await api.post('/api/analytics/insights');
  return response.data;
}
