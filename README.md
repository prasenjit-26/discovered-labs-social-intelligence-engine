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
- *(Note: Twitter data is mocked for demonstration purposes as API access requires paid plans).*

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
