import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Tag, MessageSquare, Database } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const EntityBrowser = () => {
  const [entities, setEntities] = useState([]);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');

  // Fetch list on mount
  useEffect(() => {
    fetchEntities();
  }, []);

  const fetchEntities = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/v1/entities`);
      setEntities(res.data);
    } catch (err) {
      console.error("Failed to fetch entities", err);
    }
  };

  const handleEntityClick = async (entity) => {
    setSelectedEntity(entity);
    setDetails(null); // Clear previous
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/v1/entities/${entity.name}`);
      setDetails(res.data);
    } catch (err) {
      console.error("Failed to fetch entity details", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredEntities = entities.filter(e => 
    e.name.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex h-[600px] border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      {/* Sidebar List */}
      <div className="w-1/3 border-r border-gray-100 flex flex-col bg-gray-50">
        <div className="p-4 border-b border-gray-100 bg-white">
            <h3 className="font-bold text-gray-700 mb-2 flex items-center gap-2">
                <Database size={18} className="text-indigo-600"/> 
                Canonical Entities
            </h3>
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input 
                    type="text" 
                    placeholder="Search entities..." 
                    value={filter}
                    onChange={e => setFilter(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
            </div>
        </div>
        <div className="overflow-y-auto flex-grow">
            {filteredEntities.length === 0 ? (
                <div className="p-4 text-center text-gray-400 text-sm">No entities found.</div>
            ) : (
                filteredEntities.map((entity) => (
                    <button
                        key={entity.name}
                        onClick={() => handleEntityClick(entity)}
                        className={`w-full text-left px-4 py-3 border-b border-gray-100 text-sm hover:bg-indigo-50 transition-colors flex justify-between items-center group ${selectedEntity?.name === entity.name ? 'bg-indigo-50 border-l-4 border-l-indigo-600' : 'border-l-4 border-l-transparent'}`}
                    >
                        <span className="font-medium text-gray-700 group-hover:text-indigo-700">{entity.name}</span>
                        <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">{entity.label}</span>
                    </button>
                ))
            )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="w-2/3 flex flex-col h-full overflow-hidden">
        {selectedEntity ? (
            <div className="flex flex-col h-full">
                {/* Header */}
                <div className="p-6 border-b border-gray-100 bg-white">
                    <div className="flex items-center gap-3 mb-2">
                        <h2 className="text-2xl font-bold text-gray-900">{selectedEntity.name}</h2>
                        <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded uppercase">
                            {selectedEntity.label}
                        </span>
                    </div>
                    {details && (
                        <div className="flex flex-wrap gap-2 text-sm text-gray-600 mt-2">
                            <span className="font-semibold text-gray-400">Known Variations:</span>
                            {details.variations.map((v, i) => (
                                <span key={i} className="bg-gray-100 px-2 py-0.5 rounded border border-gray-200">
                                    {v}
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Mentions List */}
                <div className="flex-grow overflow-y-auto bg-gray-50 p-6">
                    <h3 className="font-bold text-gray-700 mb-4 flex items-center gap-2">
                        <MessageSquare size={18} />
                        Recent Mentions & Context
                    </h3>
                    
                    {loading ? (
                        <div className="flex justify-center py-10">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {details?.mentions?.length === 0 ? (
                                <div className="text-center text-gray-400 italic py-8">No recorded mentions yet.</div>
                            ) : (
                                details?.mentions?.map((mention) => (
                                    <div key={mention.id} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                                        <div className="mb-2 text-sm text-gray-500 flex justify-between">
                                            <span>Found as: <strong className="text-indigo-600">{mention.variation_used}</strong></span>
                                            <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded border border-green-100">
                                                {(mention.confidence * 100).toFixed(0)}% Confidence
                                            </span>
                                        </div>
                                        <div className="text-gray-800 leading-relaxed italic border-l-2 border-gray-200 pl-3">
                                            "{mention.context}"
                                        </div>
                                        <div className="mt-3 text-xs text-gray-400 text-right">
                                            {new Date(mention.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>
        ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 bg-gray-50">
                <Database size={48} className="mb-4 opacity-20" />
                <p>Select an entity to view details and mentions.</p>
            </div>
        )}
      </div>
    </div>
  );
};

export default EntityBrowser;
