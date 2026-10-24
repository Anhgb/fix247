"""
AI Provider Interface and Implementations for Fix 24/7.
Strict SRS §7.2 JSON schema validation, retry up to 2 times, timeout 20s,
fallback to secondary provider, and graceful degradation path.

AGENTS.md: AI price rule – prices shown to users ALWAYS come from
fault_catalog table, NEVER from model output.
"""
import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Strict SRS §7.2 schema constraints
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def validate_ai_output(data: Any) -> tuple[bool, str | None]:
    """
    Validate AI output strictly against SRS §7.2 schema.
    Returns (is_valid, error_reason).
    """
    if not isinstance(data, dict):
        return False, "Output must be a JSON object"

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or len(candidates) == 0:
        return False, "Field 'candidates' must be a non-empty list"
    if len(candidates) > 3:
        return False, "Field 'candidates' can contain at most 3 items"

    for idx, c in enumerate(candidates):
        if not isinstance(c, dict):
            return False, f"Candidate [{idx}] must be a JSON object"
        for field in ("fault_code", "name", "confidence", "severity"):
            if field not in c:
                return False, f"Candidate [{idx}] missing required field '{field}'"

        if not isinstance(c["fault_code"], str) or not c["fault_code"].strip():
            return False, f"Candidate [{idx}].fault_code must be a non-empty string"
        if not isinstance(c["name"], str) or not c["name"].strip():
            return False, f"Candidate [{idx}].name must be a non-empty string"

        try:
            conf = float(c["confidence"])
            if not (0.0 <= conf <= 1.0):
                return False, f"Candidate [{idx}].confidence must be between 0 and 1"
        except (ValueError, TypeError):
            return False, f"Candidate [{idx}].confidence must be a float number"

        if c["severity"] not in VALID_SEVERITIES:
            return False, f"Candidate [{idx}].severity must be one of {VALID_SEVERITIES}"

    if not isinstance(data.get("safety_warnings"), list):
        return False, "Field 'safety_warnings' must be a list"
    if not isinstance(data.get("self_checks"), list):
        return False, "Field 'self_checks' must be a list"
    if not isinstance(data.get("followup_questions"), list):
        return False, "Field 'followup_questions' must be a list"
    if not isinstance(data.get("needs_technician"), bool):
        return False, "Field 'needs_technician' must be a boolean"

    return True, None


class AIProvider(ABC):
    """Abstract AI Provider interface."""

    @abstractmethod
    async def diagnose_raw(
        self,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None,
        clarifying_answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call AI model and return raw parsed JSON dict."""
        ...


class MockAIProvider(AIProvider):
    """
    Deterministic Mock AI Provider for development and local testing.
    Picks faults from known catalog by keywords.
    Supports low confidence (<50%) questions and simulation flags.
    """

    async def diagnose_raw(
        self,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None,
        clarifying_answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = ((description or "") + " " + json.dumps(clarifying_answers or {})).lower()

        # Testing hooks for simulation
        if "simulate_timeout" in text:
            await asyncio.sleep(25)
            raise TimeoutError("Simulated AI timeout > 20s")

        if "simulate_error" in text:
            raise RuntimeError("Simulated AI service unavailable")

        if "simulate_invalid_schema" in text:
            return {"error": "Invalid schema returned by mock"}

        # Low confidence test cases (<50%)
        if any(w in text for w in ("lạ lạ", "rung nhẹ", "không rõ", "kỳ kỳ", "chập chờn")):
            if not clarifying_answers:
                if category_group == "home":
                    return {
                        "candidates": [
                            {
                                "fault_code": "AC-FAN-MOTOR-01",
                                "name": "Motor quạt dàn lạnh / nóng yếu",
                                "confidence": 0.42,
                                "severity": "medium",
                            }
                        ],
                        "safety_warnings": [],
                        "self_checks": ["Thử tắt bật lại cầu dao điều hòa"],
                        "followup_questions": [
                            "Dàn nóng ngoài trời quạt có quay không?",
                            "Máy có báo đèn đỏ hoặc chớp nháy không?",
                        ],
                        "needs_technician": True,
                    }
                else:
                    return {
                        "candidates": [
                            {
                                "fault_code": "MB-ENG-VALVE-01",
                                "name": "Hở / kêu xu-páp",
                                "confidence": 0.45,
                                "severity": "medium",
                            }
                        ],
                        "safety_warnings": [],
                        "self_checks": ["Kiểm tra mức nhớt động cơ"],
                        "followup_questions": [
                            "Tiếng kêu cạch cạch hay tiếng hú gió khi tăng ga?",
                            "Xe bị nặng máy khi chở nặng hay ngay cả khi đi một mình?",
                        ],
                        "needs_technician": True,
                    }

        # Motorbike keyword matching
        if category_group == "motorbike" or any(w in text for w in ("xe", "wave", "sh", "honda", "yamaha")):
            if any(w in text for w in ("thủng", "xì", "lốp", "bánh", "vá", "đinh")):
                return {
                    "candidates": [
                        {
                            "fault_code": "MB-TIRE-FLAT-01",
                            "name": "Lốp xe bị xì / thủng",
                            "confidence": 0.92,
                            "severity": "medium",
                        },
                        {
                            "fault_code": "MB-TIRE-REPLACE-01",
                            "name": "Thay lốp xe mới",
                            "confidence": 0.58,
                            "severity": "medium",
                        },
                    ],
                    "safety_warnings": ["Dừng xe sát lề đường an toàn, không cố chạy gây hỏng vành mâm"],
                    "self_checks": ["Kiểm tra xem có đinh hoặc vết rách lớn ở lốp xe"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            if any(w in text for w in ("xích", "sên", "đứt", "chùng")):
                return {
                    "candidates": [
                        {
                            "fault_code": "MB-ENG-CHAIN-01",
                            "name": "Sên (xích) bị chùng / đứt",
                            "confidence": 0.88,
                            "severity": "medium",
                        },
                        {
                            "fault_code": "MB-TRANS-GEAR-01",
                            "name": "Số bị cứng / không vào số",
                            "confidence": 0.52,
                            "severity": "low",
                        },
                    ],
                    "safety_warnings": ["Không cố đạp nổ khi xích đã bị kẹt vào líp"],
                    "self_checks": ["Quan sát hộp sên xem xích có bị tuột hoặc đứt mắt"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            if any(w in text for w in ("bình", "ắc quy", "ắc-quy", "đề", "hết điện", "không đề")):
                return {
                    "candidates": [
                        {
                            "fault_code": "MB-BAT-DEAD-01",
                            "name": "Ắc-quy yếu / hết điện",
                            "confidence": 0.89,
                            "severity": "medium",
                        },
                        {
                            "fault_code": "MB-ELEC-RELAY-01",
                            "name": "Rơ-le khởi động hỏng",
                            "confidence": 0.62,
                            "severity": "low",
                        },
                        {
                            "fault_code": "MB-ENG-STARTER-01",
                            "name": "Đề (motor khởi động) yếu / hỏng",
                            "confidence": 0.51,
                            "severity": "medium",
                        },
                    ],
                    "safety_warnings": [],
                    "self_checks": ["Bật còi hoặc xi-nhan xem có hoạt động bình thường không", "Thử đạp nổ bằng cần đạp"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            if any(w in text for w in ("bugi", "chết máy", "không nổ", "tắt máy")):
                return {
                    "candidates": [
                        {
                            "fault_code": "MB-ENG-SPARK-01",
                            "name": "Bugi hỏng / bám muội than",
                            "confidence": 0.84,
                            "severity": "medium",
                        },
                        {
                            "fault_code": "MB-CARB-FUEL-01",
                            "name": "Bộ chế hòa khí bẩn / tắc xăng",
                            "confidence": 0.65,
                            "severity": "medium",
                        },
                    ],
                    "safety_warnings": [],
                    "self_checks": ["Kiểm tra kim xăng còn không", "Gạt chân chống bên lên"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            if any(w in text for w in ("phanh", "thắng", "đĩa", "má phanh")):
                return {
                    "candidates": [
                        {
                            "fault_code": "MB-BRAKE-PAD-01",
                            "name": "Bố phanh (má phanh) mòn",
                            "confidence": 0.85,
                            "severity": "high",
                        },
                        {
                            "fault_code": "MB-BRAKE-FLUID-01",
                            "name": "Dầu phanh thiếu / chảy rò",
                            "confidence": 0.60,
                            "severity": "high",
                        },
                    ],
                    "safety_warnings": ["Không đi xe khi phanh kém, nguy hiểm tính mạng"],
                    "self_checks": ["Bóp tay thắng kiểm tra độ sâu và cảm giác kẹt cứng"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            # Default Motorbike diagnosis
            return {
                "candidates": [
                    {
                        "fault_code": "MB-ENG-VALVE-01",
                        "name": "Hở / kêu xu-páp",
                        "confidence": 0.76,
                        "severity": "medium",
                    },
                    {
                        "fault_code": "MB-ENG-SPARK-01",
                        "name": "Bugi hỏng / bám muội than",
                        "confidence": 0.64,
                        "severity": "medium",
                    },
                    {
                        "fault_code": "MB-CARB-FUEL-01",
                        "name": "Bộ chế hòa khí bẩn / tắc xăng",
                        "confidence": 0.52,
                        "severity": "low",
                    },
                ],
                "safety_warnings": ["Không chạy xe tiếp nếu máy kêu to bất thường"],
                "self_checks": ["Kiểm tra mức nhớt", "Kiểm tra kim xăng"],
                "followup_questions": [],
                "needs_technician": True,
            }

        # Home Appliance matching
        if any(w in text for w in ("điều hòa", "máy lạnh", "daikin", "panasonic", "gas", "chảy nước", "lạnh")):
            if any(w in text for w in ("chảy nước", "nước nhỏ", "tắc ống", "tràn nước")):
                return {
                    "candidates": [
                        {
                            "fault_code": "AC-DRAIN-BLOCK-01",
                            "name": "Ống thoát nước bị tắc, chảy vào phòng",
                            "confidence": 0.89,
                            "severity": "medium",
                        },
                        {
                            "fault_code": "AC-FILTER-DIRTY-01",
                            "name": "Lọc bụi bẩn, giảm làm lạnh",
                            "confidence": 0.64,
                            "severity": "low",
                        },
                    ],
                    "safety_warnings": ["Tắt máy lạnh hoặc ngắt cầu dao để tránh nước ngấm vào mạch điện"],
                    "self_checks": ["Kiểm tra xem máng nước có bị tràn hoặc ống xả ngoài trời bị gập"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            if any(w in text for w in ("gas", "không mát", "kém lạnh", "hết gas", "không lạnh")):
                return {
                    "candidates": [
                        {
                            "fault_code": "AC-GAS-LOW-01",
                            "name": "Thiếu gas lạnh R32/R410A",
                            "confidence": 0.86,
                            "severity": "high",
                        },
                        {
                            "fault_code": "AC-FILTER-DIRTY-01",
                            "name": "Lọc bụi bẩn, giảm làm lạnh",
                            "confidence": 0.70,
                            "severity": "low",
                        },
                        {
                            "fault_code": "AC-FAN-MOTOR-01",
                            "name": "Motor quạt dàn lạnh / nóng yếu",
                            "confidence": 0.54,
                            "severity": "medium",
                        },
                    ],
                    "safety_warnings": ["Không tự nạp gas, dễ bỏng lạnh và nguy hiểm"],
                    "self_checks": ["Vệ sinh lưới lọc bụi của dàn lạnh", "Kiểm tra nhiệt độ cài đặt trên remote"],
                    "followup_questions": [],
                    "needs_technician": True,
                }

            # General AC
            return {
                "candidates": [
                    {
                        "fault_code": "AC-FILTER-DIRTY-01",
                        "name": "Lọc bụi bẩn, giảm làm lạnh",
                        "confidence": 0.82,
                        "severity": "low",
                    },
                    {
                        "fault_code": "AC-GAS-LOW-01",
                        "name": "Thiếu gas lạnh R32/R410A",
                        "confidence": 0.71,
                        "severity": "high",
                    },
                ],
                "safety_warnings": ["Bảo trì định kỳ giúp tiết kiệm điện và tránh nấm mốc"],
                "self_checks": ["Tháo nắp dàn lạnh kiểm tra lưới lọc"],
                "followup_questions": [],
                "needs_technician": True,
            }

        # Fallback general appliance
        return {
            "candidates": [
                {
                    "fault_code": "ELEC-CB-TRIP-01",
                    "name": "Aptomat (CB) nhảy liên tục",
                    "confidence": 0.75,
                    "severity": "critical",
                },
                {
                    "fault_code": "ELEC-OUTLET-01",
                    "name": "Ổ cắm điện hỏng / cháy",
                    "confidence": 0.60,
                    "severity": "medium",
                },
            ],
            "safety_warnings": ["Ngắt cầu dao tổng trước khi kiểm tra thiết bị"],
            "self_checks": ["Rút phích cắm tất cả thiết bị trên đường dây bị nhảy CB"],
            "followup_questions": [],
            "needs_technician": True,
        }


class GeminiAIProvider(AIProvider):
    """Gemini 1.5 Flash Provider with 20s timeout and strict JSON prompt."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().gemini_api_key

    async def diagnose_raw(
        self,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None,
        clarifying_answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        prompt = (
            f"Bạn là chuyên gia chẩn đoán kỹ thuật xe máy và điện máy tại TP. Huế cho hệ thống Fix 24/7.\n"
            f"Nhóm dịch vụ: {category_group}\n"
            f"Mô tả của khách hàng: {description or 'Không có mô tả'}\n"
            f"Thông tin thiết bị/xe: {json.dumps(asset_info or {}, ensure_ascii=False)}\n"
            f"Câu trả lời làm rõ: {json.dumps(clarifying_answers or {}, ensure_ascii=False)}\n"
            f"Media đính kèm: {media_urls}\n\n"
            f"QUAN TRỌNG: Bạn chỉ được trả về ĐÚNG MỘT JSON OBJECT theo đúng schema sau, không kèm bất kỳ giải thích nào khác:\n"
            f"{{\n"
            f'  "candidates": [\n'
            f'    {{"fault_code": "MÃ_LỖI", "name": "Tên lỗi tiếng Việt", "confidence": 0.85, "severity": "medium"}}\n'
            f"  ],\n"
            f'  "safety_warnings": ["Cảnh báo an toàn nếu có"],\n'
            f'  "self_checks": ["Kiểm tra sơ bộ khách tự làm được"],\n'
            f'  "followup_questions": ["Câu hỏi làm rõ nếu confidence < 0.5"],\n'
            f'  "needs_technician": true\n'
            f"}}\n"
            f"- confidence từ 0.0 đến 1.0\n"
            f"- severity chỉ chọn 1 trong: low, medium, high, critical\n"
            f"- candidates tối đa 3 phần tử\n"
            f"- TUYỆT ĐỐI KHÔNG TỰ SINH GIÁ TIỀN\n"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean possible markdown formatting
            cleaned = re.sub(r"^```json\s*", "", raw_text.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            return json.loads(cleaned)


class OpenAIAIProvider(AIProvider):
    """OpenAI GPT-4o-mini Provider with 20s timeout and JSON mode."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().openai_api_key

    async def diagnose_raw(
        self,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None,
        clarifying_answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        system_prompt = (
            "Bạn là trợ lý AI chẩn đoán sự cố xe máy và điện máy gia dụng tại TP. Huế cho hệ thống Fix 24/7. "
            "Chỉ trả về JSON theo đúng định dạng: "
            '{"candidates": [{"fault_code": str, "name": str, "confidence": float, "severity": "low"|"medium"|"high"|"critical"}], '
            '"safety_warnings": [str], "self_checks": [str], "followup_questions": [str], "needs_technician": bool}. '
            "Tối đa 3 candidates. Tuyệt đối không sinh giá tiền."
        )

        user_content = (
            f"Nhóm: {category_group}. Mô tả: {description}. "
            f"Thiết bị: {json.dumps(asset_info or {}, ensure_ascii=False)}. "
            f"Trả lời làm rõ: {json.dumps(clarifying_answers or {}, ensure_ascii=False)}."
        )

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)


class AIDiagnosisAdapter:
    """
    AI Diagnosis Adapter enforcing SRS §7.2 & FR-DIAG-02.
    - Max 2 retries on schema errors.
    - 20s timeout per call.
    - Automatic fallback: Primary -> Secondary -> Mock.
    - Graceful failure path (can_book_without_diagnosis=True).
    """

    def __init__(
        self,
        primary_provider: AIProvider | None = None,
        secondary_provider: AIProvider | None = None,
    ) -> None:
        settings = get_settings()
        self.primary_name = settings.provider_ai

        # Setup primary
        if primary_provider:
            self.primary = primary_provider
        elif self.primary_name == "gemini" and settings.gemini_api_key:
            self.primary = GeminiAIProvider()
        elif self.primary_name == "openai" and settings.openai_api_key:
            self.primary = OpenAIAIProvider()
        else:
            self.primary = MockAIProvider()

        # Setup secondary
        if secondary_provider:
            self.secondary = secondary_provider
        elif self.primary_name == "gemini" and settings.openai_api_key:
            self.secondary = OpenAIAIProvider()
        elif self.primary_name == "openai" and settings.gemini_api_key:
            self.secondary = GeminiAIProvider()
        else:
            self.secondary = MockAIProvider()

    async def execute_provider_with_retry(
        self,
        provider: AIProvider,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None,
        clarifying_answers: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Attempt provider with up to 2 retries on schema invalidation."""
        last_error = None
        for attempt in range(1, 4):  # initial + up to 2 retries = 3 attempts max
            try:
                # 20s timeout per FR-DIAG-02 & SRS 7.3
                raw_output = await asyncio.wait_for(
                    provider.diagnose_raw(
                        category_group,
                        description,
                        media_urls,
                        asset_info,
                        clarifying_answers,
                    ),
                    timeout=20.0,
                )
                is_valid, reason = validate_ai_output(raw_output)
                if is_valid:
                    return raw_output, None
                last_error = f"Schema validation error (attempt {attempt}): {reason}"
                logger.warning("ai_schema_validation_failed", attempt=attempt, reason=reason)
            except TimeoutError:
                last_error = f"AI Provider call timed out after 20s (attempt {attempt})"
                logger.warning("ai_call_timeout", attempt=attempt)
                break  # Don't retry same provider immediately if hard timeout
            except Exception as e:
                last_error = f"AI Provider error (attempt {attempt}): {str(e)}"
                logger.warning("ai_call_error", attempt=attempt, error=str(e))

        return None, last_error

    async def diagnose(
        self,
        category_group: str,
        description: str | None,
        media_urls: list[str],
        asset_info: dict[str, Any] | None = None,
        clarifying_answers: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str, bool]:
        """
        Execute diagnosis through fallback chain.
        Returns: (ai_output_dict, provider_used, is_graceful_failure)
        """
        # Try Primary Provider
        output, err = await self.execute_provider_with_retry(
            self.primary,
            category_group,
            description,
            media_urls,
            asset_info,
            clarifying_answers,
        )
        if output is not None:
            provider_name = getattr(self.primary, "__class__", type(self.primary)).__name__
            return output, provider_name, False

        logger.warning(
            "ai_primary_failed_switching_to_secondary",
            primary=str(self.primary),
            error=err,
        )

        # Try Secondary Provider (Fallback)
        if self.secondary and self.secondary is not self.primary:
            output, sec_err = await self.execute_provider_with_retry(
                self.secondary,
                category_group,
                description,
                media_urls,
                asset_info,
                clarifying_answers,
            )
            if output is not None:
                provider_name = getattr(self.secondary, "__class__", type(self.secondary)).__name__
                return output, provider_name, False
            logger.error("ai_secondary_failed_as_well", error=sec_err)

        # Graceful Failure Path (AT-09, FR-DIAG-02):
        # User can still book directly without diagnosis!
        logger.error("ai_all_providers_failed_returning_graceful_degradation")
        graceful_output = {
            "candidates": [],
            "safety_warnings": [
                "Hệ thống chẩn đoán AI đang tạm thời gián đoạn. Vui lòng ngắt nguồn hoặc dừng xe an toàn."
            ],
            "self_checks": ["Bạn có thể đặt thợ trực tiếp để được khảo sát tận nơi."],
            "followup_questions": [],
            "needs_technician": True,
            "can_book_without_diagnosis": True,
            "error_message": "Không thể hoàn tất chẩn đoán AI lúc này. Bạn có thể bấm 'Gọi thợ' để thợ khảo sát trực tiếp.",
        }
        return graceful_output, "fallback_graceful", True


def get_ai_adapter() -> AIDiagnosisAdapter:
    """Factory for AI diagnosis adapter."""
    return AIDiagnosisAdapter()


# Backward-compatible factory
def get_ai_provider() -> MockAIProvider:
    return MockAIProvider()
