import spacy
from typing import List, Dict
import asyncio
from app.models.unified import EntityMatch
from app.core.database import supabase, get_supabase_client
from thefuzz import process, fuzz
import time

class EntityResolver:
    def __init__(self):
        print("Loading NLP Model...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
            
        # In-memory storage for canonical forms (In production, this goes to DB)
        # Format: {"openai": "OpenAI", "chatgpt": "ChatGPT"}
        self.canonical_map: Dict[str, str] = {}
        # We load mappings asynchronously in initialize()

    async def load_mappings(self):
        """Load existing mappings from Supabase asynchronously"""
        try:
            # We want to map variations to their canonical names
            # Table entity_variations: variation (PK), canonical_name (FK)
            response = await asyncio.to_thread(
                lambda: supabase.table("entity_variations").select("*").execute()
            )
            for item in response.data:
                # Map the variation (e.g. "open ai") to canonical (e.g. "OpenAI")
                # We assume variation in DB is what we use for lookup (lowercased stripped)
                self.canonical_map[item['variation']] = item['canonical_name']
            print(f"Loaded {len(self.canonical_map)} entity variations from DB.")
        except Exception as e:
            print(f"Warning: Could not load entity mappings from DB: {e}")

    async def extract_and_resolve(self, text: str) -> List[EntityMatch]:
        """
        Extracts entities from text and normalizes them.
        Returns structured EntityMatch objects with confidence scores.
        """
        doc = self.nlp(text)
        
        # Filter for relevant types
        # Expanded per Level 0 requirements
        relevant_labels = {
            "ORG", "PERSON", "PRODUCT", 
            "GPE", "LOC", "EVENT", "NORP", "WORK_OF_ART"
        }
        
        matches = []
        seen_canonical = set()
        
        for ent in doc.ents:
            if ent.label_ in relevant_labels:
                canonical = await self._normalize(ent.text, ent.label_)
                
                # Skip if we've already seen this entity in this text (simple deduplication)
                if canonical in seen_canonical:
                    continue
                    
                seen_canonical.add(canonical)
                
                # Heuristic confidence scoring
                # spaCy small model is decent but not perfect. 
                # If we have a canonical mapping already, we are more confident.
                confidence = 0.85
                if ent.text.lower().strip() in self.canonical_map:
                    confidence = 0.95
                
                # Extract context (surrounding sentence)
                context = ent.sent.text.strip()

                matches.append(EntityMatch(
                    text=canonical,
                    label=ent.label_,
                    confidence=confidence,
                    original_text=ent.text,
                    context=context
                ))
                
        return matches

    async def _normalize(self, raw_text: str, label: str = "UNKNOWN") -> str:
        """
        Converts 'open ai' -> 'OpenAI' and persists if new.
        Uses Fuzzy Matching to map to existing canonical entities.
        """
        # 1. Basic cleaning: remove '@', strip whitespace
        clean = raw_text.strip().replace("@", "")
        
        # 2. Key generation (lowercase, keep spaces for distinct variations)
        key = clean.lower()
        
        # 3. Check if we already have a canonical form (Exact Match)
        if key in self.canonical_map:
            return self.canonical_map[key]
        
        # 4. Fuzzy Match: Check if this is a variation of something we already know
        # e.g. "Open AI" vs "openai"
        if len(self.canonical_map) > 0 and len(key) > 3:
            # Get the best match from existing variation keys
            best_match = process.extractOne(key, self.canonical_map.keys(), scorer=fuzz.ratio)
            
            if best_match:
                match_text, score = best_match
                # Threshold: 90% similarity to consider it the same entity
                if score >= 90:
                    canonical_name = self.canonical_map[match_text]
                    
                    # Update memory
                    self.canonical_map[key] = canonical_name
                    
                    # Persist ONLY the new variation mapping
                    await asyncio.to_thread(self._persist_variation, key, canonical_name)
                    
                    return canonical_name

        # 5. If completely new, register this as the canonical form
        canonical_name = clean
        # If it came in all lowercase, try to title case it
        if clean.islower():
            canonical_name = clean.title()
            
        # Update memory
        self.canonical_map[key] = canonical_name
        
        # Update DB (New Entity + New Variation)
        await asyncio.to_thread(self._persist_entity, canonical_name, label, key)

        return canonical_name

    def _persist_entity(self, canonical_name: str, label: str, key: str):
        try:
            client = get_supabase_client()
            # Upsert Canonical Entity
            client.table("entities").upsert({
                "name": canonical_name,
                "label": label
            }).execute()
            
            # Upsert Variation
            self._persist_variation(key, canonical_name)
        except Exception as e:
            print(f"Error persisting entity {canonical_name}: {e}")

    def _persist_variation(self, variation: str, canonical_name: str):
        last_err = None
        for attempt in range(3):
            try:
                client = get_supabase_client()
                client.table("entity_variations").upsert({
                    "variation": variation,
                    "canonical_name": canonical_name
                }).execute()
                return
            except Exception as e:
                last_err = e
                time.sleep(0.2 * (attempt + 1))
        print(f"Error persisting variation {variation}: {last_err}")
