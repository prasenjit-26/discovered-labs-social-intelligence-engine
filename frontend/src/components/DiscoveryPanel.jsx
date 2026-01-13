import React from 'react';
import { Users, ExternalLink, TrendingUp, Activity } from 'lucide-react';

const DiscoveryPanel = ({ communities, loading, history, selectedCompany, companyPosts, onSelectCompany, onRefetchCompany }) => {
  if (loading) {
    return (
      <div className="py-12 text-center">
        <div className="mx-auto mb-4 w-12 h-12 rounded-full border-b-2 border-indigo-600 animate-spin"></div>
        <p className="text-gray-500">Scouting the social web...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="flex gap-2 items-center text-2xl font-bold text-gray-900">
            <Users className="text-indigo-600" />
            Discovered Communities
          </h2>
          {selectedCompany ? (
            <div className="mt-1 text-sm text-gray-500">Company: <span className="font-semibold text-gray-700">{selectedCompany}</span></div>
          ) : (
            <div className="mt-1 text-sm text-gray-500">Pick a previously fetched company or run a new analysis.</div>
          )}
        </div>

        <div className="flex gap-2">
          <select
            value={selectedCompany || ''}
            onChange={(e) => onSelectCompany && onSelectCompany(e.target.value)}
            className="px-3 py-2 text-sm bg-white rounded-lg border border-gray-200"
          >
            <option value="">Browse fetched companies...</option>
            {(history || []).map((h) => (
              <option key={h.company_domain} value={h.company_domain}>{h.company_domain}</option>
            ))}
          </select>

          <button
            onClick={() => onRefetchCompany && onRefetchCompany(selectedCompany)}
            disabled={!selectedCompany}
            className={`px-3 py-2 rounded-lg text-sm font-semibold border transition ${
              selectedCompany
                ? 'text-white bg-indigo-600 border-indigo-600 hover:bg-indigo-700'
                : 'text-gray-400 bg-gray-100 border-gray-200 cursor-not-allowed'
            }`}
          >
            Refetch
          </button>
        </div>
      </div>

      {(!communities || communities.length === 0) && (
        <div className="py-12 text-center text-gray-400">
          No communities loaded yet.
        </div>
      )}

      <div className="grid gap-4">
        {(communities || []).map((comm) => {
          const subscribers = comm.subscribers || 0
          const activeUsers = comm.active_users || 0
          const engagementPct = subscribers > 0 ? ((activeUsers / subscribers) * 100).toFixed(2) : '0.00'

          return (
            <div 
              key={comm.id} 
              className="p-6 bg-white rounded-xl border border-gray-200 shadow-sm transition-all duration-200 hover:shadow-md group"
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="text-lg font-bold text-gray-900 transition-colors group-hover:text-indigo-600">
                    {comm.name}
                  </h3>
                  <p className="mt-1 max-w-2xl text-sm text-gray-500 line-clamp-2">
                    {comm.description || "No description available."}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-indigo-600">{comm.relevance_score}</div>
                  <div className="text-xs font-semibold text-gray-400 uppercase">Value Score</div>
                </div>
              </div>
              
              <div className="flex gap-6 items-center pt-4 mt-4 text-sm text-gray-600 border-t border-gray-50">
                <div className="flex items-center gap-1.5">
                  <Users size={16} />
                  <span>{subscribers.toLocaleString()} subscribers</span>
                </div>
                {/* <div className="flex items-center gap-1.5">
                  <Activity size={16} />
                  <span>{activeUsers.toLocaleString()} active</span>
                </div> */}
                {/* <div className="flex items-center gap-1.5">
                  <TrendingUp size={16} />
                  <span>{engagementPct}% engagement</span>
                </div> */}
                <a 
                  href={comm.url} 
                  target="_blank" 
                  rel="noreferrer"
                  className="flex gap-1 items-center ml-auto font-medium text-indigo-600 hover:text-indigo-800"
                >
                  Visit <ExternalLink size={14} />
                </a>
              </div>
            </div>
          )
        })}
      </div>

      {selectedCompany && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-gray-900">Top Community Posts</h3>

          {(companyPosts || []).length === 0 && (
            <div className="py-8 text-center text-gray-400 bg-gray-50 rounded-xl border border-gray-200 border-dashed">
              No posts loaded yet.
            </div>
          )}

          <div className="grid gap-4">
            {(companyPosts || []).map((item) => {
              const community = item.community || {}
              const posts = item.posts || []

              return (
                <div key={community.id} className="p-4 bg-white rounded-xl border border-gray-200">
                  <div className="flex justify-between items-center">
                    <div className="font-bold text-gray-900">{community.name || community.id}</div>
                    {community.url && (
                      <a
                        href={community.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                      >
                        Open
                      </a>
                    )}
                  </div>

                  <div className="mt-3 space-y-3">
                    {posts.map((p) => (
                      <div key={p.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                        <div className="text-sm text-gray-800 whitespace-pre-wrap line-clamp-4">
                          {p.content}
                        </div>
                        <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
                          <div>Engagement: {Math.round(p.engagement_score || 0).toLocaleString()}</div>
                          {p.url && (
                            <a
                              href={p.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-indigo-600 hover:text-indigo-800"
                            >
                              View
                            </a>
                          )}
                        </div>
                      </div>
                    ))}

                    {posts.length === 0 && (
                      <div className="py-4 text-sm italic text-gray-400">No persisted posts for this community yet.</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default DiscoveryPanel;
