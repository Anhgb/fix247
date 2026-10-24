"""
Diagnosis Service – Fix 24/7.
FR-DIAG-01..09, UC-02.
- Upload validation (StorageService)
- Quotas: 10/day for user, 2/day for anonymous (FR-DIAG-07, returns 429)
- Cache by content hash for 24 hours (FR-DIAG-08)
- AI price rule: prices ALWAYS mapped from fault_catalog, rounded to 10.000đ (FR-DIAG-05)
- Unknown fault_code -> "Cần thợ khảo sát" & null price
- Low confidence (<50%) -> follow-up questions
"""
import hashlib
import json
import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Diagnosis, FaultCatalog, ServiceCategory
from app.providers.ai import AIDiagnosisAdapter, get_ai_adapter
from app.schemas.diagnosis import (
    CandidateResponse,
    DiagnosisResponse,
    PriceRange,
    get_confidence_label,
    get_severity_vi,
)

logger = get_logger(__name__)

USER_DAILY_QUOTA = 10
ANONYMOUS_DAILY_QUOTA = 2
CACHE_TTL_SECONDS = 86400  # 24 hours per FR-DIAG-08


def round_to_10k(amount: int | float) -> int:
    """Round to nearest 10,000 VND per FR-DIAG-05."""
    if amount <= 0:
        return 0
    return int(round(amount / 10000.0) * 10000)


class DiagnosisService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        ai_adapter: AIDiagnosisAdapter | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.ai = ai_adapter or get_ai_adapter()

    async def check_and_increment_quota(
        self,
        user_id: str | None,
        client_ip: str,
    ) -> None:
        """Enforce FR-DIAG-07 daily quotas."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        if user_id:
            quota_key = f"diag_quota:user:{user_id}:{today}"
            limit = USER_DAILY_QUOTA
            err_msg = f"Bạn đã sử dụng hết hạn mức {USER_DAILY_QUOTA} lượt chẩn đoán AI hôm nay."
        else:
            quota_key = f"diag_quota:anon:{client_ip}:{today}"
            limit = ANONYMOUS_DAILY_QUOTA
            err_msg = (
                f"Bạn đã sử dụng hết {ANONYMOUS_DAILY_QUOTA} lượt chẩn đoán vãng lai hôm nay. "
                "Vui lòng đăng nhập để có thêm 10 lượt chẩn đoán mỗi ngày."
            )

        current_count = await self.redis.get(quota_key)
        if current_count and int(current_count) >= limit:
            logger.warning(
                "diagnosis_quota_exceeded",
                user_id=user_id,
                client_ip=client_ip,
                current_count=current_count,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": err_msg,
                },
            )

        # Increment quota count with 24h expiration
        await self.redis.incr(quota_key)
        await self.redis.expire(quota_key, 86400)

    def compute_content_hash(
        self,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        clarifying_answers: dict[str, Any] | None,
    ) -> str:
        """FR-DIAG-08: SHA-256 of inputs."""
        hasher = hashlib.sha256()
        payload = {
            "group": category_group.lower(),
            "desc": (description or "").strip().lower(),
            "media": sorted(media_urls),
            "answers": clarifying_answers or {},
        }
        hasher.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
        return hasher.hexdigest()

    async def map_candidates_to_catalog(
        self,
        candidates: list[dict[str, Any]],
    ) -> tuple[list[CandidateResponse], list[str], float]:
        """
        AI Price Rule (AGENTS.md): Prices shown to users ALWAYS come from
        the fault_catalog table, never from model output.
        Unknown fault_code means "Cần thợ khảo sát" and no price.
        """
        mapped: list[CandidateResponse] = []
        extra_safety_warnings: list[str] = []
        max_conf = 0.0

        for c in candidates:
            code = c.get("fault_code", "").strip()
            name = c.get("name", "Sự cố kỹ thuật").strip()
            conf = float(c.get("confidence", 0.0))
            max_conf = max(max_conf, conf)
            sev = c.get("severity", "medium").lower()

            # Query catalog by fault_code
            stmt = select(FaultCatalog).where(
                FaultCatalog.fault_code == code,
                FaultCatalog.is_active.is_(True),
            )
            result = await self.db.execute(stmt)
            catalog_item = result.scalar_one_or_none()

            if catalog_item:
                min_total = catalog_item.labor_min + catalog_item.parts_min
                max_total = catalog_item.labor_max + catalog_item.parts_max
                rounded_min = round_to_10k(min_total)
                rounded_max = round_to_10k(max_total)

                price_range = PriceRange(min=rounded_min, max=rounded_max)
                price_display = f"{rounded_min:,.0f}đ - {rounded_max:,.0f}đ"
                safety_warning = catalog_item.safety_notes

                if safety_warning and safety_warning not in extra_safety_warnings:
                    extra_safety_warnings.append(safety_warning)

                mapped.append(
                    CandidateResponse(
                        fault_code=code,
                        name=catalog_item.name,
                        confidence=conf,
                        confidence_label=get_confidence_label(conf),
                        severity=sev,
                        severity_vi=get_severity_vi(sev),
                        price_range=price_range,
                        price_display=price_display,
                        safety_warning=safety_warning,
                    )
                )
            else:
                # Unknown fault code: Price is null and display "Cần thợ khảo sát"
                mapped.append(
                    CandidateResponse(
                        fault_code=code,
                        name=name,
                        confidence=conf,
                        confidence_label=get_confidence_label(conf),
                        severity=sev,
                        severity_vi=get_severity_vi(sev),
                        price_range=None,
                        price_display="Cần thợ khảo sát",
                        safety_warning=None,
                    )
                )

        return mapped, extra_safety_warnings, max_conf

    async def create_diagnosis(
        self,
        user_id: str | None,
        client_ip: str,
        category_group: str,
        category_id: str | None,
        asset_id: str | None,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None = None,
        clarifying_answers: dict[str, Any] | None = None,
    ) -> DiagnosisResponse:
        """
        Execute full diagnosis flow:
        1. Quota check
        2. Cache lookup (FR-DIAG-08)
        3. Call AI Adapter (with retry & fallback)
        4. Price mapping from fault_catalog
        5. Persist DB and Cache
        """
        # 1. Quota check (only if not already cached)
        content_hash = self.compute_content_hash(
            category_group, description, media_urls, clarifying_answers
        )
        cache_key = f"diag_cache:{content_hash}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            logger.info("diagnosis_cache_hit", hash=content_hash)
            cached_dict = json.loads(cached_data)
            cached_dict["is_cached"] = True
            return DiagnosisResponse(**cached_dict)

        # Enforce quota since this is a new AI call
        await self.check_and_increment_quota(user_id, client_ip)

        # 2. Call AI adapter
        ai_output, provider_used, is_graceful = await self.ai.diagnose(
            category_group=category_group,
            description=description,
            media_urls=media_urls,
            asset_info=asset_info,
            clarifying_answers=clarifying_answers,
        )

        raw_candidates = ai_output.get("candidates", [])
        mapped_candidates, extra_safety, max_conf = await self.map_candidates_to_catalog(
            raw_candidates
        )

        all_safety = list(
            dict.fromkeys(ai_output.get("safety_warnings", []) + extra_safety)
        )
        has_audio = any(
            url.endswith((".webm", ".ogg", ".mp3", ".wav", ".m4a")) or "/audios/" in url
            for url in media_urls
        )

        diag_id = str(uuid.uuid4())
        created_at_str = datetime.now(UTC).isoformat()

        # 3. Save DB record
        try:
            diag_record = Diagnosis(
                id=diag_id,
                user_id=user_id,
                asset_id=asset_id,
                category_id=category_id,
                media_urls=media_urls,
                description=description,
                input_hash=content_hash,
                ai_output=ai_output,
                ai_provider=provider_used,
                confidence_max=max_conf,
                has_safety_warnings=bool(all_safety),
            )
            self.db.add(diag_record)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error("failed_saving_diagnosis_db", error=str(e))

        response = DiagnosisResponse(
            id=diag_id,
            user_id=user_id,
            asset_id=asset_id,
            category_id=category_id,
            category_group=category_group,
            description=description,
            media_urls=media_urls,
            candidates=mapped_candidates,
            safety_warnings=all_safety,
            self_checks=ai_output.get("self_checks", []),
            followup_questions=ai_output.get("followup_questions", []),
            needs_technician=ai_output.get("needs_technician", True),
            can_book_without_diagnosis=is_graceful,
            is_cached=False,
            has_audio_beta=has_audio,
            created_at=created_at_str,
        )

        # 4. Cache in Redis for 24h (FR-DIAG-08)
        try:
            await self.redis.setex(
                cache_key,
                CACHE_TTL_SECONDS,
                response.model_dump_json(),
            )
        except Exception as e:
            logger.warning("failed_caching_diagnosis", error=str(e))

        return response

    async def get_diagnosis_by_id(self, diagnosis_id: str) -> DiagnosisResponse:
        """Retrieve diagnosis by ID and re-map current catalog prices."""
        stmt = select(Diagnosis).where(Diagnosis.id == diagnosis_id)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DIAGNOSIS_NOT_FOUND",
                    "message": "Không tìm thấy kết quả chẩn đoán yêu cầu.",
                },
            )

        ai_output = record.ai_output or {}
        raw_candidates = ai_output.get("candidates", [])
        mapped_candidates, extra_safety, _ = await self.map_candidates_to_catalog(
            raw_candidates
        )
        all_safety = list(
            dict.fromkeys(ai_output.get("safety_warnings", []) + extra_safety)
        )
        has_audio = any("/audios/" in u or u.endswith((".webm", ".ogg", ".mp3", ".wav")) for u in (record.media_urls or []))

        return DiagnosisResponse(
            id=record.id,
            user_id=record.user_id,
            asset_id=record.asset_id,
            category_id=record.category_id,
            category_group="motorbike" if any(c.fault_code.startswith("MB-") for c in mapped_candidates) else "home",
            description=record.description,
            media_urls=record.media_urls or [],
            candidates=mapped_candidates,
            safety_warnings=all_safety,
            self_checks=ai_output.get("self_checks", []),
            followup_questions=ai_output.get("followup_questions", []),
            needs_technician=ai_output.get("needs_technician", True),
            can_book_without_diagnosis=ai_output.get("can_book_without_diagnosis", False),
            is_cached=False,
            has_audio_beta=has_audio,
            created_at=record.created_at.isoformat() if record.created_at else datetime.now(UTC).isoformat(),
        )

    async def submit_feedback(
        self,
        diagnosis_id: str,
        verified_label: str | None,
        feedback_text: str | None,
        rating: int | None,
        user_id: str | None,
    ) -> dict[str, Any]:
        """FR-DIAG-09: Save verified label and feedback."""
        stmt = select(Diagnosis).where(Diagnosis.id == diagnosis_id)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "DIAGNOSIS_NOT_FOUND", "message": "Không tìm thấy chẩn đoán."},
            )

        if verified_label:
            record.verified_label = verified_label
            record.verified_by_id = user_id
            record.verified_at = datetime.now(UTC)

        await self.db.commit()
        return {"ok": True, "message": "Phản hồi chẩn đoán đã được ghi nhận."}
