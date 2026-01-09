import React, { useState, useRef, useEffect } from 'react';
import { sendStreamingChatRequest } from '../utils/api';
import type { Message } from '../types';
import { AgentSteps, agentStepsStyles } from './AgentSteps';
import '../styles/simple.css';

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'initial',
      type: 'assistant',
      content: '👋 Hello! I\'m your AI Knowledge Assistant.\n\nI can answer questions about any documents you upload:\n• PDF files (reports, articles, books)\n• Text files (notes, documentation)\n• Markdown files (docs, READMEs)\n• And more...\n\n💡 How it works:\n1. Upload your documents using the "Documents" tab\n2. Click "Ingest All Documents" to process them\n3. Ask me anything about your documents!\n\nWhat would you like to know?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`session-${Date.now()}`);
  const [agentSteps, setAgentSteps] = useState<{ step: string; label: string; status: 'pending' | 'active' | 'complete' }[]>([]);
  const [currentStep, setCurrentStep] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (query: string) => {
    if (!query.trim() || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    // Reset agent steps
    setAgentSteps([]);
    setCurrentStep('');

    try {
      // Stream response
      let fullContent = '';
      for await (const event of sendStreamingChatRequest({
        query: query,
        user_id: 'demo-user',
        session_id: sessionId,
      })) {
        if (event.type === 'step' && event.step && event.label) {
          // Handle agent step event
          setAgentSteps((prev) => {
            const exists = prev.some(s => s.step === event.step);
            if (!exists) {
              return [...prev, { step: event.step!, label: event.label!, status: 'active' as const }];
            }
            return prev;
          });
          setCurrentStep(event.step);
        } else if (event.type === 'metadata') {
          // Mark all steps as complete when metadata arrives
          setAgentSteps((prev) => prev.map(s => ({ ...s, status: 'complete' as const })));
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                  ...msg,
                  intent: event.intent,
                  confidence: event.confidence,
                  reasoning: event.reasoning,
                  processingTime: event.processing_time_ms,
                  retrievalGrade: event.retrieval_grade,
                  webSearchUsed: event.web_search_used,
                  iterationCount: event.iteration_count,
                }
                : msg
            )
          );
        } else if (event.type === 'token' && event.content) {
          fullContent += event.content;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: fullContent }
                : msg
            )
          );
        } else if (event.type === 'citations' && event.citations) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, citations: event.citations }
                : msg
            )
          );
        } else if (event.type === 'error') {
          throw new Error(event.message || 'Unknown error');
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
              ...msg,
              content:
                '❌ Error: Could not connect to server. Is the backend running on http://localhost:8000?',
            }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="simple-chat">
      <div className="simple-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`simple-message ${msg.type}`}>
            <div className="simple-message-avatar">
              {msg.type === 'user' ? '👤' : '🤖'}
            </div>
            <div className="simple-message-content">
              {msg.type === 'assistant' && isLoading && msg.id === messages[messages.length - 1].id && (
                <div>
                  {agentSteps.length > 0 && (
                    <AgentSteps steps={agentSteps} currentStep={currentStep} />
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <div className="simple-spinner"></div>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Processing...</span>
                  </div>
                  <style>{agentStepsStyles}</style>
                </div>
              )}
              <div className="simple-message-text">
                {msg.content.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    {i < msg.content.split('\n').length - 1 && <br />}
                  </React.Fragment>
                ))}
              </div>

              {msg.type === 'assistant' && (
                <div>
                  {msg.intent && (
                    <div className="simple-badge">
                      <span>🎯</span>
                      <span>Intent: {msg.intent.replace('_', ' ')}</span>
                      {msg.confidence !== undefined && (
                        <span> ({(msg.confidence * 100).toFixed(0)}%)</span>
                      )}
                    </div>
                  )}

                  {msg.citations && msg.citations.length > 0 && (
                    <div className="simple-citations">
                      <div style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 600 }}>
                        📚 Sources ({msg.citations.length})
                      </div>
                      {msg.citations.map((cite, i) => (
                        <div key={i} className="simple-citation">
                          <div className="simple-citation-source">{cite.source}</div>
                          <div className="simple-citation-preview">{cite.content_preview}</div>
                          <div className="simple-citation-score">Similarity: {cite.similarity_score}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {msg.processingTime && (
                    <div style={{ marginTop: '8px', color: 'var(--text-muted)', fontSize: '11px' }}>
                      ⏱️ {msg.processingTime.toFixed(0)}ms
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="simple-input-area">
        <div className="simple-input-wrapper">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything... (Shift+Enter for new line)"
            disabled={isLoading}
            rows={2}
            className="simple-input"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
            className="simple-send-btn"
            aria-label="Send message"
          >
            {isLoading ? (
              <>
                <div className="simple-spinner"></div>
                Sending...
              </>
            ) : (
              <>Send</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
