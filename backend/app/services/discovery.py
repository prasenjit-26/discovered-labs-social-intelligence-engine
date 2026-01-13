from typing import List
from app.models.unified import Community
from app.sources.factory import get_reddit_source
from app.services.entity_resolver import EntityResolver
from app.services.relationship_extractor import RelationshipExtractor
from app.core.database import supabase, get_supabase_client
from app.core.config import settings
from app.services.llm_extractor import LLMExtractorService
from thefuzz import fuzz
from textblob import TextBlob
from app.services.graph_service import GraphService
import logging
import asyncio
import math
import time

logger = logging.getLogger(__name__)

class DiscoveryService:
    def __init__(self, graph_service: GraphService = None):
        # Initialize Reddit Source via Factory
        self.reddit_source = get_reddit_source()
        
        self.entity_resolver = EntityResolver()
        # Share the resolver to avoid double-loading spaCy
        self.relationship_extractor = RelationshipExtractor(resolver=self.entity_resolver)
        self.graph_service = graph_service if graph_service else GraphService()

        self.llm_extractor = None
        if getattr(settings, "OPENAI_API_KEY", ""):
            try:
                self.llm_extractor = LLMExtractorService()
            except Exception:
                self.llm_extractor = None

    async def initialize(self):
        """Perform async initialization tasks"""
        logger.info("Initializing Entity Resolver...")
        await self.entity_resolver.load_mappings()

    async def discover_communities(self, company_domain: str) -> List[Community]:
        """
        Level 0 Logic:
        1. Extract query from domain (openai.com -> openai)
        2. Search plugins
        3. Rank/Score results based on 'Business Value'
        4. Fetch top 5 data & resolve entities (Level 0 req)
        5. Persist to DB
        """
        # 1. Extraction
        query = company_domain.split('.')[0] # simplistic extraction
        
        # 2. Search (Mocking concurrent gathering for now)
        communities = await self.reddit_source.search_communities(query)
        
        # 3. Scoring & Ranking Logic
        scored_communities = self._rank_communities(communities, query)
        
        # 4. Fetch data for Top 5 (Level 0 requirement) - Parallelized
        top_communities = scored_communities[:5]
        import asyncio
        
        # Create tasks for parallel processing
        tasks = [self._process_community(comm, company_domain) for comm in top_communities]
        await asyncio.gather(*tasks)

        # Return top 20
        return scored_communities[:20]

    async def _process_community(self, comm: Community, company_domain: str):
        """Fetches posts, resolves entities, and persists data for a single community."""
        try:
            # Limit to 5 posts per community for LLM batching + cost control
            posts = await self.reddit_source.fetch_discussions(comm.id, limit=5)
            
            # 1) Entity resolution (basic NLP) for each post
            for post in posts:
                post.entities = await self.entity_resolver.extract_and_resolve(post.content)
                blob = TextBlob(post.content)
                post.sentiment = blob.sentiment.polarity

            # 2) Relationship inference (LLM) batched per community
            if self.llm_extractor:
                batch = []
                for post in posts:
                    entities = []
                    seen = set()
                    for ent in post.entities:
                        canonical = (ent.text or "").strip()
                        if not canonical:
                            continue
                        if canonical in seen:
                            continue
                        seen.add(canonical)
                        entities.append({"canonical": canonical, "label": ent.label})

                    batch.append({"id": post.id, "text": post.content, "entities": entities})

                extracted = await self.llm_extractor.infer_relations(batch)
                post_map = extracted.get("posts", {}) if isinstance(extracted, dict) else {}

                for post in posts:
                    info = post_map.get(post.id, {}) if isinstance(post_map, dict) else {}
                    rel_list = info.get("relations", []) if isinstance(info, dict) else []

                    for r in rel_list if isinstance(rel_list, list) else []:
                        try:
                            src = (r.get("source") or "").strip()
                            rel = (r.get("relation") or "").strip()
                            tgt = (r.get("target") or "").strip()
                            conf = float(r.get("confidence") or 0.6)
                            if not src or not rel or not tgt:
                                continue

                            await self.graph_service.add_relationship(
                                src,
                                rel,
                                tgt,
                                confidence=max(0.0, min(1.0, conf)),
                                company_domain=company_domain,
                            )
                        except Exception:
                            continue
            else:
                # Fallback relationship inference (non-LLM)
                for post in posts:
                    relations = await self.relationship_extractor.extract_relations(post.content)
                    for subj, rel, obj, confidence in relations:
                        await self.graph_service.add_relationship(subj, rel, obj, confidence=confidence, company_domain=company_domain)
                
            comm.recent_posts = posts
            
            # 5. Persist to DB
            await asyncio.to_thread(self._persist_community_data, comm)
            
        except Exception as e:
            logger.error(f"Error fetching/saving posts for {comm.name}: {e}")

    def _persist_community_data(self, community: Community):
        """Save community and its posts to Supabase"""
        try:
            client = get_supabase_client()
            # Upsert Community
            data = {
                "id": community.id,
                "name": community.name,
                "url": community.url,
                "platform": community.platform.value,
                "subscribers": community.subscribers,
                "active_users": community.active_users,
                "description": community.description,
                "relevance_score": community.relevance_score
            }

            last_err = None
            for attempt in range(3):
                try:
                    client.table("communities").upsert(data).execute()
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(0.2 * (attempt + 1))
            if last_err is not None:
                raise last_err
            
            # Upsert Posts
            for post in community.recent_posts:
                post_data = {
                    "id": post.id,
                    "platform": post.platform.value,
                    "content": post.content,
                    "author_id": post.author.id,
                    "author_username": post.author.username,
                    "community_id": community.id,
                    "timestamp": post.timestamp.isoformat(),
                    "engagement_score": post.engagement_score,
                    "url": post.url,
                    "sentiment": post.sentiment # Now populated
                }
                last_err = None
                for attempt in range(3):
                    try:
                        client.table("posts").upsert(post_data).execute()
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        time.sleep(0.2 * (attempt + 1))
                if last_err is not None:
                    print(f"Error saving post {post.id}: {last_err}")

                # Level 0 Requirement: Persist Entity Mentions with Context
                if post.entities:
                    # Ensure canonical entities + variations exist before inserting mentions (FK constraints)
                    try:
                        entities_rows = []
                        variations_rows = []

                        for ent in post.entities:
                            entities_rows.append({
                                "name": ent.text,
                                "label": ent.label,
                            })
                            variation_key = (ent.original_text or "").strip().replace("@", "").lower()
                            if variation_key:
                                variations_rows.append({
                                    "variation": variation_key,
                                    "canonical_name": ent.text,
                                })

                        if entities_rows:
                            client.table("entities").upsert(entities_rows).execute()
                        if variations_rows:
                            client.table("entity_variations").upsert(variations_rows).execute()
                    except Exception as e:
                        print(f"Error upserting entities/variations for post {post.id}: {e}")

                    mentions_data = []
                    for ent in post.entities:
                        mentions_data.append({
                            "entity_name": ent.text,
                            "post_id": post.id,
                            "variation_used": ent.original_text,
                            "confidence": ent.confidence,
                            "context": ent.context
                        })
                    if mentions_data:
                        # Insert mentions (ignore errors if duplicates or issues, mostly just logging)
                        try:
                            last_err = None
                            for attempt in range(3):
                                try:
                                    client.table("entity_mentions").insert(mentions_data).execute()
                                    last_err = None
                                    break
                                except Exception as e:
                                    last_err = e
                                    time.sleep(0.2 * (attempt + 1))
                            if last_err is not None:
                                raise last_err
                        except Exception as e:
                             # Don't fail the whole batch for one mention error, but log it
                            print(f"Error saving mentions for post {post.id}: {e}")
                
        except Exception as e:
            print(f"DB Persist Error for {community.name}: {e}")

    def _rank_communities(self, communities: List[Community], query: str) -> List[Community]:
        """
        Calculates 'Business Value Score' for each community.
        
        Formula factors:
        - Relevance (Text match of name/description to query)
        - Reach (Log of subscribers)
        - Engagement (Active users / Subscribers ratio)
        """
        for comm in communities:
            # 1. Relevance: How close is the subreddit name to the company name?
            # We use fuzzy matching. "OpenAI" vs "OpenAI" = 100. "ArtificialIntelligence" vs "OpenAI" = low.
            name_match = fuzz.partial_ratio(query.lower(), comm.name.lower())
            desc_match = fuzz.partial_ratio(query.lower(), comm.description.lower()) if comm.description else 0
            
            # Weighted relevance
            relevance = (name_match * 0.7 + desc_match * 0.3) / 100.0
            
            # 2. Engagement Ratio
            engagement_ratio = 0.0
            if comm.subscribers > 0 and comm.active_users and comm.active_users > 0:
                engagement_ratio = comm.active_users / comm.subscribers

            # 2b. Reach (log-scaled so very large communities don't dominate)
            reach_score = 0.0
            if comm.subscribers and comm.subscribers > 0:
                # Normalize so ~100k subscribers maps close to max reach score
                reach_score = min((math.log10(comm.subscribers + 1) / math.log10(100000)) * 20.0, 20.0)
            
            # 3. Final Score
            # We prioritize Relevance heavily, then Reach.
            # Score = (Relevance * 50) + (Log(Subscribers) * factor) ... simplified here:
            
            # Normalized score 0-100 (heuristic)
            engagement_score = min(engagement_ratio * 100.0, 20.0)
            raw_score = (relevance * 70) + engagement_score + reach_score
            
            comm.relevance_score = round(raw_score, 2)
            
        # Sort by score descending
        return sorted(communities, key=lambda x: x.relevance_score, reverse=True)
