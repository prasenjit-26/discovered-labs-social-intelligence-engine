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
    
    def calculate_metrics(self, posts: List[UnifiedPost], target_company: str, competitors: List[str]) -> Dict[str, Any]:
        """
        Calculates Share of Voice and Sentiment for target vs competitors.
        """
        # 1. Filter posts mentions
        # We need to scan posts to see who they mention. 
        # In a real DB, we'd query the 'mentions' table. 
        # Here we simulate scanning the 'content'.
        
        data = []
        all_entities = [target_company] + competitors
        
        for post in posts:
            content_lower = post.content.lower()
            found_entities = [e for e in all_entities if e.lower() in content_lower]
            
            # Sentiment
            # Use pre-calculated sentiment if available, otherwise calculate it
            if post.sentiment is not None:
                sentiment = post.sentiment
            else:
                blob = TextBlob(post.content)
                sentiment = blob.sentiment.polarity # -1.0 to 1.0
            
            for entity in found_entities:
                data.append({
                    "entity": entity,
                    "timestamp": post.timestamp,
                    "sentiment": sentiment,
                    "platform": post.platform,
                    "source_id": post.community_id
                })
                
        if not data:
            return {"share_of_voice": {}, "sentiment": {}, "anomalies": []}
            
        df = pd.DataFrame(data)
        
        # 2. Share of Voice
        # Count mentions per entity
        total_mentions = len(df)
        sov = df['entity'].value_counts(normalize=True).to_dict() # Percentage
        
        # 3. Sentiment Distribution
        # Average sentiment per entity
        sentiment_avg = df.groupby('entity')['sentiment'].mean().to_dict()
        
        # 4. Anomaly Detection (Simple Time-Series)
        anomalies = self._detect_anomalies(df)
        
        return {
            "share_of_voice": sov,
            "sentiment": sentiment_avg,
            "anomalies": anomalies,
            "total_mentions": total_mentions
        }

    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detects spikes in mentions.
        Logic: If volume in current hour > mean + 2*std_dev of previous window.
        """
        anomalies = []
        
        # Group by entity and hour
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        for entity in df['entity'].unique():
            entity_df = df[df['entity'] == entity].copy()
            # Resample to hourly counts
            hourly_counts = entity_df.set_index('timestamp').resample('h').size()
            
            if len(hourly_counts) < 5:
                continue
                
            mean = hourly_counts.mean()
            std = hourly_counts.std()
            
            # Check for spikes
            threshold = mean + (2 * std) if std > 0 else mean + 5
            
            spikes = hourly_counts[hourly_counts > threshold]
            
            for time, count in spikes.items():
                anomalies.append({
                    "entity": entity,
                    "type": "spike",
                    "timestamp": time.isoformat(),
                    "details": f"Mention count {count} exceeded threshold {round(threshold, 2)}"
                })
                
        return anomalies
