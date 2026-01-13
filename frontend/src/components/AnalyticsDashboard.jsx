import React from "react";
import ForceGraph2D from "react-force-graph-2d";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from "recharts";
import { BarChart2, Zap, AlertTriangle } from "lucide-react";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444"];

const AnalyticsDashboard = ({ exposureData, causationData }) => {
  if (!exposureData && !causationData) return null;

  const flowNodes = Array.isArray(causationData?.flow_graph?.nodes)
    ? causationData.flow_graph.nodes
    : [];
  const flowEdges = Array.isArray(causationData?.flow_graph?.edges)
    ? causationData.flow_graph.edges
    : [];
  const flowGraphData =
    flowNodes.length && flowEdges.length
      ? {
          nodes: flowNodes.map((n) => ({ id: n.id })),
          links: flowEdges.map((e) => ({
            source: e.from,
            target: e.to,
            label: `lag ${e.lag_hours}h | corr ${e.correlation}`,
            correlation: e.correlation,
            lag_hours: e.lag_hours,
          })),
        }
      : null;

  const companies =
    exposureData?.competitors && exposureData?.company
      ? [exposureData.company, ...(exposureData.competitors || [])]
      : [];

  // Share of voice per community -> stacked bar data
  const sovByCommunity = Array.isArray(exposureData?.share_of_voice)
    ? exposureData.share_of_voice.map((row) => {
        const out = { name: row.community_name || row.community_id };
        (companies.length ? companies : Object.keys(row.totals || {})).forEach(
          (c) => {
            out[c] =
              row.shares && row.shares[c] != null
                ? Number((row.shares[c] * 100).toFixed(1))
                : 0;
          }
        );
        return out;
      })
    : [];

  // Sentiment distribution -> bar data (avg)
  const sentimentAvgData = exposureData?.sentiment
    ? Object.entries(exposureData.sentiment).map(([name, obj]) => ({
        name,
        value: Number((obj.avg ?? 0).toFixed(2)),
      }))
    : [];

  // Sentiment buckets -> stacked bars
  const sentimentBucketsData = exposureData?.sentiment
    ? Object.entries(exposureData.sentiment).map(([name, obj]) => ({
        name,
        negative: obj?.buckets?.negative || 0,
        neutral: obj?.buckets?.neutral || 0,
        positive: obj?.buckets?.positive || 0,
      }))
    : [];

  const coMentionData = Array.isArray(exposureData?.co_mentions)
    ? exposureData.co_mentions
        .slice()
        .sort((a, b) => (b.count || 0) - (a.count || 0))
        .slice(0, 10)
        .map((x) => ({ name: `${x.a} + ${x.b}`, value: x.count }))
    : [];

  return (
    <div className="space-y-8">
      {/* Level 2: Competitive Exposure */}
      <div>
        {exposureData && (
          <h2 className="flex gap-2 items-center mb-6 text-2xl font-bold text-gray-900">
            <BarChart2 className="text-indigo-600" />
            Competitive Intelligence
          </h2>
        )}

        {exposureData && (
          <div className="grid grid-cols-1 gap-6">
            {/* Share of Voice per Subreddit */}
            <div className="p-6 bg-white rounded-xl border border-gray-200 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-700">
                Share of Voice by Subreddit (%)
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sovByCommunity}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Legend />
                    {(companies.length ? companies : []).map((c, idx) => (
                      <Bar
                        key={c}
                        dataKey={c}
                        stackId="a"
                        fill={COLORS[idx % COLORS.length]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {/* Sentiment Avg */}
              <div className="p-6 bg-white rounded-xl border border-gray-200 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold text-gray-700">
                  Sentiment Avg (-1 to +1)
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sentimentAvgData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis domain={[-1, 1]} />
                      <Tooltip />
                      <Bar
                        dataKey="value"
                        fill="#6366f1"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Sentiment Distribution */}
              <div className="p-6 bg-white rounded-xl border border-gray-200 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold text-gray-700">
                  Sentiment Distribution
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sentimentBucketsData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="negative" stackId="a" fill="#ef4444" />
                      <Bar dataKey="neutral" stackId="a" fill="#f59e0b" />
                      <Bar dataKey="positive" stackId="a" fill="#10b981" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Co-mentions */}
            <div className="p-6 bg-white rounded-xl border border-gray-200 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-700">
                Top Co-mentions
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={coMentionData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" width={180} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Anomalies */}
        {exposureData?.anomalies?.length > 0 && (
          <div className="p-6 mt-6 bg-red-50 rounded-xl border border-red-100">
            <h3 className="flex gap-2 items-center mb-3 font-bold text-red-800">
              <AlertTriangle size={20} />
              Detected Anomalies
            </h3>
            <ul className="space-y-2">
              {exposureData.anomalies.map((a, i) => (
                <li
                  key={i}
                  className="p-2 text-sm text-red-700 bg-white bg-opacity-50 rounded"
                >
                  <div className="flex gap-3 justify-between items-center">
                    <div className="font-semibold text-red-800">
                      {a.type === "sentiment_shift"
                        ? "Sentiment shift"
                        : a.type === "mention_spike"
                        ? "Mention spike"
                        : a.type || "Anomaly"}
                    </div>
                    <div className="text-xs text-red-600 whitespace-nowrap">
                      {new Date(a.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <div className="mt-1">
                    <strong>{a.entity}</strong>: {a.details}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Level 3: Cross-Channel Causation */}
      {causationData && (
        <div className="pt-8 border-t border-gray-200">
          <h2 className="flex gap-2 items-center mb-6 text-2xl font-bold text-gray-900">
            <Zap className="text-yellow-500" />
            Cross-Channel Causation
          </h2>

          <div className="p-8 text-white bg-gradient-to-r from-indigo-900 to-purple-900 rounded-xl shadow-lg">
            <div className="grid grid-cols-1 gap-8 text-center md:grid-cols-3">
              <div>
                <div className="mb-1 text-sm font-semibold tracking-wider text-indigo-300 uppercase">
                  Causation Flow
                </div>
                <div className="text-2xl font-bold">
                  {causationData.explanation}
                </div>
              </div>
              <div>
                <div className="mb-1 text-sm font-semibold tracking-wider text-indigo-300 uppercase">
                  Correlation Strength
                </div>
                <div className="text-3xl font-extrabold text-green-400">
                  {causationData.correlation_score}
                </div>
              </div>
              <div>
                <div className="mb-1 text-sm font-semibold tracking-wider text-indigo-300 uppercase">
                  Estimated Lag
                </div>
                <div className="text-3xl font-bold">
                  {Math.abs(causationData.best_lag_hours)} Hours
                </div>
              </div>
            </div>
          </div>

          {flowGraphData && (
            <div className="grid grid-cols-1 gap-6 mt-6 lg:grid-cols-3">
              <div className="p-4 bg-white rounded-xl border border-gray-200 shadow-sm lg:col-span-2">
                <div className="mb-2 text-lg font-semibold text-gray-800">
                  Influence Flow Graph
                </div>
                <div className="mb-3 text-sm text-gray-500">
                  Directed edge means{" "}
                  <span className="font-semibold">lead</span> →{" "}
                  <span className="font-semibold">follow</span>.
                </div>
                <div className="h-[380px] bg-gray-900 rounded-lg overflow-hidden">
                  <ForceGraph2D
                    graphData={flowGraphData}
                    backgroundColor="#111827"
                    nodeLabel="id"
                    nodeColor={() => "#f59e0b"}
                    nodeRelSize={8}
                    linkDirectionalArrowLength={4}
                    linkDirectionalArrowRelPos={1}
                    linkColor={() => "rgba(255,255,255,0.2)"}
                    linkWidth={2}
                    linkLabel={(l) => l.label}
                    nodeCanvasObject={(node, ctx) => {
                      const label = node.name || node.id;
                      // draw node
                      ctx.fillStyle = "#6366f1";
                      ctx.beginPath();
                      ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI);
                      ctx.fill();
                      // centered label
                      ctx.font = "2px Sans-Serif";
                      ctx.textAlign = "center";
                      ctx.textBaseline = "middle";
                      ctx.fillStyle = "rgba(255,255,255,0.9)";
                      ctx.fillText(label, node.x, node.y);
                    }}
                    linkCanvasObject={(link, ctx) => {
                      const start = link.source;
                      const end = link.target;
                      if (typeof start !== "object" || typeof end !== "object")
                        return;
                      const label = link.label;
                      const textPos = {
                        x: start.x + (end.x - start.x) / 2,
                        y: start.y + (end.y - start.y) / 2,
                      };
                      ctx.save();
                      ctx.font = "2px Sans-Serif";
                      ctx.fillStyle = "rgba(17, 24, 39, 0.8)";
                      const w = ctx.measureText(label).width + 8;
                      ctx.fillRect(textPos.x - w / 2, textPos.y - 8, w, 16);
                      ctx.textAlign = "center";
                      ctx.textBaseline = "middle";
                      ctx.fillStyle = "rgba(255,255,255,0.9)";
                      ctx.fillText(label, textPos.x, textPos.y);
                      ctx.restore();
                    }}
                    linkCanvasObjectMode={() => "after"}
                  />
                </div>
              </div>

              <div className="p-4 space-y-4 bg-white rounded-xl border border-gray-200 shadow-sm">
                <div>
                  <div className="text-lg font-semibold text-gray-800">
                    Prediction
                  </div>
                  <div className="text-sm text-gray-500">
                    Which channel is likely to discuss next.
                  </div>
                </div>

                {Array.isArray(causationData?.predictions) &&
                causationData.predictions.length > 0 ? (
                  <div className="space-y-3">
                    {causationData.predictions.map((p, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-indigo-50 rounded-lg border border-indigo-100"
                      >
                        <div className="text-xs font-semibold text-indigo-700 uppercase">
                          Next
                        </div>
                        <div className="text-xl font-bold text-indigo-900">
                          {p.next_channel}
                        </div>
                        <div className="mt-1 text-sm text-indigo-800">
                          From{" "}
                          <span className="font-semibold">
                            {p.from_channel}
                          </span>{" "}
                          · ETA{" "}
                          <span className="font-semibold">{p.eta_hours}h</span>
                        </div>
                        <div className="mt-1 text-xs text-indigo-700">
                          Confidence: {p.confidence}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm italic text-gray-500">
                    Not enough signal to predict next channel.
                  </div>
                )}

                <div className="pt-2 border-t border-gray-100">
                  <div className="text-lg font-semibold text-gray-800">
                    Validation
                  </div>
                  <div className="text-sm text-gray-500">
                    Backtest on last window of data.
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                    <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500">Edges</div>
                      <div className="text-lg font-bold text-gray-900">
                        {causationData?.validation?.edges_evaluated ?? 0}
                      </div>
                    </div>
                    <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500">Hit rate</div>
                      <div className="text-lg font-bold text-gray-900">
                        {causationData?.validation?.hit_rate ?? 0}
                      </div>
                    </div>
                    <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="text-xs text-gray-500">Avg corr</div>
                      <div className="text-lg font-bold text-gray-900">
                        {causationData?.validation?.avg_test_correlation ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
