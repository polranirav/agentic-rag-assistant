import React, { useState, useEffect } from 'react';
import { getDashboardStats, compareResumes, getCareerInsights } from '../utils/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, LineChart, Line } from 'recharts';
import { TrendingUp, Users, Award, Target, Zap, Brain } from 'lucide-react';
import '../styles/dashboard.css';
import '../styles/futuristic-dashboard.css';

interface ResumeStats {
  totalResumes: number;
  totalSkills: number;
  avgExperience: number;
  topSkills: { name: string; count: number }[];
  skillDistribution: { category: string; value: number }[];
  experienceTimeline: { year: string; value: number }[];
}

export const ResumeDashboard: React.FC = () => {
  const [stats, setStats] = useState<ResumeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'skills' | 'comparison' | 'insights'>('overview');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch from backend API
      const data = await getDashboardStats();
      const stats: ResumeStats = {
        totalResumes: data.total_resumes,
        totalSkills: data.total_skills,
        avgExperience: data.avg_experience_years,
        topSkills: data.top_skills.map((s: any) => ({ name: s.name, count: s.count })),
        skillDistribution: Object.entries(data.skill_distribution).map(([category, value]) => ({
          category,
          value: value as number,
        })),
        experienceTimeline: data.experience_timeline,
      };
      setStats(stats);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="futuristic-loading">
        <div className="futuristic-spinner"></div>
        <p>Loading Dashboard Analytics...</p>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="futuristic-dashboard">
      <div className="futuristic-dashboard-header">
        <h1>📊 Resume Intelligence Dashboard</h1>
        <p>Advanced Analytics & Insights Across All Resumes</p>
      </div>

      <div className="futuristic-dashboard-tabs">
        <button
          className={`futuristic-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Target size={18} /> Overview
        </button>
        <button
          className={`futuristic-btn ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          <Brain size={18} /> Skills Analysis
        </button>
        <button
          className={`futuristic-btn ${activeTab === 'comparison' ? 'active' : ''}`}
          onClick={() => setActiveTab('comparison')}
        >
          <Users size={18} /> Comparison
        </button>
        <button
          className={`futuristic-btn ${activeTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveTab('insights')}
        >
          <Zap size={18} /> AI Insights
        </button>
      </div>

      {activeTab === 'overview' && (
        <div>
          <div className="futuristic-stats-grid">
            <div className="futuristic-stat-card">
              <div className="futuristic-stat-icon">
                <Users size={28} />
              </div>
              <div className="futuristic-stat-value">{stats.totalResumes}</div>
              <div className="futuristic-stat-label">Resumes Analyzed</div>
            </div>
            <div className="futuristic-stat-card">
              <div className="futuristic-stat-icon">
                <Award size={28} />
              </div>
              <div className="futuristic-stat-value">{stats.totalSkills}</div>
              <div className="futuristic-stat-label">Unique Skills</div>
            </div>
            <div className="futuristic-stat-card">
              <div className="futuristic-stat-icon">
                <TrendingUp size={28} />
              </div>
              <div className="futuristic-stat-value">{stats.avgExperience}</div>
              <div className="futuristic-stat-label">Years Experience</div>
            </div>
            <div className="futuristic-stat-card">
              <div className="futuristic-stat-icon">
                <Zap size={28} />
              </div>
              <div className="futuristic-stat-value">95%</div>
              <div className="futuristic-stat-label">Skill Coverage</div>
            </div>
          </div>

          <div className="futuristic-chart-container">
            <h3>Experience Timeline</h3>
            <LineChart width={800} height={300} data={stats.experienceTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 240, 255, 0.2)" />
              <XAxis dataKey="year" stroke="#00f0ff" />
              <YAxis stroke="#00f0ff" />
              <Tooltip 
                contentStyle={{ 
                  background: 'rgba(10, 14, 39, 0.95)', 
                  border: '1px solid #00f0ff',
                  borderRadius: '8px',
                  color: '#00f0ff'
                }} 
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#00f0ff" 
                strokeWidth={3}
                dot={{ fill: '#b026ff', r: 6 }}
                activeDot={{ r: 8 }}
              />
            </LineChart>
          </div>
        </div>
      )}

      {activeTab === 'skills' && (
        <div>
          <div className="futuristic-chart-container">
            <h3>Top Skills Distribution</h3>
            <BarChart width={800} height={400} data={stats.topSkills}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 240, 255, 0.2)" />
              <XAxis dataKey="name" stroke="#00f0ff" />
              <YAxis stroke="#00f0ff" />
              <Tooltip 
                contentStyle={{ 
                  background: 'rgba(10, 14, 39, 0.95)', 
                  border: '1px solid #00f0ff',
                  borderRadius: '8px',
                  color: '#00f0ff'
                }} 
              />
              <Legend />
              <Bar dataKey="count" fill="url(#colorGradient)" />
              <defs>
                <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00f0ff" />
                  <stop offset="100%" stopColor="#b026ff" />
                </linearGradient>
              </defs>
            </BarChart>
          </div>

          <div className="futuristic-chart-container">
            <h3>Skill Radar Chart</h3>
            <RadarChart width={600} height={400} data={stats.skillDistribution}>
              <PolarGrid stroke="rgba(0, 240, 255, 0.3)" />
              <PolarAngleAxis dataKey="category" stroke="#00f0ff" />
              <PolarRadiusAxis stroke="#00f0ff" />
              <Radar 
                name="Skills" 
                dataKey="value" 
                stroke="#00f0ff" 
                fill="#b026ff" 
                fillOpacity={0.6}
                strokeWidth={2}
              />
            </RadarChart>
          </div>
        </div>
      )}

      {activeTab === 'comparison' && (
        <div>
          <div className="futuristic-comparison-grid">
            <div className="futuristic-comparison-card">
              <h3>AI Engineer Resume</h3>
              <div className="futuristic-skill-tags">
                <span className="futuristic-skill-tag">Python</span>
                <span className="futuristic-skill-tag">TensorFlow</span>
                <span className="futuristic-skill-tag">NLP</span>
                <span className="futuristic-skill-tag">Computer Vision</span>
              </div>
              <div className="futuristic-strength-meter">
                <div className="futuristic-strength-bar" style={{ width: '92%' }}></div>
              </div>
            </div>
            <div className="futuristic-comparison-card">
              <h3>Data Engineer Resume</h3>
              <div className="futuristic-skill-tags">
                <span className="futuristic-skill-tag">Spark</span>
                <span className="futuristic-skill-tag">Airflow</span>
                <span className="futuristic-skill-tag">Azure</span>
                <span className="futuristic-skill-tag">ETL</span>
              </div>
              <div className="futuristic-strength-meter">
                <div className="futuristic-strength-bar" style={{ width: '88%' }}></div>
              </div>
            </div>
            <div className="futuristic-comparison-card">
              <h3>Data Scientist Resume</h3>
              <div className="futuristic-skill-tags">
                <span className="futuristic-skill-tag">Statistics</span>
                <span className="futuristic-skill-tag">Pandas</span>
                <span className="futuristic-skill-tag">Scikit-learn</span>
                <span className="futuristic-skill-tag">SQL</span>
              </div>
              <div className="futuristic-strength-meter">
                <div className="futuristic-strength-bar" style={{ width: '90%' }}></div>
              </div>
            </div>
            <div className="futuristic-comparison-card">
              <h3>ML Engineer Resume</h3>
              <div className="futuristic-skill-tags">
                <span className="futuristic-skill-tag">PyTorch</span>
                <span className="futuristic-skill-tag">MLOps</span>
                <span className="futuristic-skill-tag">Docker</span>
                <span className="futuristic-skill-tag">Kubernetes</span>
              </div>
              <div className="futuristic-strength-meter">
                <div className="futuristic-strength-bar" style={{ width: '85%' }}></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'insights' && (
        <div>
          <div className="futuristic-insights-grid">
            <div className="futuristic-insight-card">
              <h3>🎯 Career Path Recommendation</h3>
              <p>Based on your skill profile, you're well-positioned for <strong>Senior ML Engineer</strong> or <strong>AI Solutions Architect</strong> roles.</p>
            </div>
            <div className="futuristic-insight-card">
              <h3>📈 Skill Gap Analysis</h3>
              <p>Consider strengthening: <strong>Kubernetes</strong>, <strong>GraphQL</strong>, and <strong>Real-time Systems</strong> for next-level roles.</p>
            </div>
            <div className="futuristic-insight-card">
              <h3>💡 Industry Trends</h3>
              <p>Your skills align with <strong>95%</strong> of current AI/ML job postings. Strong match for FAANG companies.</p>
            </div>
            <div className="futuristic-insight-card">
              <h3>🚀 Growth Potential</h3>
              <p>With your experience, you're in the <strong>top 15%</strong> of candidates. Focus on leadership skills for management roles.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
