from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from textblob import TextBlob
from app.models.unified import UnifiedPost

class ExposureService:
    """
    Level 2: Competitive Exposure Tracking
    Tracks share of voice, sentiment, and anomalies.
    """
    
    def calculate_metrics(
        self,
        posts: List[UnifiedPost],
        target_company: str,
        competitors: List[str],
        community_meta: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculates Level 2 metrics for target vs competitors using DB-persisted posts scoped to discovered communities.
        """
        community_meta = community_meta or {}

        companies: List[str] = [target_company] + (competitors or [])
        if len(companies) == 0:
            return {"share_of_voice": [], "sentiment": {}, "co_mentions": [], "anomalies": [], "total_posts": 0}

        def _aliases(domain: str) -> List[str]:
            d = (domain or "").strip().lower()
            if not d:
                return []
            base = d.split(".")[0]
            out = [d, base]
            # Cheap heuristic aliases for common patterns
            if base and base not in out:
                out.append(base)
            return list(dict.fromkeys([a for a in out if a]))

        aliases_by_company: Dict[str, List[str]] = {c: _aliases(c) for c in companies}

        # Build post-level mention signals (one row per post)
        post_rows: List[Dict[str, Any]] = []
        mention_rows: List[Dict[str, Any]] = []

        for post in posts:
            content = post.content or ""
            content_lower = content.lower()

            if post.sentiment is not None:
                sentiment = post.sentiment
            else:
                blob = TextBlob(content)
                sentiment = blob.sentiment.polarity

            mentioned: List[str] = []
            for company, aliases in aliases_by_company.items():
                if any(a in content_lower for a in aliases):
                    mentioned.append(company)

            post_rows.append({
                "post_id": post.id,
                "community_id": post.community_id,
                "timestamp": post.timestamp,
                "sentiment": sentiment,
                "mentioned": mentioned,
            })

            for company in mentioned:
                mention_rows.append({
                    "company": company,
                    "community_id": post.community_id,
                    "timestamp": post.timestamp,
                    "sentiment": sentiment,
                })

        total_posts = len(post_rows)
        if len(mention_rows) == 0:
            return {
                "share_of_voice": [],
                "sentiment": {},
                "co_mentions": [],
                "anomalies": [],
                "total_posts": total_posts,
            }

        mdf = pd.DataFrame(mention_rows)
        pdf = pd.DataFrame(post_rows)

        # Share of Voice per community (subreddit)
        counts = (
            mdf.groupby(["community_id", "company"]).size().reset_index(name="mentions")
        )
        community_totals = (
            mdf.groupby(["community_id"]).size().reset_index(name="total_mentions")
        )
        merged = counts.merge(community_totals, on="community_id", how="left")
        merged["share"] = merged["mentions"] / merged["total_mentions"].replace({0: 1})

        share_of_voice: List[Dict[str, Any]] = []
        for cid in merged["community_id"].unique():
            sub = merged[merged["community_id"] == cid]
            totals_by_company = {row["company"]: int(row["mentions"]) for _, row in sub.iterrows()}
            share_by_company = {row["company"]: float(row["share"]) for _, row in sub.iterrows()}
            meta = community_meta.get(cid, {})
            share_of_voice.append({
                "community_id": cid,
                "community_name": meta.get("name") or cid,
                "totals": totals_by_company,
                "shares": share_by_company,
                "total_mentions": int(sub["total_mentions"].iloc[0]) if len(sub) else 0,
            })

        # Sentiment distribution per company
        sentiment: Dict[str, Any] = {}
        for company in companies:
            sdf = mdf[mdf["company"] == company]
            if len(sdf) == 0:
                sentiment[company] = {"avg": 0.0, "count": 0, "buckets": {"negative": 0, "neutral": 0, "positive": 0}}
                continue
            avg = float(sdf["sentiment"].mean())
            neg = int((sdf["sentiment"] < -0.2).sum())
            neu = int(((sdf["sentiment"] >= -0.2) & (sdf["sentiment"] <= 0.2)).sum())
            pos = int((sdf["sentiment"] > 0.2).sum())
            sentiment[company] = {
                "avg": avg,
                "count": int(len(sdf)),
                "buckets": {"negative": neg, "neutral": neu, "positive": pos},
            }

        # Co-mentions (post-level)
        co_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        mention_counts: Dict[str, int] = defaultdict(int)
        for _, row in pdf.iterrows():
            mentioned = row.get("mentioned") or []
            mentioned = list(dict.fromkeys([m for m in mentioned if m]))
            for a in mentioned:
                mention_counts[a] += 1
            for i in range(len(mentioned)):
                for j in range(i + 1, len(mentioned)):
                    a = mentioned[i]
                    b = mentioned[j]
                    co_counts[a][b] += 1

        co_mentions: List[Dict[str, Any]] = []
        for a, row in co_counts.items():
            for b, cnt in row.items():
                denom = (mention_counts[a] + mention_counts[b] - cnt)
                jaccard = float(cnt / denom) if denom > 0 else 0.0
                co_mentions.append({"a": a, "b": b, "count": int(cnt), "jaccard": jaccard})

        # Anomaly Detection
        anomalies = self._detect_anomalies(mdf)

        return {
            "share_of_voice": share_of_voice,
            "sentiment": sentiment,
            "co_mentions": co_mentions,
            "anomalies": anomalies,
            "total_posts": total_posts,
        }

    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detects spikes in mentions.
        Logic: If daily volume > mean + 3*std_dev of previous window (or mean+5 if std==0).
        """
        anomalies = []
        
        if df is None or len(df) == 0:
            return []

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Daily counts by company + community
        df['day'] = df['timestamp'].dt.floor('D')

        grouped = df.groupby(['company', 'community_id', 'day']).size().reset_index(name='count')
        for (company, community_id), sub in grouped.groupby(['company', 'community_id']):
            if len(sub) < 7:
                continue

            mean = float(sub['count'].mean())
            std = float(sub['count'].std())
            threshold = mean + (3 * std) if std > 0 else mean + 5

            spikes = sub[sub['count'] > threshold]
            for _, row in spikes.iterrows():
                anomalies.append({
                    "entity": company,
                    "type": "mention_spike",
                    "timestamp": row['day'].isoformat(),
                    "details": f"Daily mentions {int(row['count'])} exceeded threshold {round(threshold, 2)} in community {community_id}"
                })

        # Sentiment shift detection
        # Logic:
        # - compute daily average sentiment per (company, community)
        # - compare most recent day to baseline mean of previous days
        # - flag when absolute delta > threshold and there is enough volume on the recent day
        sentiment_threshold = 0.2
        min_mentions = 2
        baseline_days = 3

        daily_sent = df.groupby(['company', 'community_id', 'day'])['sentiment'].mean().reset_index(name='avg_sentiment')
        daily_merged = daily_sent.merge(grouped, on=['company', 'community_id', 'day'], how='left')

        for (company, community_id), sub in daily_merged.groupby(['company', 'community_id']):
            sub = sub.sort_values('day')
            if len(sub) < (baseline_days + 1):
                continue

            latest = sub.iloc[-1]
            baseline = sub.iloc[-(baseline_days + 1):-1]
            baseline_mean = float(baseline['avg_sentiment'].mean())
            latest_avg = float(latest['avg_sentiment'])
            latest_count = int(latest.get('count') or 0)
            delta = latest_avg - baseline_mean

            if latest_count < min_mentions:
                continue
            if abs(delta) <= sentiment_threshold:
                continue

            anomalies.append({
                "entity": company,
                "type": "sentiment_shift",
                "timestamp": latest['day'].isoformat(),
                "details": f"Avg sentiment shifted by {round(delta, 2)} (baseline {round(baseline_mean, 2)} → {round(latest_avg, 2)}) in community {community_id}"
            })
                
        return anomalies
