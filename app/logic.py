from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime, timezone

def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)

def _day_key(ts: str) -> str:
    return _parse_iso(ts).astimezone(timezone.utc).date().isoformat()

def daily_metrics(events: List[Dict[str, Any]], day: str) -> Dict[str, Any]:
    counts: Dict[str,int] = {}
    total_amount = 0.0
    for e in events:
        ts = e.get("ts_utc")
        if not ts or _day_key(ts) != day:
            continue
        et = str(e.get("event_type","unknown"))
        counts[et] = counts.get(et, 0) + 1
        amt = e.get("amount")
        if isinstance(amt, (int, float)):
            total_amount += float(amt)
    top = sorted(counts.items(), key=lambda kv:(-kv[1], kv[0]))[:10]
    return {
        "day": day,
        "event_count": sum(counts.values()),
        "counts_by_type": counts,
        "top_types": top,
        "total_amount": round(total_amount, 2),
    }

def delta(a: Dict[str,Any], b: Dict[str,Any]) -> Dict[str,Any]:
    return {
        "event_count_delta": a.get("event_count",0) - b.get("event_count",0),
        "total_amount_delta": round(float(a.get("total_amount",0.0)) - float(b.get("total_amount",0.0)), 2),
    }

def confidence_from_metrics(m: Dict[str,Any]) -> str:
    ev = int(m.get("event_count",0) or 0)
    amt = abs(float(m.get("total_amount",0.0) or 0.0))
    if ev == 0:
        return "low"
    if ev < 10 and amt < 500:
        return "low"
    if ev < 50:
        return "medium"
    return "high"

def explain(patterns: Dict[str,Any], ai_enabled: bool) -> Dict[str,Any]:
    if not ai_enabled:
        return {
            "enabled": False,
            "summary": None,
            "reasons": [],
            "confidence": "low",
            "scope": "daily_comparison",
            "model_version": "none",
        }

    dm = patterns.get("day_metrics") or {}
    conf = confidence_from_metrics(dm)
    reasons = []
    d = patterns.get("delta") or {}
    if d.get("event_count_delta",0) != 0:
        reasons.append("Transaction volume changed compared to the prior day.")
    if d.get("total_amount_delta",0.0) != 0.0:
        reasons.append("Revenue total changed compared to the prior day.")
    if not reasons:
        reasons.append("No material changes detected in deterministic summary.")
    summary = "Advisory explanation based on deterministic day-over-day comparison."
    return {
        "enabled": True,
        "summary": summary,
        "reasons": reasons,
        "confidence": conf,
        "scope": "daily_comparison",
        "model_version": "internal-heuristic-v1",
    }
