# Social Intelligence Engine

A comprehensive social intelligence platform built for the Discovered Labs challenge. This system discovers communities, infers entity relationships, tracks competitive exposure, and models cross-channel causation.

## 🏗 Architecture

The system is built as a modular microservices-style application (monorepo):

- **Backend**: FastAPI (Python)
  - **Modular Sources**: Plugin system for Reddit, Twitter, etc. (`app/sources/`)
  - **Intelligence Engine**: 
    - `EntityResolver`: Normalizes names (e.g. "Open AI" -> "OpenAI").
    - `ExposureService`: Pandas-based Share of Voice & Sentiment analysis.
    - `CausationService`: Time-lag cross-correlation for trend propagation.
- **Frontend**: React + Vite + TailwindCSS
  - **Visualizations**: `react-force-graph-2d` (Knowledge Graph), `recharts` (Analytics).
- **Infrastructure**: Docker & Docker Compose.

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- A Reddit App (Client ID & Secret) from [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)

### Setup

1. **Configure Environment**
   Create a `.env` file in the root directory (copied from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Reddit credentials:
   ```
   REDDIT_CLIENT_ID=your_id
   REDDIT_CLIENT_SECRET=your_secret
   REDDIT_USER_AGENT=python:social-engine:v1.0
   ```

2. **Run with Docker**
   ```bash
   docker-compose up --build
   ```

3. **Access the App**
   - **Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🧠 Features Implemented

### Level 0: Discovery
- Auto-discovers relevant subreddits based on company domain.
- Ranks communities by a calculated "Business Value Score" (Relevance + Reach + Engagement).

### Level 1: Knowledge Graph
- Extracts Subject-Verb-Object relationships from text using NLP.
- Visualizes the network of entities (e.g., "Elon" -> "criticized" -> "OpenAI").

### Level 2: Competitive Exposure
- Tracks **Share of Voice** (Mention volume vs competitors).
- Analyzes **Sentiment** (Polarity of discussions).
- Detects **Anomalies** (Spikes in mentions) using statistical thresholds (Z-score logic).

### Level 3: Cross-Channel Causation
- Models influence flow between platforms (e.g., "Twitter leads Reddit by 4 hours").
- Uses **Time-Lag Cross-Correlation** to determine which channel breaks news first.
- Supports a reliable demo mode via a request flag (`use_mock_x`) that generates deterministic bursty X data.
- In mock mode, the backend also generates aligned mock HackerNews and Reddit posts (fixed lags) so the causation window has enough recent cross-channel overlap.

## 🎥 Demo Steps (L2 + L3)

### Level 2 (Competitive Exposure)
1. Enter a target domain (e.g., `openai.com`) and optionally competitors.
2. Click **Analyze** to run discovery and persist posts.
3. Go to **Level 2** tab to view:
   - Share of voice by subreddit
   - Sentiment metrics
   - Co-mentions
   - Anomalies

### Level 3 (Cross-Channel Causation)
1. Go to **Level 3** tab.
2. Enable **Use mock X data** (recommended for demos).
3. Click **Fetch X + HackerNews** to ingest cross-channel posts.
4. Click **Run Causation** to generate:
   - Influence flow graph
   - Predictions (next channel + ETA)
   - Validation stats

## 🔌 API Examples (curl)

### Level 3 Ingest (mock mode)
```bash
curl -X POST http://localhost:8000/api/v1/analytics/level3/ingest \
  -H "Content-Type: application/json" \
  -d '{"domain":"openai.com","limit_x":25,"limit_hn":25,"use_mock_x":true}'
```

### Level 3 Causation
```bash
curl -X POST http://localhost:8000/api/v1/analytics/causation \
  -H "Content-Type: application/json" \
  -d '{"target_company":"openai.com","days":14}'
```

## 📂 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/            # REST Endpoints
│   │   ├── services/       # Core Logic (NLP, Graph, Analytics)
│   │   ├── sources/        # Data Connectors (Reddit, etc.)
│   │   └── models/         # Pydantic Schemas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React Components (Graph, Charts)
│   │   └── App.jsx         # Main Dashboard Logic
│   └── Dockerfile
└── docker-compose.yml
```
