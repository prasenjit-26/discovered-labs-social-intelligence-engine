import React, { useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Share2, Info, X } from 'lucide-react';
import axios from 'axios';

// API base URL helper
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const GraphView = ({ data }) => {
  const fgRef = useRef();
  const [dimensions, setDimensions] = useState({ w: 800, h: 600 });
  const containerRef = useRef(null);
  
  // State for selected entity details
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetails, setNodeDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    // Responsive graph
    if (containerRef.current) {
      setDimensions({
        w: containerRef.current.offsetWidth,
        h: 600
      });
    }
  }, []);

  const handleNodeClick = async (node) => {
    setSelectedNode(node);
    setLoadingDetails(true);
    setNodeDetails(null); // Clear previous details
    
    // Zoom to node
    if (fgRef.current) {
        fgRef.current.centerAt(node.x, node.y, 1000);
        fgRef.current.zoom(6, 2000);
    }

    try {
        const res = await axios.get(`${API_URL}/api/v1/graph/${node.id}`);
        setNodeDetails(res.data);
    } catch (err) {
        console.error("Failed to fetch entity details", err);
    } finally {
        setLoadingDetails(false);
    }
  };

  const closePanel = () => {
    setSelectedNode(null);
    setNodeDetails(null);
  };

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="text-center py-20 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
        <Share2 className="mx-auto h-12 w-12 text-gray-300 mb-4" />
        <p className="text-gray-500">No relationships mapped yet. Run discovery to build the graph.</p>
      </div>
    );
  }

  return (
    <div className="flex gap-4 h-[600px]">
      <div className="flex-grow flex flex-col space-y-4 h-full">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Share2 className="text-indigo-600" />
          Entity Knowledge Graph
        </h2>
        <div 
          ref={containerRef} 
          className="flex-grow border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-gray-900 relative"
        >
          <ForceGraph2D
            ref={fgRef}
            width={dimensions.w}
            height={dimensions.h}
            graphData={data}
            nodeLabel="id"
            nodeColor={() => "#6366f1"} // Indigo 500
            nodeVal={node => node.val || 1}
            linkColor={() => "rgba(255,255,255,0.2)"}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.25}
            backgroundColor="#111827" // Gray 900
            
            // Cool particle effects on links
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={d => 0.005}
            
            linkCanvasObject={(link, ctx, globalScale) => {
              const label = link.name;
              const start = link.source;
              const end = link.target;
              // ignore unbound links
              if (typeof start !== 'object' || typeof end !== 'object') return;

              // calculate label positioning
              const textPos = Object.assign(...['x', 'y'].map(c => ({
                [c]: start[c] + (end[c] - start[c]) / 2 // calc middle point
              })));

              const relLink = { x: end.x - start.x, y: end.y - start.y };

              const maxTextLength = Math.sqrt(Math.pow(relLink.x, 2) + Math.pow(relLink.y, 2)) - 8;

              let textAngle = Math.atan2(relLink.y, relLink.x);
              // maintain label vertical orientation for legibility 
              if (textAngle > Math.PI / 2) textAngle = -(Math.PI - textAngle);
              if (textAngle < -Math.PI / 2) textAngle = -(-Math.PI - textAngle);

              const fontSize = 4; // reduced font size for cleaner look
              ctx.font = `${fontSize}px Sans-Serif`;
              
              // Background for text
              const textWidth = ctx.measureText(label).width;
              const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

              ctx.save();
              ctx.translate(textPos.x, textPos.y);
              ctx.rotate(textAngle);

              ctx.fillStyle = 'rgba(17, 24, 39, 0.8)'; // Dark background matching theme
              ctx.fillRect(-bckgDimensions[0] / 2, -bckgDimensions[1] / 2, ...bckgDimensions);

              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
              ctx.fillText(label, 0, 0);
              ctx.restore();
            }}
            linkCanvasObjectMode={() => 'after'}

            onNodeClick={handleNodeClick}
          />
        </div>
        <p className="text-sm text-gray-500 italic">
          * Interactive: Zoom, pan, and drag nodes. Click node for details.
        </p>
      </div>

      {/* Side Panel for Entity Details */}
      {selectedNode && (
        <div className="w-80 flex-shrink-0 bg-white border border-gray-200 rounded-xl shadow-lg p-4 h-full overflow-y-auto animate-in slide-in-from-right duration-300 flex flex-col">
            <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-gray-900 break-words w-60">{selectedNode.id}</h3>
                <button onClick={closePanel} className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100">
                    <X size={20} />
                </button>
            </div>
            
            {loadingDetails ? (
                <div className="flex-grow flex justify-center items-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="bg-indigo-50 p-4 rounded-xl">
                        <div className="text-xs font-bold text-indigo-800 uppercase tracking-wide mb-1">Connections</div>
                        <div className="text-3xl font-extrabold text-indigo-600">
                            {nodeDetails?.links?.length || 0}
                        </div>
                    </div>

                    <div>
                        <h4 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2 border-b border-gray-100 pb-2">
                            <Info size={16} className="text-indigo-500" /> 
                            Relationships
                        </h4>
                        <div className="space-y-3">
                            {nodeDetails?.links?.map((link, idx) => {
                                // Determine direction
                                const isSource = link.source.id === selectedNode.id || link.source === selectedNode.id;
                                const otherNode = isSource ? (link.target.id || link.target) : (link.source.id || link.source);
                                
                                return (
                                    <div key={idx} className="text-sm bg-gray-50 p-3 rounded-lg border border-gray-100">
                                        <div className="text-gray-500 text-xs mb-1">
                                            {isSource ? (
                                                <span className="flex items-center gap-1">
                                                    is <span className="font-bold text-indigo-600 bg-indigo-50 px-1 rounded">{link.name}</span> of
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1">
                                                    has <span className="font-bold text-indigo-600 bg-indigo-50 px-1 rounded">{link.name}</span>
                                                </span>
                                            )}
                                        </div>
                                        <div className="font-bold text-gray-900 text-base">
                                            {otherNode}
                                        </div>
                                    </div>
                                );
                            })}
                            {(!nodeDetails?.links || nodeDetails.links.length === 0) && (
                                <div className="text-center py-8 text-gray-400 italic bg-gray-50 rounded-lg border border-dashed border-gray-200">
                                    No direct connections found.
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
      )}
    </div>
  );
};

export default GraphView;
