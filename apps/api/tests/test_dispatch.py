"""
Unit tests for Dispatch Ranking (BR-03) and Sequential Dispatch Worker.
Pure unit tests with time and DB mocking.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import Order, OrderStatus, _uuid_default
from app.services.booking_rules import rank_technicians
from app.services.dispatch_worker import start_dispatch


# ── BR-03 Ranking Tests ────────────────────────────────────────────────────────

def test_rank_technicians_empty():
    assert rank_technicians([], 16.4637, 107.5909) == []


def test_rank_technicians_single():
    cand = [{"user_id": "u1", "distance_m": 500, "rating_avg": 4.5, "accept_rate": 0.8, "specialty_match": 1.0}]
    ranked = rank_technicians(cand, 16.4637, 107.5909)
    assert len(ranked) == 1
    assert ranked[0]["user_id"] == "u1"
    assert "_score" in ranked[0]


def test_rank_technicians_proximity_dominates_when_others_equal():
    """Closer tech has higher score when rating, accept_rate, specialty are equal."""
    candidates = [
        {"user_id": "far", "distance_m": 2500, "rating_avg": 4.5, "accept_rate": 0.8, "specialty_match": 1.0},
        {"user_id": "near", "distance_m": 500, "rating_avg": 4.5, "accept_rate": 0.8, "specialty_match": 1.0},
    ]
    ranked = rank_technicians(candidates, 16.4637, 107.5909)
    assert ranked[0]["user_id"] == "near"
    assert ranked[1]["user_id"] == "far"
    assert ranked[0]["_score"] > ranked[1]["_score"]


def test_rank_technicians_rating_impact():
    """Higher rating beats lower rating when distance is equal."""
    candidates = [
        {"user_id": "low_rating", "distance_m": 1000, "rating_avg": 3.0, "accept_rate": 0.8, "specialty_match": 0.0},
        {"user_id": "high_rating", "distance_m": 1000, "rating_avg": 5.0, "accept_rate": 0.8, "specialty_match": 0.0},
    ]
    ranked = rank_technicians(candidates, 16.4637, 107.5909)
    assert ranked[0]["user_id"] == "high_rating"
    assert ranked[1]["user_id"] == "low_rating"


def test_rank_technicians_specialty_match_bonus():
    """Specialty match gives 0.1 bonus."""
    candidates = [
        {"user_id": "no_match", "distance_m": 1000, "rating_avg": 4.0, "accept_rate": 0.8, "specialty_match": 0.0},
        {"user_id": "match", "distance_m": 1000, "rating_avg": 4.0, "accept_rate": 0.8, "specialty_match": 1.0},
    ]
    ranked = rank_technicians(candidates, 16.4637, 107.5909)
    assert ranked[0]["user_id"] == "match"
    diff = round(ranked[0]["_score"] - ranked[1]["_score"], 4)
    assert diff == 0.1


def test_rank_technicians_numerical_formula():
    """Verify BR-03 formula exact value."""
    candidates = [
        {"user_id": "c1", "distance_m": 1000, "rating_avg": 4.0, "accept_rate": 0.9, "specialty_match": 1.0},
        {"user_id": "c2", "distance_m": 2000, "rating_avg": 4.0, "accept_rate": 0.9, "specialty_match": 1.0},
    ]
    ranked = rank_technicians(candidates, 16.4637, 107.5909)
    assert ranked[0]["_score"] == 0.72


# ── Dispatch Worker Execution Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_accept_flow():
    """Worker invites top tech, who accepts -> order becomes ACCEPTED."""
    order = MagicMock(spec=Order)
    order.id = _uuid_default()
    order.status = OrderStatus.CREATED
    order.lat = 16.4637
    order.lng = 107.5909
    order.address = "123 Le Loi, Hue"

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    candidate = {
        "user_id": "tech-001",
        "distance_m": 800,
        "rating_avg": 4.8,
        "accept_rate": 0.95,
        "specialty_match": 1.0,
    }

    async def mock_find_nearby(db, lat, lng, radius_m):
        return [candidate]

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"accepted")

    async def instant_sleep(secs):
        return

    with patch("app.services.dispatch_worker.transition_order", new_callable=AsyncMock) as mock_transition:
        await start_dispatch(
            db=mock_db,
            order=order,
            find_nearby_fn=mock_find_nearby,
            redis_client=mock_redis,
            sleep_fn=instant_sleep,
        )

        assert mock_transition.call_count >= 2
        calls = [c[0][2] for c in mock_transition.call_args_list]
        assert OrderStatus.SEARCHING in calls
        assert OrderStatus.ACCEPTED in calls
        assert order.technician_id == "tech-001"


@pytest.mark.asyncio
async def test_dispatch_no_tech_fallback():
    """When no technicians are available within 3km or 5km, ends in NO_TECH."""
    order = MagicMock(spec=Order)
    order.id = _uuid_default()
    order.status = OrderStatus.CREATED
    order.lat = 16.4637
    order.lng = 107.5909
    order.address = "123 Le Loi, Hue"

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # No candidates anywhere
    async def mock_find_nearby(db, lat, lng, radius_m):
        return []

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    async def instant_sleep(secs):
        return

    # Simulate time advancing 100 seconds to trigger expansion and finish
    simulated_times = [0.0, 100.0, 105.0, 110.0]
    time_index = 0

    def mock_time():
        nonlocal time_index
        val = simulated_times[min(time_index, len(simulated_times) - 1)]
        time_index += 1
        return val

    with patch("app.services.dispatch_worker.transition_order", new_callable=AsyncMock) as mock_transition, \
         patch("app.services.dispatch_worker.time.time", side_effect=mock_time):
        await start_dispatch(
            db=mock_db,
            order=order,
            find_nearby_fn=mock_find_nearby,
            redis_client=mock_redis,
            sleep_fn=instant_sleep,
        )

        calls = [c[0][2] for c in mock_transition.call_args_list]
        assert OrderStatus.SEARCHING in calls
        assert OrderStatus.NO_TECH in calls

