from typing import List, Dict, Any
import pandas as pd
from app.models.unified import UnifiedPost, Platform

class CausationService:
    """
    Level 3: Cross-Channel Causation
    Models how discussions propagate between platforms (e.g. Reddit -> Twitter).
    """
    
    def analyze_causation(self, posts: List[UnifiedPost], entity: str) -> Dict[str, Any]:
        """
        Determines which platform 'leads' the conversation for a specific entity.
        """
        # 1. Prepare Dataframe
        data = []
        for post in posts:
            if entity.lower() in post.content.lower():
                data.append({
                    "platform": post.platform,
                    "timestamp": post.timestamp
                })
                
        if not data:
            return {"leader": "Inconclusive", "correlation": 0}
            
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 2. Pivot to get timeseries per platform
        # Resample to hourly counts
        # Result: Index=Time, Columns=[reddit, twitter]
        pivot = df.pivot_table(index='timestamp', columns='platform', aggfunc='size', fill_value=0)
        
        # Resample to ensure continuous time axis (fill gaps with 0)
        pivot = pivot.resample('h').sum().fillna(0)
        
        platforms = pivot.columns.tolist()
        if len(platforms) < 2:
             return {"leader": platforms[0] if platforms else "None", "details": "Not enough cross-channel data"}
             
        # 3. Time-Lag Cross-Correlation
        # We compare Series A (Reddit) vs Series B (Twitter)
        # We shift A by +1h, +2h... and see if correlation improves.
        
        # Example: Reddit vs Twitter
        # If we have Reddit and Twitter data
        correlation_results = {}
        
        # Simple Pairwise check (e.g. Reddit vs Twitter)
        # In a real system, we'd do all pairs.
        p1 = platforms[0]
        p2 = platforms[1]
        
        series1 = pivot[p1]
        series2 = pivot[p2]
        
        max_corr = 0
        best_lag = 0
        direction = f"{p1} -> {p2}"
        
        # Check lags from -24h to +24h
        for lag in range(-12, 13):
            # Shift series2
            shifted_s2 = series2.shift(lag)
            corr = series1.corr(shifted_s2)
            
            if pd.notna(corr) and abs(corr) > abs(max_corr):
                max_corr = corr
                best_lag = lag
        
        # Interpret Lag
        # If lag is positive (e.g. +4), it means S1 aligns with S2 shifted INTO THE FUTURE.
        # Wait, let's verify logic:
        # S1.corr(S2.shift(lag))
        # If lag = -2 (S2 is shifted back 2 hours), and corr is high...
        # It means S1(t) looks like S2(t-2).
        # So S2 happened 2 hours ago. S2 leads S1.
        
        leader = "Unknown"
        if best_lag < 0:
            leader = p2 # S2 leads
            lag_hours = abs(best_lag)
            explanation = f"{p2} leads {p1} by {lag_hours} hours"
        elif best_lag > 0:
            leader = p1 # S1 leads
            lag_hours = best_lag
            explanation = f"{p1} leads {p2} by {lag_hours} hours"
        else:
            leader = "Simultaneous"
            explanation = "Events happen simultaneously"
            
        return {
            "entity": entity,
            "leader": leader,
            "correlation_score": round(max_corr, 3),
            "explanation": explanation,
            "best_lag_hours": best_lag,
            "platforms_analyzed": platforms
        }
