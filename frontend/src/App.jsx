import { useState, useEffect } from 'react'
import axios from 'axios'
import { Activity, Search, Users, Share2, BarChart2, Zap, Database } from 'lucide-react'
import DiscoveryPanel from './components/DiscoveryPanel'
import GraphView from './components/GraphView'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import EntityBrowser from './components/EntityBrowser'

// Configure Axios base URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const api = axios.create({ baseURL: API_URL });

function App() {
  const [status, setStatus] = useState('Checking System...')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('discovery')
  
  // Inputs
  const [domain, setDomain] = useState('openai.com')
  const [competitors, setCompetitors] = useState('google.com, anthropic.com')

  // Data State
  const [communities, setCommunities] = useState([])
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [exposureData, setExposureData] = useState(null)
  const [causationData, setCausationData] = useState(null)
  const [hasRun, setHasRun] = useState(false)

  const [companyPosts, setCompanyPosts] = useState([])

  const [discoveryHistory, setDiscoveryHistory] = useState([])
  const [selectedCompany, setSelectedCompany] = useState('')

  useEffect(() => {
    // Check backend health
    api.get('/')
      .then(res => setStatus(res.data.message))
      .catch(err => setStatus('Backend Disconnected'))
  }, [])

  const refreshDiscoveryHistory = async () => {
    try {
      const res = await api.get('/api/v1/discover/history')
      const items = res.data?.items || []
      setDiscoveryHistory(items)
      if (!hasRun && items.length > 0) {
        setHasRun(true)
      }
    } catch (e) {
      console.error('Failed to load discovery history', e)
    }
  }

  useEffect(() => {
    refreshDiscoveryHistory()
  }, [])

  const loadCachedCompany = async (companyDomain) => {
    if (!companyDomain) return
    setLoading(true)
    setHasRun(true)
    setActiveTab('discovery')
    setSelectedCompany(companyDomain)
    try {
      const res = await api.get(`/api/v1/discover/cached?domain=${companyDomain}`)
      setCommunities(res.data)

      const postsRes = await api.get(`/api/v1/discover/posts?domain=${companyDomain}`)
      setCompanyPosts(postsRes.data?.items || [])

      const graphRes = await api.get(`/api/v1/graph?domain=${companyDomain}`)
      setGraphData(graphRes.data)
    } catch (e) {
      console.error('Failed to load cached discovery', e)
      alert('No cached data found for this company. Try refetch.')
    } finally {
      setLoading(false)
    }
  }

  const refetchCompany = async (companyDomain) => {
    if (!companyDomain) return
    setLoading(true)
    setHasRun(true)
    setActiveTab('discovery')
    setSelectedCompany(companyDomain)
    try {
      const res = await api.post(`/api/v1/discover/refetch?domain=${companyDomain}`)
      setCommunities(res.data)
      await refreshDiscoveryHistory()

      const postsRes = await api.get(`/api/v1/discover/posts?domain=${companyDomain}`)
      setCompanyPosts(postsRes.data?.items || [])

      const graphRes = await api.get(`/api/v1/graph?domain=${companyDomain}`)
      setGraphData(graphRes.data)
    } catch (e) {
      console.error('Failed to refetch discovery', e)
      alert('Refetch failed. Ensure backend and DB are running.')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async () => {
    setLoading(true);
    setHasRun(true);
    setCommunities([]);
    setGraphData({ nodes: [], links: [] });
    setExposureData(null);
    setCausationData(null);

    try {
      // 1. Level 0: Discovery
      const discRes = await api.get(`/api/v1/discover?domain=${domain}`);
      setCommunities(discRes.data);
      setSelectedCompany(domain)
      await refreshDiscoveryHistory()

      const postsRes = await api.get(`/api/v1/discover/posts?domain=${domain}`)
      setCompanyPosts(postsRes.data?.items || [])

      // 2. Level 1: Graph (Fetching global graph for demo)
      const graphRes = await api.get(`/api/v1/graph?domain=${domain}`);
      setGraphData(graphRes.data);

      // 3. Level 2: Competitive Exposure
      const compList = competitors.split(',').map(c => c.trim()).filter(c => c);
      const expoRes = await api.post('/api/v1/analytics/exposure', {
        target_company: domain,
        competitors: compList
      });
      setExposureData(expoRes.data);

      // 4. Level 3: Causation
      // const causeRes = await api.post('/api/v1/analytics/causation', {
      //   target_company: domain
      // });
      // setCausationData(causeRes.data);

    } catch (error) {
      console.error("Analysis failed", error);
      alert("Analysis failed. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pb-20 min-h-screen font-sans text-gray-900 bg-gray-50">
      {/* Navigation */}
      <nav className="flex sticky top-0 z-50 justify-between items-center px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex gap-2 items-center text-xl font-bold text-indigo-600">
          <Activity />
          <span>SocialRadar</span>
        </div>
        <div className="text-sm text-gray-500">
          System Status: <span className={status === 'Backend Disconnected' ? 'text-red-500' : 'text-green-600 font-medium'}>{status}</span>
        </div>
      </nav>

      <main className="px-6 py-12 mx-auto max-w-7xl">
        
        {/* Header & Inputs */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-extrabold text-gray-900">Discover Your Social Footprint</h1>
          <p className="mx-auto mb-8 max-w-2xl text-lg text-gray-600">
            Enter a company domain to discover communities, track entities, and analyze influence across platforms.
          </p>

          <div className="p-2 mx-auto max-w-2xl bg-white rounded-2xl border border-gray-100 shadow-lg">
            <div className="flex flex-col gap-2 md:flex-row">
              <div className="relative flex-grow">
                <input 
                  type="text" 
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="Target (e.g. openai.com)" 
                  className="px-5 py-3 pl-12 w-full font-medium bg-gray-50 rounded-xl border-transparent transition outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
                <Search className="absolute left-4 top-1/2 text-gray-400 -translate-y-1/2" size={20} />
              </div>
              <div className="relative flex-grow">
                <input 
                  type="text" 
                  value={competitors}
                  onChange={(e) => setCompetitors(e.target.value)}
                  placeholder="Competitors (comma separated)" 
                  className="px-5 py-3 pl-12 w-full font-medium bg-gray-50 rounded-xl border-transparent transition outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
                <Users className="absolute left-4 top-1/2 text-gray-400 -translate-y-1/2" size={20} />
              </div>
              <button 
                onClick={handleAnalyze}
                disabled={loading}
                className={`px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition flex items-center gap-2 justify-center min-w-[140px] ${loading ? 'opacity-75 cursor-not-allowed' : ''}`}
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 rounded-full border-2 border-white animate-spin border-t-transparent" />
                    Running...
                  </>
                ) : (
                  <>
                    <Zap size={20} />
                    Analyze
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Results Area */}
        {hasRun && (
          <div className="space-y-8 duration-500 animate-in fade-in slide-in-from-bottom-4">
            
            {/* Tabs */}
            <div className="flex justify-center mb-8">
              <div className="inline-flex p-1 bg-white rounded-xl border border-gray-200 shadow-sm">
                {[
                  { id: 'discovery', label: 'Discovery', icon: Users },
                  { id: 'entities', label: 'Entity Browser', icon: Database },
                  { id: 'graph', label: 'Knowledge Graph', icon: Share2 },
                  { id: 'analytics', label: 'Intelligence', icon: BarChart2 },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-6 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                      activeTab === tab.id 
                        ? 'bg-indigo-600 text-white shadow-md' 
                        : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <tab.icon size={16} />
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="min-h-[400px]">
              {activeTab === 'discovery' && (
                <DiscoveryPanel
                  communities={communities}
                  loading={loading}
                  history={discoveryHistory}
                  selectedCompany={selectedCompany}
                  companyPosts={companyPosts}
                  onSelectCompany={loadCachedCompany}
                  onRefetchCompany={refetchCompany}
                />
              )}
              {activeTab === 'entities' && (
                <EntityBrowser />
              )}
              {activeTab === 'graph' && (
                <GraphView data={graphData} />
              )}
              {activeTab === 'analytics' && (
                <AnalyticsDashboard exposureData={exposureData} causationData={causationData} />
              )}
            </div>

          </div>
        )}
      </main>
    </div>
  )
}

export default App
