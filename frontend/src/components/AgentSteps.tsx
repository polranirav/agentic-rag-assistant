import React from 'react';

interface AgentStep {
  step: string;
  label: string;
  status: 'pending' | 'active' | 'complete';
}

interface AgentStepsProps {
  steps: AgentStep[];
  currentStep: string;
}

const stepIcons: Record<string, string> = {
  router: '🎯',
  retrieval: '🔍',
  grader: '📋',
  rewrite: '🔄',
  web_search: '🌐',
  synthesis: '✨',
};

export const AgentSteps: React.FC<AgentStepsProps> = ({ steps, currentStep }) => {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="agent-steps">
      <div className="agent-steps-header">
        <span className="agent-steps-icon">⚙️</span>
        <span className="agent-steps-title">Agent Workflow</span>
      </div>
      <div className="agent-steps-list">
        {steps.map((step, index) => {
          const isActive = step.step === currentStep;
          const isComplete = steps.findIndex(s => s.step === currentStep) > index;
          
          return (
            <div
              key={step.step}
              className={`agent-step ${isActive ? 'active' : ''} ${isComplete ? 'complete' : ''}`}
            >
              <div className="agent-step-indicator">
                {isComplete ? (
                  <span className="agent-step-check">✓</span>
                ) : isActive ? (
                  <div className="agent-step-spinner"></div>
                ) : (
                  <span className="agent-step-number">{index + 1}</span>
                )}
              </div>
              <div className="agent-step-content">
                <span className="agent-step-icon">{stepIcons[step.step] || '•'}</span>
                <span className="agent-step-label">{step.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// CSS for agent steps (add to simple.css or include inline)
export const agentStepsStyles = `
.agent-steps {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
}

.agent-steps-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.agent-steps-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.agent-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-muted);
  transition: all 0.3s ease;
}

.agent-step.active {
  background: rgba(99, 102, 241, 0.2);
  color: var(--accent);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
}

.agent-step.complete {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.agent-step-indicator {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  font-size: 10px;
  font-weight: 600;
}

.agent-step.complete .agent-step-indicator {
  background: #22c55e;
  color: white;
}

.agent-step.active .agent-step-indicator {
  background: var(--accent);
}

.agent-step-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.agent-step-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.agent-step-icon {
  font-size: 14px;
}

.agent-step-label {
  font-size: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
`;
