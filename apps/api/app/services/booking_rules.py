"""
Booking business rules – Fix 24/7.
BR-03 through BR-07 per SRS §5.
All user-facing strings in Vietnamese. Currency VND (integers). Timezone Asia/Ho_Chi_Minh.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    pass

_TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")


# ── BR-03: Technician ranking ──────────────────────────────────────────────────

def rank_technicians(
    candidates: list[dict],
    order_lat: float,
    order_lng: float,
) -> list[dict]:
    """
    BR-03: Score and rank technician candidates.
    score = 0.4×proximity_norm + 0.3×(rating/5) + 0.2×accept_rate + 0.1×specialty_match
    Returns list sorted descending by score.

    Each candidate dict must have keys:
      - distance_m: float (metres from order location)
      - rating_avg: float (0–5)
      - accept_rate: float (0–1)
      - specialty_match: float (0–1)  – pre-computed by caller
    """
    if not candidates:
        return []

    # Normalise proximity: nearest tech scores 1.0, furthest 0.0
    distances = [c.get("distance_m", 0) for c in candidates]
    max_dist = max(distances) or 1  # avoid div/0

    scored = []
    for c in candidates:
        dist = c.get("distance_m", 0)
        proximity_norm = 1.0 - (dist / max_dist)
        rating_norm = float(c.get("rating_avg", 0)) / 5.0
        accept_rate = float(c.get("accept_rate", 0))
        specialty_match = float(c.get("specialty_match", 0))

        score = (
            0.4 * proximity_norm
            + 0.3 * rating_norm
            + 0.2 * accept_rate
            + 0.1 * specialty_match
        )
        scored.append({**c, "_score": round(score, 6)})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored


# ── BR-04: Night surcharge ─────────────────────────────────────────────────────

def get_night_surcharge(created_at: datetime, config: dict) -> int:
    """
    BR-04: Return night surcharge (VND integer) if order created between 22:00–05:00
    Asia/Ho_Chi_Minh local time. Amount from config (key 'night_surcharge', default 15000).
    """
    local_dt = created_at.astimezone(_TZ_VN)
    hour = local_dt.hour
    is_night = hour >= 22 or hour < 5

    if not is_night:
        return 0

    amount = config.get("night_surcharge", 15000)
    try:
        return int(amount)
    except (TypeError, ValueError):
        return 15000


# ── BR-05: Quote threshold check ──────────────────────────────────────────────

def check_quote_threshold(quote_total: int, price_max: int) -> bool:
    """
    BR-05: Returns True if quote_total exceeds price_max by more than 20%.
    When True, quote_reason is mandatory (enforced by caller/schema).
    """
    if price_max <= 0:
        return False
    return quote_total > price_max * 1.20


# ── BR-06: Cancellation fee ────────────────────────────────────────────────────

def get_cancellation_fee(order, config: dict) -> int:
    """
    BR-06: Return cancellation fee (VND integer).
    - 0 if technician has not yet started (ON_THE_WAY status not yet reached)
    - travel_fee from config if ON_THE_WAY was reached at any point.

    We determine this by checking order.status or order events;
    here we check if the order status has progressed past ACCEPTED
    (i.e. ON_THE_WAY or beyond) to keep it simple and dependency-free.
    Caller may also pass a pre-computed flag via order._reached_on_the_way.
    """
    from app.models import OrderStatus

    reached_statuses = {
        OrderStatus.ON_THE_WAY,
        OrderStatus.SURVEYING,
        OrderStatus.QUOTE_PENDING,
        OrderStatus.QUOTE_REJECTED,
        OrderStatus.IN_REPAIR,
        OrderStatus.AWAITING_CONFIRM,
        OrderStatus.COMPLETED,
        OrderStatus.DISPUTED,
    }

    current = order.status
    reached = current in reached_statuses

    if not reached:
        return 0

    travel_fee = config.get("travel_fee", 0)
    try:
        return int(travel_fee)
    except (TypeError, ValueError):
        return 0


# ── BR-07: Survey fee ─────────────────────────────────────────────────────────

def apply_survey_fee(order, config: dict) -> int:
    """
    BR-07: Returns survey_fee (VND integer) charged when customer rejects quote
    after technician surveys. Default 30000 VND.
    """
    survey_fee = config.get("survey_fee", 30000)
    try:
        return int(survey_fee)
    except (TypeError, ValueError):
        return 30000
