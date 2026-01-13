from typing import List, Dict, Any, Tuple
import pandas as pd
from app.models.unified import UnifiedPost, Platform


class CausationService:
    """
    Level 3: Cross-Channel Causation
    Models how discussions propagate between platforms (e.g. Reddit -> Twitter).
    """

    def _build_timeseries(self, posts: List[UnifiedPost], entity: str) -> pd.DataFrame:
        data = []
        needle = (entity or "").lower()
        for post in posts:
            if needle and needle in (post.content or "").lower():
                data.append({"platform": post.platform, "timestamp": post.timestamp})

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp"])
        if df.empty:
            return pd.DataFrame()

        pivot = df.pivot_table(
            index="timestamp", columns="platform", aggfunc="size", fill_value=0
        )
        pivot = pivot.resample("h").sum().fillna(0)
        return pivot

    def _best_lag_corr(
        self, a: pd.Series, b: pd.Series, max_lag_hours: int = 12
    ) -> Tuple[int, float]:
        best_lag = 0
        best_corr = 0.0
        for lag in range(-max_lag_hours, max_lag_hours + 1):
            corr = a.corr(b.shift(lag))
            if pd.notna(corr) and abs(corr) > abs(best_corr):
                best_corr = float(corr)
                best_lag = int(lag)
        return best_lag, best_corr

    def analyze_causation(
        self, posts: List[UnifiedPost], entity: str
    ) -> Dict[str, Any]:
        """
        Determines which platform 'leads' the conversation for a specific entity.
        """
        pivot = self._build_timeseries(posts, entity)
        if pivot.empty:
            return {"entity": entity, "leader": "Inconclusive", "correlation_score": 0}

        platforms = pivot.columns.tolist()
        if len(platforms) < 2:
            only = platforms[0] if platforms else "None"
            return {
                "entity": entity,
                "leader": only,
                "details": "Not enough cross-channel data",
                "platforms_analyzed": platforms,
            }

        # Train/test split for validation (last 25% is test, minimum 12 hours)
        n = len(pivot)
        test_n = max(12, int(n * 0.25))
        test_n = min(test_n, max(1, n - 1))
        train = pivot.iloc[:-test_n]
        test = pivot.iloc[-test_n:]

        edges = []
        for i in range(len(platforms)):
            for j in range(len(platforms)):
                if i == j:
                    continue
                a = platforms[i]
                b = platforms[j]
                lag, corr = self._best_lag_corr(train[a], train[b])
                if corr == 0 or pd.isna(corr):
                    continue

                # Determine direction using the same lag interpretation as before
                if lag < 0:
                    leader = b
                    follower = a
                    lag_hours = abs(lag)
                elif lag > 0:
                    leader = a
                    follower = b
                    lag_hours = lag
                else:
                    # simultaneous, skip edge
                    continue

                edges.append({
                    "from": str(leader.value if isinstance(leader, Platform) else leader),
                    "to": str(follower.value if isinstance(follower, Platform) else follower),
                    "lag_hours": int(lag_hours),
                    "correlation": round(float(corr), 3),
                })

        # Pick best single edge for backward-compatible fields
        best = None
        for e in edges:
            if best is None or abs(e["correlation"]) > abs(best["correlation"]):
                best = e

        if best is None:
            return {"entity": entity, "leader": "Inconclusive", "correlation_score": 0, "platforms_analyzed": [str(p.value if isinstance(p, Platform) else p) for p in platforms]}

        explanation = f"{best['from']} leads {best['to']} by {best['lag_hours']} hours"

        # Validation: evaluate each edge on test window using same lag
        hits = 0
        evaluated = 0
        test_corrs = []
        for e in edges:
            try:
                # Use value lookup to handle both string and enum key
                s_from = Platform(e["from"])
                s_to = Platform(e["to"])
            except Exception:
                continue

            if s_from not in test.columns or s_to not in test.columns:
                continue

            evaluated += 1
            lag = int(e["lag_hours"])
            # if from leads to by lag hours, then from aligns with to shifted into future (+lag)
            corr_t = test[s_from].corr(test[s_to].shift(lag))
            if pd.notna(corr_t):
                test_corrs.append(float(corr_t))
                # hit if same sign and magnitude is non-trivial
                if (corr_t >= 0 and e["correlation"] >= 0) or (corr_t < 0 and e["correlation"] < 0):
                    if abs(corr_t) >= 0.1:
                        hits += 1

        validation = {
            "edges_evaluated": evaluated,
            "hit_rate": round((hits / evaluated), 3) if evaluated else 0,
            "avg_test_correlation": round((sum(test_corrs) / len(test_corrs)), 3) if test_corrs else 0,
            "test_window_hours": int(test_n),
        }

        # Prediction: find current most active platform and predict next channels using outgoing edges
        recent = pivot.tail(6)
        # Ensure we use string keys for aggregation
        recent_sums = {str(p.value if isinstance(p, Platform) else p): float(recent[p].sum()) for p in platforms}
        current = max(recent_sums.items(), key=lambda x: x[1])[0]

        outgoing = [e for e in edges if e["from"] == current]
        outgoing.sort(key=lambda x: abs(x["correlation"]) / max(1, x["lag_hours"]), reverse=True)

        predictions = []
        for e in outgoing[:3]:
            predictions.append({
                "next_channel": e["to"],
                "from_channel": e["from"],
                "eta_hours": e["lag_hours"],
                "confidence": round(abs(e["correlation"]), 3),
            })

        flow_graph = {
            "nodes": [{"id": str(p.value if isinstance(p, Platform) else p)} for p in platforms],
            "edges": edges,
        }

        return {
            "entity": entity,
            "leader": best["from"],
            "correlation_score": best["correlation"],
            "explanation": explanation,
            "best_lag_hours": int(best["lag_hours"]),
            "platforms_analyzed": [str(p.value if isinstance(p, Platform) else p) for p in platforms],
            "flow_graph": flow_graph,
            "predictions": predictions,
            "validation": validation,
        }
