"""
Tests for Phase 1: Customer Diagnosis Flow (UC-02, FR-DIAG-01..09).
Acceptance: AT-01, AT-09.
Tests:
- Schema validation
- Price mapping from catalog (rounded to 10k VND, unknown code -> 'Cần thợ khảo sát')
- Quotas (10/day user, 2/day anon -> 429)
- Cache by content hash (24h)
- AI Fallback and retry behavior
- Graceful degradation path (can_book_without_diagnosis=True)
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.providers.ai import (
    AIDiagnosisAdapter,
    AIProvider,
    MockAIProvider,
    validate_ai_output,
)
from app.schemas.diagnosis import get_confidence_label, get_severity_vi
from app.services.diagnosis import (
    ANONYMOUS_DAILY_QUOTA,
    USER_DAILY_QUOTA,
    DiagnosisService,
    round_to_10k,
)


# ── 1. Schema Validation Tests ───────────────────────────────────────────────

class TestAISchemaValidation:
    def test_valid_schema(self):
        valid_payload = {
            "candidates": [
                {
                    "fault_code": "MB-ENG-VALVE-01",
                    "name": "Hở/kêu xú-páp",
                    "confidence": 0.72,
                    "severity": "medium",
                }
            ],
            "safety_warnings": ["Không chạy xe tiếp nếu máy kêu to"],
            "self_checks": ["Kiểm tra mức nhớt"],
            "followup_questions": [],
            "needs_technician": True,
        }
        is_valid, err = validate_ai_output(valid_payload)
        assert is_valid is True
        assert err is None

    def test_invalid_missing_fields(self):
        invalid_payload = {
            "candidates": [
                {"name": "Thiếu fault_code", "confidence": 0.5, "severity": "low"}
            ],
            "safety_warnings": [],
            "self_checks": [],
            "followup_questions": [],
            "needs_technician": True,
        }
        is_valid, err = validate_ai_output(invalid_payload)
        assert is_valid is False
        assert "fault_code" in err

    def test_invalid_confidence_range(self):
        invalid_payload = {
            "candidates": [
                {
                    "fault_code": "MB-01",
                    "name": "Lỗi",
                    "confidence": 1.5,  # > 1.0 invalid
                    "severity": "low",
                }
            ],
            "safety_warnings": [],
            "self_checks": [],
            "followup_questions": [],
            "needs_technician": True,
        }
        is_valid, err = validate_ai_output(invalid_payload)
        assert is_valid is False
        assert "confidence" in err

    def test_invalid_severity_value(self):
        invalid_payload = {
            "candidates": [
                {
                    "fault_code": "MB-01",
                    "name": "Lỗi",
                    "confidence": 0.5,
                    "severity": "extreme",  # Not in {low, medium, high, critical}
                }
            ],
            "safety_warnings": [],
            "self_checks": [],
            "followup_questions": [],
            "needs_technician": True,
        }
        is_valid, err = validate_ai_output(invalid_payload)
        assert is_valid is False
        assert "severity" in err

    def test_too_many_candidates(self):
        invalid_payload = {
            "candidates": [
                {"fault_code": f"MB-0{i}", "name": f"Lỗi {i}", "confidence": 0.5, "severity": "low"}
                for i in range(4)  # 4 candidates > max 3
            ],
            "safety_warnings": [],
            "self_checks": [],
            "followup_questions": [],
            "needs_technician": True,
        }
        is_valid, err = validate_ai_output(invalid_payload)
        assert is_valid is False
        assert "at most 3" in err


# ── 2. Price Mapping & Rounding Tests ─────────────────────────────────────────

class TestPriceMappingRules:
    def test_round_to_10k(self):
        assert round_to_10k(34000) == 30000
        assert round_to_10k(35000) == 40000
        assert round_to_10k(36000) == 40000
        assert round_to_10k(128000) == 130000
        assert round_to_10k(0) == 0

    @pytest.mark.asyncio
    async def test_known_fault_code_price_mapping(self):
        """Known fault code in catalog maps to rounded labor + parts."""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        service = DiagnosisService(mock_db, mock_redis)

        # Mock DB returning catalog item
        mock_catalog_item = MagicMock()
        mock_catalog_item.fault_code = "MB-TIRE-FLAT-01"
        mock_catalog_item.name = "Lốp xe bị xì / thủng"
        mock_catalog_item.labor_min = 30000
        mock_catalog_item.labor_max = 60000
        mock_catalog_item.parts_min = 0
        mock_catalog_item.parts_max = 35000
        mock_catalog_item.safety_notes = "Dừng xe sát lề"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_catalog_item
        mock_db.execute.return_value = mock_result

        candidates = [
            {"fault_code": "MB-TIRE-FLAT-01", "name": "AI Name", "confidence": 0.85, "severity": "medium"}
        ]
        mapped, extra_safety, max_conf = await service.map_candidates_to_catalog(candidates)

        assert len(mapped) == 1
        assert mapped[0].fault_code == "MB-TIRE-FLAT-01"
        assert mapped[0].name == "Lốp xe bị xì / thủng"
        # min = 30000 + 0 = 30000; max = 60000 + 35000 = 95000 -> rounded to 100000
        assert mapped[0].price_range.min == 30000
        assert mapped[0].price_range.max == 100000
        assert mapped[0].confidence_label == "Cao"  # >= 0.80
        assert "Dừng xe sát lề" in extra_safety

    @pytest.mark.asyncio
    async def test_unknown_fault_code_handling(self):
        """Unknown fault code displays 'Cần thợ khảo sát' and null price_range."""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        service = DiagnosisService(mock_db, mock_redis)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not in catalog
        mock_db.execute.return_value = mock_result

        candidates = [
            {"fault_code": "UNKNOWN-CODE-99", "name": "Lỗi lạ chưa rõ", "confidence": 0.40, "severity": "low"}
        ]
        mapped, _, _ = await service.map_candidates_to_catalog(candidates)

        assert len(mapped) == 1
        assert mapped[0].fault_code == "UNKNOWN-CODE-99"
        assert mapped[0].price_range is None
        assert mapped[0].price_display == "Cần thợ khảo sát"
        assert mapped[0].confidence_label == "Thấp"  # < 0.50


# ── 3. Quota Enforcement Tests (FR-DIAG-07) ───────────────────────────────────

class TestDiagnosisQuotas:
    @pytest.mark.asyncio
    async def test_authenticated_user_quota_limit(self):
        """Logged-in user gets 10 diagnoses/day; 11th raises 429."""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        service = DiagnosisService(mock_db, mock_redis)

        # Quota at 9: passes
        mock_redis.get = AsyncMock(return_value="9")
        mock_redis.incr = AsyncMock(return_value=10)
        mock_redis.expire = AsyncMock(return_value=True)

        await service.check_and_increment_quota(user_id="user-123", client_ip="127.0.0.1")

        # Quota at 10: raises 429
        mock_redis.get.return_value = "10"
        with pytest.raises(HTTPException) as exc_info:
            await service.check_and_increment_quota(user_id="user-123", client_ip="127.0.0.1")
        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["code"] == "QUOTA_EXCEEDED"

    @pytest.mark.asyncio
    async def test_anonymous_user_quota_limit(self):
        """Anonymous user gets 2 diagnoses/day; 3rd raises 429."""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        service = DiagnosisService(mock_db, mock_redis)

        mock_redis.get.return_value = "2"
        with pytest.raises(HTTPException) as exc_info:
            await service.check_and_increment_quota(user_id=None, client_ip="1.2.3.4")
        assert exc_info.value.status_code == 429
        assert "vãng lai" in exc_info.value.detail["message"]


# ── 4. Cache By Content Hash Tests (FR-DIAG-08) ───────────────────────────────

class TestDiagnosisCache:
    def test_content_hash_consistency(self):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        service = DiagnosisService(mock_db, mock_redis)

        h1 = service.compute_content_hash("motorbike", "Xe chết máy", ["/img2.jpg", "/img1.jpg"], None)
        h2 = service.compute_content_hash("motorbike", "Xe chết máy", ["/img1.jpg", "/img2.jpg"], None)
        assert h1 == h2

        h3 = service.compute_content_hash("home", "Xe chết máy", ["/img1.jpg"], None)
        assert h1 != h3

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data_without_calling_ai(self):
        """When cache hit occurs, AI adapter is NOT called."""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_ai = AsyncMock()
        service = DiagnosisService(mock_db, mock_redis, ai_adapter=mock_ai)

        cached_payload = {
            "id": "cached-uuid",
            "user_id": None,
            "asset_id": None,
            "category_id": None,
            "category_group": "motorbike",
            "description": "Lốp xì",
            "media_urls": [],
            "candidates": [
                {
                    "fault_code": "MB-TIRE-FLAT-01",
                    "name": "Lốp xe bị xì / thủng",
                    "confidence": 0.90,
                    "confidence_label": "Cao",
                    "severity": "medium",
                    "severity_vi": "Trung bình",
                    "price_range": {"min": 30000, "max": 60000, "currency": "VND"},
                    "price_display": "30.000đ - 60.000đ",
                }
            ],
            "safety_warnings": [],
            "self_checks": [],
            "followup_questions": [],
            "needs_technician": True,
            "can_book_without_diagnosis": False,
            "is_cached": True,
            "has_audio_beta": False,
            "created_at": "2026-10-24T00:00:00Z",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_payload))

        result = await service.create_diagnosis(
            user_id="user-1",
            client_ip="127.0.0.1",
            category_group="motorbike",
            category_id=None,
            asset_id=None,
            description="Lốp xì",
            media_urls=[],
        )

        assert result.is_cached is True
        assert result.id == "cached-uuid"
        # Verify AI adapter was never called
        mock_ai.diagnose.assert_not_called()


# ── 5. AI Fallback & Resilience Tests (AT-09) ─────────────────────────────────

class FailingProvider(AIProvider):
    async def diagnose_raw(self, *args, **kwargs):
        raise RuntimeError("Primary provider down")


class InvalidSchemaProvider(AIProvider):
    def __init__(self):
        self.call_count = 0

    async def diagnose_raw(self, *args, **kwargs):
        self.call_count += 1
        # Returns invalid schema
        return {"bad_key": 123}


class TestAIFallbackAndResilience:
    @pytest.mark.asyncio
    async def test_primary_fails_switches_to_secondary(self):
        """Primary provider fails -> automatically falls back to secondary provider."""
        failing_primary = FailingProvider()
        mock_secondary = MockAIProvider()

        adapter = AIDiagnosisAdapter(primary_provider=failing_primary, secondary_provider=mock_secondary)
        output, provider_used, is_graceful = await adapter.diagnose(
            category_group="motorbike",
            description="Xe bị thủng lốp",
            media_urls=[],
        )

        assert is_graceful is False
        assert provider_used == "MockAIProvider"
        assert len(output["candidates"]) > 0

    @pytest.mark.asyncio
    async def test_at_09_all_providers_fail_graceful_degradation(self):
        """AT-09: When all AI providers fail or timeout, system returns graceful failure allowing booking."""
        failing_primary = FailingProvider()
        failing_secondary = FailingProvider()

        adapter = AIDiagnosisAdapter(primary_provider=failing_primary, secondary_provider=failing_secondary)
        output, provider_used, is_graceful = await adapter.diagnose(
            category_group="motorbike",
            description="Hỏng hóc",
            media_urls=[],
        )

        assert is_graceful is True
        assert provider_used == "fallback_graceful"
        assert output["can_book_without_diagnosis"] is True
        assert len(output["candidates"]) == 0
        assert "chẩn đoán AI đang tạm thời gián đoạn" in output["safety_warnings"][0]


# ── 6. End-to-End Acceptance Tests (AT-01) ────────────────────────────────────

class TestAcceptanceAT01:
    @pytest.mark.asyncio
    async def test_at_01_motorbike_diagnosis_flow(self):
        """
        AT-01: Customer creates diagnosis from photo + description.
        Returns top-3 candidates, confidence %, price range from catalog, safety warnings, disclaimer.
        """
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Cache miss & quota ok
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.setex = AsyncMock(return_value=True)

        # Mock DB fault_catalog lookup
        def fake_catalog_query(stmt):
            mock_res = MagicMock()
            mock_item = MagicMock()
            mock_item.name = "Sên (xích) bị chùng / đứt"
            mock_item.labor_min = 50000
            mock_item.labor_max = 80000
            mock_item.parts_min = 80000
            mock_item.parts_max = 180000
            mock_item.safety_notes = "Không cố đạp nổ khi xích bị kẹt"
            mock_res.scalar_one_or_none.return_value = mock_item
            return mock_res

        mock_db.execute.side_effect = fake_catalog_query

        adapter = AIDiagnosisAdapter(primary_provider=MockAIProvider())
        service = DiagnosisService(mock_db, mock_redis, ai_adapter=adapter)

        res = await service.create_diagnosis(
            user_id="user-cust-01",
            client_ip="127.0.0.1",
            category_group="motorbike",
            category_id="cat-mb-01",
            asset_id=None,
            description="Xe máy Honda Wave bị đứt xích khi đang chạy trên đường Lê Lợi",
            media_urls=["/media/images/broken_chain.jpg"],
        )

        assert res.id is not None
        assert len(res.candidates) >= 1
        top = res.candidates[0]
        assert top.fault_code == "MB-ENG-CHAIN-01"
        assert top.confidence >= 0.80
        assert top.confidence_label == "Cao"
        assert top.price_range is not None
        # 50k+80k=130k min, 80k+180k=260k max
        assert top.price_range.min == 130000
        assert top.price_range.max == 260000
        assert "Không cố đạp nổ" in res.safety_warnings[0]
        assert "mang tính tham khảo" in res.disclaimer

    @pytest.mark.asyncio
    async def test_at_01_air_conditioner_diagnosis_flow(self):
        """AT-01: Home appliance (Air conditioner) diagnosis flow."""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.setex = AsyncMock(return_value=True)

        def fake_catalog_query(stmt):
            mock_res = MagicMock()
            mock_item = MagicMock()
            mock_item.name = "Thiếu gas lạnh R32/R410A"
            mock_item.labor_min = 150000
            mock_item.labor_max = 250000
            mock_item.parts_min = 150000
            mock_item.parts_max = 300000
            mock_item.safety_notes = "Không tự nạp gas, dễ bỏng lạnh"
            mock_res.scalar_one_or_none.return_value = mock_item
            return mock_res

        mock_db.execute.side_effect = fake_catalog_query

        adapter = AIDiagnosisAdapter(primary_provider=MockAIProvider())
        service = DiagnosisService(mock_db, mock_redis, ai_adapter=adapter)

        res = await service.create_diagnosis(
            user_id="user-cust-02",
            client_ip="127.0.0.1",
            category_group="home",
            category_id="cat-ac-01",
            asset_id=None,
            description="Điều hòa Daikin bật cả tiếng nhưng không mát, nghi thiếu gas lạnh",
            media_urls=["/media/images/ac_unit.jpg"],
        )

        assert res.id is not None
        top = res.candidates[0]
        assert top.fault_code == "AC-GAS-LOW-01"
        assert top.confidence >= 0.80
        assert top.confidence_label == "Cao"
        assert top.price_range.min == 300000
        assert top.price_range.max == 550000
        assert any("Không tự nạp gas" in w for w in res.safety_warnings)
