import spacy
from typing import List, Tuple, Optional
from app.services.entity_resolver import EntityResolver
from spacy.lang.en.stop_words import STOP_WORDS

class RelationshipExtractor:
    def __init__(self, resolver: Optional[EntityResolver] = None):
        # We reuse the entity resolver to normalize names before extracting relationships
        self.resolver = resolver if resolver else EntityResolver()
        self.nlp = self.resolver.nlp # Reuse the loaded spaCy model

        # Standard Google Knowledge Graph types + Custom mappings from problem statement
        self.verb_map = {
            "found": "founder",
            "start": "founder",
            "create": "founder",
            "launch": "founder",
            "lead": "ceo",
            "announce": "ceo", # Context dependent, but specified in example
            "run": "ceo",
            "criticize": "competitor",
            "attack": "competitor",
            "slam": "competitor",
            "invest": "investor",
            "buy": "investor",
            "acquire": "acquired",
            "partner": "partner",
            "join": "employee",
            "work": "employee",
            "hire": "employee",
            "advise": "advisor",
            "consult": "advisor",
            "own": "parentCompany",
            "parent": "parentCompany",
            "operate": "subsidiary", # "Operates X" -> X is subsidiary
            "graduate": "alumniOf",
            "affiliate": "affiliation",
            "serve": "boardMember"
        }

    async def extract_relations(self, text: str) -> List[Tuple[str, str, str, float]]:
        """
        Extracts (Subject, Verb, Object) triples.
        Example: "Elon Musk criticized OpenAI" -> ("Elon Musk", "opponent", "OpenAI")
        """
        doc = self.nlp(text)
        relations_set = set()

        relevant_entity_labels = {
            "ORG",
            "PERSON",
            "PRODUCT",
            "GPE",
            "LOC",
            "EVENT",
            "NORP",
            "WORK_OF_ART",
        }

        def _normalize_concept(raw: str) -> Optional[str]:
            if not raw:
                return None
            cleaned = " ".join(raw.strip().split())
            cleaned = cleaned.strip(" \n\t\r" + "\"'`()[]{}:;,.!?" )
            if not cleaned:
                return None
            if len(cleaned) < 3:
                return None
            return cleaned.lower()

        def _entity_for_token(sent, token):
            """Resolve an entity related to a token.

            In real text, the grammatical subject/object token is often a common noun
            (e.g., "announcement") while the entity appears inside its subtree.
            """
            if token is None:
                return None

            ents = [e for e in sent.ents if e.label_ in relevant_entity_labels]
            if not ents:
                return None

            # 1) Token is directly inside an entity span
            for ent in ents:
                if ent.start <= token.i < ent.end:
                    return ent

            # 2) Any entity appears in the token's subtree
            subtree_ids = {t.i for t in token.subtree}
            for ent in ents:
                if any(i in subtree_ids for i in range(ent.start, ent.end)):
                    return ent

            # 3) Token appears in an entity's subtree (entity head governs token)
            for ent in ents:
                ent_subtree_ids = {t.i for t in ent.root.subtree}
                if token.i in ent_subtree_ids:
                    return ent

            return None

        def _tokens_with_conj(token):
            if token is None:
                return []
            return [token] + list(token.conjuncts)

        def _concept_for_token(sent, token) -> Optional[str]:
            """Fallback concept extractor for Option B.

            If a token doesn't map cleanly to a named entity, we try to extract a noun phrase
            from its subtree. This enables relations like PERSON -> concept or concept -> concept.
            """
            if token is None:
                return None

            # Prefer nouns/proper nouns in subtree (avoids capturing whole clauses)
            candidates = [t for t in token.subtree if t.pos_ in {"NOUN", "PROPN"} and not t.is_stop]
            if not candidates:
                if token.pos_ in {"NOUN", "PROPN"} and not token.is_stop:
                    candidates = [token]
                else:
                    return None

            # Choose the leftmost noun-like head as anchor
            anchor = min(candidates, key=lambda t: t.i)
            span = doc[anchor.left_edge.i : anchor.right_edge.i + 1]

            # Don't duplicate named entities as concepts
            for ent in sent.ents:
                if ent.start <= span.start < ent.end or ent.start < span.end <= ent.end:
                    return None

            words = []
            for t in span:
                if t.is_space:
                    continue
                if t.is_punct:
                    continue
                if t.lower_ in STOP_WORDS:
                    continue
                if t.pos_ in {"DET", "PRON", "PART"}:
                    continue
                words.append(t.lemma_.lower())
                if len(words) >= 5:
                    break

            return _normalize_concept(" ".join(words))

        for sent in doc.sents:
            sent_ents = [e for e in sent.ents if e.label_ in relevant_entity_labels]

            for token in sent:
                if token.pos_ not in {"VERB", "AUX"}:
                    continue

                verb_lemma = token.lemma_.lower()
                relation_type = self.verb_map.get(verb_lemma, verb_lemma)

                subj_token = next((c for c in token.children if c.dep_ in {"nsubj", "nsubjpass"}), None)
                if subj_token is None:
                    continue

                obj_token = next((c for c in token.children if c.dep_ in {"dobj", "obj", "attr", "oprd"}), None)
                obj_via_prep = False
                if obj_token is None:
                    prep = next((c for c in token.children if c.dep_ == "prep"), None)
                    if prep is not None:
                        obj_token = next((c for c in prep.children if c.dep_ == "pobj"), None)
                        obj_via_prep = obj_token is not None

                # Clause complements (common in posts): "Hinton says agents can share knowledge"
                # Here, obj is not a direct noun; it is a clausal complement.
                if obj_token is None:
                    comp = next((c for c in token.children if c.dep_ in {"ccomp", "xcomp"}), None)
                    if comp is not None:
                        obj_token = comp

                if obj_token is None:
                    continue

                # Special case: Copula patterns like "Sam Altman is CEO of OpenAI"
                # spaCy often sets token="is" (AUX), subj=PERSON, obj_token=attr ("CEO"), and the ORG is pobj of "of".
                if verb_lemma == "be":
                    attr_token = next((c for c in token.children if c.dep_ == "attr"), None)
                    prep = next((c for c in token.children if c.dep_ == "prep" and c.lemma_.lower() == "of"), None)
                    pobj = next((c for c in prep.children if c.dep_ == "pobj"), None) if prep is not None else None
                    if attr_token is not None and pobj is not None:
                        attr_text = attr_token.text.lower()
                        if "ceo" in attr_text:
                            relation_type = "ceo"
                            obj_token = pobj
                            obj_via_prep = True
                        elif "founder" in attr_text or "cofound" in attr_text:
                            relation_type = "founder"
                            obj_token = pobj
                            obj_via_prep = True

                subj_candidates = []
                for st in _tokens_with_conj(subj_token):
                    ent = _entity_for_token(sent, st)
                    if ent is not None:
                        subj_candidates.append(ent)

                subj_concepts = []
                if len(subj_candidates) == 0:
                    for st in _tokens_with_conj(subj_token):
                        concept = _concept_for_token(sent, st)
                        if concept is not None:
                            subj_concepts.append(concept)

                obj_candidates = []
                for ot in _tokens_with_conj(obj_token):
                    ent = _entity_for_token(sent, ot)
                    if ent is not None:
                        obj_candidates.append(ent)

                obj_concepts = []
                if len(obj_candidates) == 0:
                    for ot in _tokens_with_conj(obj_token):
                        concept = _concept_for_token(sent, ot)
                        if concept is not None:
                            obj_concepts.append(concept)

                if (len(subj_candidates) == 0 and len(subj_concepts) == 0) or (len(obj_candidates) == 0 and len(obj_concepts) == 0):
                    continue

                subj_nodes: List[Tuple[str, bool]] = []
                for subj_ent in subj_candidates:
                    subj_nodes.append((await self.resolver._normalize(subj_ent.text), True))
                for subj_concept in subj_concepts:
                    subj_nodes.append((subj_concept, False))

                obj_nodes: List[Tuple[str, bool]] = []
                for obj_ent in obj_candidates:
                    obj_nodes.append((await self.resolver._normalize(obj_ent.text), True))
                for obj_concept in obj_concepts:
                    obj_nodes.append((obj_concept, False))

                for subj, subj_is_entity in subj_nodes:
                    for obj, obj_is_entity in obj_nodes:
                        if not subj or not obj:
                            continue
                        if subj == obj:
                            continue

                        confidence = 0.45
                        if verb_lemma in self.verb_map or relation_type in {"ceo", "founder"}:
                            confidence += 0.2
                        if subj_is_entity and obj_is_entity:
                            confidence += 0.1
                        confidence += 0.05 if obj_via_prep else 0.1
                        if len(sent_ents) > 4:
                            confidence -= 0.1
                        confidence = max(0.0, min(1.0, confidence))

                        relations_set.add((subj, relation_type, obj, round(confidence, 2)))

        return list(relations_set)
