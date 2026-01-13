import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { BarChart2, Zap, AlertTriangle } from 'lucide-react';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];

const AnalyticsDashboard = ({ exposureData, causationData }) => {
  if (!exposureData && !causationData) return null;

  // Prepare Share of Voice Data
  const sovData = exposureData?.share_of_voice 
    ? Object.entries(exposureData.share_of_voice).map(([name, value]) => ({ name, value: (value * 100).toFixed(1) }))
    : [];

  // Prepare Sentiment Data
  const sentimentData = exposureData?.sentiment
    ? Object.entries(exposureData.sentiment).map(([name, value]) => ({ name, value: value.toFixed(2) }))
    : [];

  return (
    <div className="space-y-8">
      {/* Level 2: Competitive Exposure */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-6">
          <BarChart2 className="text-indigo-600" />
          Competitive Intelligence
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Share of Voice */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Share of Voice</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sovData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    fill="#8884d8"
                    paddingAngle={5}
                    dataKey="value"
                    label
                  >
                    {sovData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Sentiment Analysis */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Sentiment Polarity (-1 to +1)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sentimentData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[-1, 1]} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Anomalies */}
        {exposureData?.anomalies?.length > 0 && (
          <div className="mt-6 bg-red-50 border border-red-100 rounded-xl p-6">
            <h3 className="text-red-800 font-bold flex items-center gap-2 mb-3">
              <AlertTriangle size={20} />
              Detected Anomalies
            </h3>
            <ul className="space-y-2">
              {exposureData.anomalies.map((a, i) => (
                <li key={i} className="text-red-700 text-sm bg-white bg-opacity-50 p-2 rounded">
                  <strong>{a.entity}</strong>: {a.details} at {new Date(a.timestamp).toLocaleString()}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Level 3: Cross-Channel Causation */}
      {causationData && (
        <div className="border-t border-gray-200 pt-8">
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-6">
            <Zap className="text-yellow-500" />
            Cross-Channel Causation
          </h2>
          
          <div className="bg-gradient-to-r from-indigo-900 to-purple-900 rounded-xl p-8 text-white shadow-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
              <div>
                <div className="text-indigo-300 text-sm font-semibold uppercase tracking-wider mb-1">Causation Flow</div>
                <div className="text-2xl font-bold">{causationData.explanation}</div>
              </div>
              <div>
                 <div className="text-indigo-300 text-sm font-semibold uppercase tracking-wider mb-1">Correlation Strength</div>
                 <div className="text-3xl font-extrabold text-green-400">{causationData.correlation_score}</div>
              </div>
              <div>
                 <div className="text-indigo-300 text-sm font-semibold uppercase tracking-wider mb-1">Estimated Lag</div>
                 <div className="text-3xl font-bold">{Math.abs(causationData.best_lag_hours)} Hours</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
