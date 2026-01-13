# Discovered Labs Build Challenge: Social Intelligence Engine

---

### Goal

Build a social intelligence system that discovers relevant communities for any company, tracks entities with relationship inference, measures competitive exposure, and models cross-channel influence propagation.

**Final System:** An intelligence platform where a user inputs a company + competitors, the system discovers high-value communities, extracts entities with relationships ("X criticized Y", "A partnered with B"), tracks competitive exposure with anomaly detection, and models how discussions propagate between channels, providing actionable intelligence with causal cross-channel explanations.

---

### Tech Stack Requirements

- **Backend:** Python (FastAPI or Flask)
• **Frontend:** React or Next.js
• **Containerization:** Docker (submission must run via `docker-compose up`)

---

### Key Concepts

- **Entity Resolution:** Normalize different mentions of the same entity into a canonical form
    - "OpenAI", "Open AI", "openai", "@openai" = same entity
- **Relationship Inference:** Extract relationships between entities from context
    - "Elon criticized OpenAI" = (Elon Musk, CRITICIZED, OpenAI)
- **Competitive Exposure:** Track share of voice, sentiment, and co-mention patterns across communities.
    - Detect anomalies and significant changes
- **Cross-Channel Causation:** Model how discussions propagate between platforms
    - Determine which channels lead vs follow for each topic

---

### Milestones

Complete as many of the milestone levels as you can to fully demonstrate you expertise and skill please.

---

### Level 0: Discovery + Entity Resolution

**Minimum requirements:**

- Given a company domain (e.g., "openai.com"), auto-discover relevant subreddits
- Analyze subreddit relevance based on: topic match, mention frequency, audience size, engagement quality
- Discover and rank top 20 subreddits, then fetch data from top 5 for demonstration
- Output ranked list with **business value scores**. You define what "valuable" means. Explain your reasoning.
- Implement entity resolution:
    - "OpenAI", "Open AI", "openai", "@openai", "the company behind ChatGPT" = same canonical entity
    - Confidence scoring per match
    - Simple UI to browse entities and their mentions with context
    - Data collection approach is your choice. Explain trade-offs in your Loom.
- Must run via `docker-compose up`

---

### Level 1: Relationship Inference

**Minimum requirements:**

- All Level 0 requirements, plus:
    - Implement relationship inference, extract not just entities but relationships from context:
        - "Sam Altman announced..." = (Sam Altman, ceo, OpenAI)
        - "Elon criticized OpenAI's approach" = (Elon Musk, opponent, OpenAI)
        - "Microsoft invested in OpenAI" = (Microsoft, investor, OpenAI)
    - Store as queryable graph. Visualization is bonus.
    - Surface key relationships per entity in UI
    - Use standard Google Knowledge Graph relationship types: founder, ceo, employee, investor, competitor, parentCompany, subsidiary, partner, acquiredBy, boardMember, advisor, alumniOf, affiliation
- You may extend with additional types if needed. Document any additions.
- You may use LLMs (GPT, Claude, etc.) for relationship inference OR build without LLM calls. Your choice. Explain your approach.

**How to submit:**

- Successful submission of Level 0
- Send private GitHub repo via email to `ben@discoveredlabs.com` with Loom link of working demonstration
- **NOTE: WILL ONLY EVALUATE WITH A RECORDING URL**

**On successful completion:**

- **$50 USD bounty**
- Technical interview scheduled with Discovered Labs team
- Note: You would only be judged on your performance in interviews and your work up to Level 1 if you decide not to complete the next levels

---

### Level 2: Competitive Exposure Tracking

**Minimum requirements:**

- All Level 0 and Level 1 requirements, plus:
• Given target company + list of competitors, track mention share across discovered subreddits
• Show:
- Share of voice per subreddit
- Sentiment distribution per company
- Co-mention patterns (when are competitors mentioned together?)
    - Detect anomalies:
    - Sudden spikes in mentions
    - Sentiment shifts
    - New entities emerging
        - You define anomaly thresholds. Explain your logic.
        - Surface significant changes with explanations
        - Dashboard UI must show all metrics. Design is your choice.

**How to submit:**

- Successful submission of Level 1
    - Send private GitHub repo via email to `ben@discoveredlabs.com` with Loom link of working demonstration
    - **NOTE: WILL ONLY EVALUATE WITH A RECORDING URL**

**On successful completion:**

- **$100 USD bounty**
- Note: You would only be judged on your performance in interviews and your work up to Level 1 if you decide not to complete the next levels

---

### Level 3: Cross-Channel Causation Analysis

**Minimum requirements:**

- All Level 0, Level 1, and Level 2 requirements, plus:
    - Add multi-platform support (Reddit + HackerNews + Twitter/X)
    - Use scraping approach for data collection to avoid API cost constraints
    - Model how discussions propagate BETWEEN channels:
- Did Reddit discussion cause Twitter buzz?
- Or did Twitter break first and Reddit follow?
    - Build influence flow graph showing which channels lead vs follow for each topic
    - Predict which channels will discuss next based on propagation patterns
    - Use data you've collected to validate predictions
    - Visualization of cross-channel influence flow

**How to submit:**

- Successful submission of Level 2
- Send private GitHub repo via email to `ben@discoveredlabs.com` with Loom link of working demonstration
- **NOTE: WILL ONLY EVALUATE WITH A RECORDING URL**

**On successful completion:**

- **$200 USD bounty (total)**
- Fast-track to final interview

---

### General Rules & Tips

- Loom recordings demonstrating the system working across multiple companies/competitors with clear explanations will be scored significantly higher
- Bonus points for:
    - Handling rate limits and data access challenges gracefully
    - Clean entity resolution with edge cases handled
    - Relationship inference that handles ambiguous context
    - Real-time or near-real-time updates
    - Clean, intuitive UI/UX
    - Scalable data collection and architecture approach
- You may use libraries for:
    - Basic NLP (spaCy, NLTK, etc. for tokenization)
    - Graph storage/visualization
    - HTTP requests / scraping utilities
- You must build from scratch:
    - Subreddit discovery + scoring logic
    - Entity resolution algorithm
    - Relationship inference logic (LLM prompting strategy counts as "building")
    - Anomaly detection
- Cross-channel causation modeling
- Feel free to take inspiration from:
    - https://github.com/networkx/networkx
    - https://github.com/explosion/spaCy
    - https://developers.google.com/knowledge-graph

---

### Evaluation Criteria

**What we're looking for:**

- **Problem Solving:** How do you approach anomaly detection? Cross-channel causation?
- **Code Quality:** Clean architecture, good abstractions, readable code

**Loom recording should cover:**

- Walk through your solution architecture
- Demo the working system with a real company (e.g., "hubspot.com")
- Explain your entity resolution approach, why did you build it this way?
- Show edge cases you handle (and ones you don't)
- What would you improve with more time?

---

### Timeline

**Submissions:** Rolling basis. The earlier you submit, the better.

- **Review turnaround:** 48 hours
- **Interview scheduled:** Within 2 days of Level 1 completion