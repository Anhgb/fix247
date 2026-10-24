#!/usr/bin/env python
"""
Seed script – Fix 24/7
Populates: categories, 60+ fault_catalog, 12 technicians, 5 customers, 1 admin, 3 QR locations, platform_config.
Run: python -m app.seed  (from apps/api directory)
"""
import asyncio
import os
import secrets
import sys
import uuid
from datetime import UTC, datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Load env
from dotenv import load_dotenv
load_dotenv(override=True)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://fix247:fix247pass@localhost:5432/fix247",
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ── Helpers ───────────────────────────────────────────────────────────────────

def uid() -> str:
    return str(uuid.uuid4())


def now_str() -> str:
    return datetime.now(UTC).isoformat()


# ── Data ──────────────────────────────────────────────────────────────────────

CATEGORIES = [
    # group=motorbike
    {"id": uid(), "name": "Động cơ xe máy", "group": "motorbike", "icon": "🔧", "sort_order": 1},
    {"id": uid(), "name": "Điện xe máy", "group": "motorbike", "icon": "⚡", "sort_order": 2},
    {"id": uid(), "name": "Hệ thống lái & phanh xe máy", "group": "motorbike", "icon": "🛞", "sort_order": 3},
    {"id": uid(), "name": "Thân – vỏ xe máy", "group": "motorbike", "icon": "🏍️", "sort_order": 4},
    # group=home
    {"id": uid(), "name": "Điều hòa không khí", "group": "home", "icon": "❄️", "sort_order": 5},
    {"id": uid(), "name": "Tủ lạnh", "group": "home", "icon": "🧊", "sort_order": 6},
    {"id": uid(), "name": "Máy giặt", "group": "home", "icon": "🫧", "sort_order": 7},
    {"id": uid(), "name": "Điện dân dụng", "group": "home", "icon": "🔌", "sort_order": 8},
    {"id": uid(), "name": "Hệ thống nước", "group": "home", "icon": "🚿", "sort_order": 9},
    {"id": uid(), "name": "Đồ gia dụng khác", "group": "home", "icon": "🔨", "sort_order": 10},
]


def _cat(name: str) -> str:
    for c in CATEGORIES:
        if c["name"] == name:
            return c["id"]
    raise ValueError(f"Category not found: {name}")


# 60+ faults with Vietnamese names and realistic Hue market prices (VND)
FAULTS = [
    # ── Động cơ xe máy ────────────────────────────────────────────────────────
    {"fault_code": "MB-ENG-SPARK-01", "name": "Bugi hỏng / bám muội than", "labor_min": 30000, "labor_max": 50000, "parts_min": 15000, "parts_max": 60000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-OIL-01", "name": "Thay nhớt động cơ", "labor_min": 20000, "labor_max": 30000, "parts_min": 50000, "parts_max": 120000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-VALVE-01", "name": "Hở / kêu xu-páp (xupap)", "labor_min": 150000, "labor_max": 250000, "parts_min": 80000, "parts_max": 200000, "cat": "Động cơ xe máy", "safety_notes": "Không chạy xe tiếp nếu máy kêu to"},
    {"fault_code": "MB-ENG-PISTON-01", "name": "Piston – xi-lanh mòn, ăn nhớt", "labor_min": 350000, "labor_max": 600000, "parts_min": 200000, "parts_max": 500000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-CARB-FUEL-01", "name": "Bộ chế hòa khí bẩn / tắc xăng", "labor_min": 80000, "labor_max": 150000, "parts_min": 0, "parts_max": 80000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-CHAIN-01", "name": "Sên (xích) bị chùng / đứt", "labor_min": 50000, "labor_max": 80000, "parts_min": 80000, "parts_max": 180000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-FILTER-01", "name": "Lọc gió bẩn, bít", "labor_min": 20000, "labor_max": 30000, "parts_min": 20000, "parts_max": 50000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-EXHAUST-01", "name": "Ống xả thủng / lỏng", "labor_min": 50000, "labor_max": 100000, "parts_min": 0, "parts_max": 200000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-COOLANT-01", "name": "Rò rỉ nước làm mát (xe tay ga)", "labor_min": 80000, "labor_max": 150000, "parts_min": 30000, "parts_max": 100000, "cat": "Động cơ xe máy", "safety_notes": "Đừng cố chạy xe khi kim nhiệt độ lên cao"},
    {"fault_code": "MB-ENG-INJECTOR-01", "name": "Kim phun xăng (FI) bẩn / hỏng", "labor_min": 100000, "labor_max": 200000, "parts_min": 150000, "parts_max": 400000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-ENG-STARTER-01", "name": "Đề (motor khởi động) yếu / hỏng", "labor_min": 80000, "labor_max": 150000, "parts_min": 100000, "parts_max": 300000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-TRANS-CLUTCH-01", "name": "Ly hợp (côn số) bị trượt", "labor_min": 150000, "labor_max": 250000, "parts_min": 100000, "parts_max": 250000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-TRANS-GEAR-01", "name": "Số bị cứng / không vào số", "labor_min": 100000, "labor_max": 200000, "parts_min": 50000, "parts_max": 150000, "cat": "Động cơ xe máy"},
    {"fault_code": "MB-TRANS-CVT-01", "name": "Bộ truyền động CVT (xe ga) rung / hú", "labor_min": 200000, "labor_max": 400000, "parts_min": 150000, "parts_max": 400000, "cat": "Động cơ xe máy"},

    # ── Điện xe máy ───────────────────────────────────────────────────────────
    {"fault_code": "MB-BAT-DEAD-01", "name": "Ắc-quy yếu / hết điện", "labor_min": 30000, "labor_max": 50000, "parts_min": 150000, "parts_max": 350000, "cat": "Điện xe máy"},
    {"fault_code": "MB-ELEC-FUSE-01", "name": "Cháy cầu chì", "labor_min": 20000, "labor_max": 40000, "parts_min": 5000, "parts_max": 30000, "cat": "Điện xe máy"},
    {"fault_code": "MB-ELEC-RELAY-01", "name": "Rơ-le khởi động hỏng", "labor_min": 50000, "labor_max": 80000, "parts_min": 30000, "parts_max": 80000, "cat": "Điện xe máy"},
    {"fault_code": "MB-ELEC-LIGHT-01", "name": "Đèn pha / đèn xi-nhan không sáng", "labor_min": 30000, "labor_max": 60000, "parts_min": 20000, "parts_max": 80000, "cat": "Điện xe máy"},
    {"fault_code": "MB-ELEC-CHARGE-01", "name": "Máy phát điện (dynamo) yếu", "labor_min": 80000, "labor_max": 150000, "parts_min": 100000, "parts_max": 250000, "cat": "Điện xe máy"},
    {"fault_code": "MB-ELEC-HORN-01", "name": "Còi không kêu / kêu yếu", "labor_min": 20000, "labor_max": 40000, "parts_min": 30000, "parts_max": 80000, "cat": "Điện xe máy"},
    {"fault_code": "MB-ELEC-SENSOR-01", "name": "Cảm biến oxy / cảm biến ga lỗi (FI)", "labor_min": 80000, "labor_max": 150000, "parts_min": 100000, "parts_max": 300000, "cat": "Điện xe máy"},

    # ── Hệ thống lái & phanh ──────────────────────────────────────────────────
    {"fault_code": "MB-BRAKE-PAD-01", "name": "Bố phanh (má phanh) mòn", "labor_min": 40000, "labor_max": 70000, "parts_min": 30000, "parts_max": 80000, "cat": "Hệ thống lái & phanh xe máy"},
    {"fault_code": "MB-BRAKE-DISC-01", "name": "Đĩa phanh méo / mòn", "labor_min": 80000, "labor_max": 150000, "parts_min": 150000, "parts_max": 350000, "cat": "Hệ thống lái & phanh xe máy"},
    {"fault_code": "MB-BRAKE-FLUID-01", "name": "Dầu phanh thiếu / chảy rò", "labor_min": 50000, "labor_max": 80000, "parts_min": 30000, "parts_max": 60000, "cat": "Hệ thống lái & phanh xe máy", "safety_notes": "Không đi xe khi phanh kém, nguy hiểm tính mạng"},
    {"fault_code": "MB-TIRE-FLAT-01", "name": "Lốp xe bị xì / thủng", "labor_min": 30000, "labor_max": 60000, "parts_min": 0, "parts_max": 30000, "cat": "Hệ thống lái & phanh xe máy"},
    {"fault_code": "MB-TIRE-REPLACE-01", "name": "Thay lốp xe mới", "labor_min": 30000, "labor_max": 60000, "parts_min": 150000, "parts_max": 350000, "cat": "Hệ thống lái & phanh xe máy"},
    {"fault_code": "MB-STEER-BEARING-01", "name": "Vòng bi cổ (bạc đạn tay lái) mòn", "labor_min": 80000, "labor_max": 150000, "parts_min": 50000, "parts_max": 120000, "cat": "Hệ thống lái & phanh xe máy"},
    {"fault_code": "MB-FORK-OIL-01", "name": "Chảy dầu giảm xóc trước", "labor_min": 100000, "labor_max": 200000, "parts_min": 50000, "parts_max": 150000, "cat": "Hệ thống lái & phanh xe máy"},
    {"fault_code": "MB-SHOCK-REAR-01", "name": "Giảm xóc sau yếu / hỏng", "labor_min": 80000, "labor_max": 150000, "parts_min": 150000, "parts_max": 400000, "cat": "Hệ thống lái & phanh xe máy"},

    # ── Thân – vỏ ─────────────────────────────────────────────────────────────
    {"fault_code": "MB-BODY-MIRROR-01", "name": "Gương chiếu hậu vỡ / mất", "labor_min": 20000, "labor_max": 40000, "parts_min": 30000, "parts_max": 80000, "cat": "Thân – vỏ xe máy"},
    {"fault_code": "MB-BODY-KEY-01", "name": "Ổ khóa xe hỏng / mất chìa", "labor_min": 80000, "labor_max": 200000, "parts_min": 80000, "parts_max": 250000, "cat": "Thân – vỏ xe máy"},

    # ── Điều hòa ──────────────────────────────────────────────────────────────
    {"fault_code": "AC-GAS-LOW-01", "name": "Thiếu gas lạnh R32/R410A", "labor_min": 150000, "labor_max": 250000, "parts_min": 150000, "parts_max": 300000, "cat": "Điều hòa không khí", "safety_notes": "Không tự nạp gas, dễ bỏng lạnh và nguy hiểm"},
    {"fault_code": "AC-FILTER-DIRTY-01", "name": "Lọc bụi bẩn, giảm làm lạnh", "labor_min": 50000, "labor_max": 100000, "parts_min": 0, "parts_max": 0, "cat": "Điều hòa không khí"},
    {"fault_code": "AC-COMP-FAIL-01", "name": "Máy nén (compressor) hỏng", "labor_min": 300000, "labor_max": 500000, "parts_min": 1500000, "parts_max": 4000000, "cat": "Điều hòa không khí", "safety_notes": "Không bật điều hòa khi nghi máy nén hỏng"},
    {"fault_code": "AC-FAN-MOTOR-01", "name": "Motor quạt dàn lạnh / nóng yếu", "labor_min": 150000, "labor_max": 250000, "parts_min": 200000, "parts_max": 600000, "cat": "Điều hòa không khí"},
    {"fault_code": "AC-DRAIN-BLOCK-01", "name": "Ống thoát nước bị tắc, chảy vào phòng", "labor_min": 80000, "labor_max": 150000, "parts_min": 0, "parts_max": 30000, "cat": "Điều hòa không khí"},
    {"fault_code": "AC-PCB-FAULT-01", "name": "Bo mạch điều khiển lỗi", "labor_min": 200000, "labor_max": 400000, "parts_min": 400000, "parts_max": 1200000, "cat": "Điều hòa không khí"},
    {"fault_code": "AC-REMOTE-01", "name": "Remote điều khiển hỏng / mất tín hiệu", "labor_min": 30000, "labor_max": 50000, "parts_min": 50000, "parts_max": 150000, "cat": "Điều hòa không khí"},

    # ── Tủ lạnh ───────────────────────────────────────────────────────────────
    {"fault_code": "FRIDGE-GAS-01", "name": "Tủ lạnh không lạnh – thiếu gas", "labor_min": 150000, "labor_max": 250000, "parts_min": 100000, "parts_max": 200000, "cat": "Tủ lạnh"},
    {"fault_code": "FRIDGE-COMP-01", "name": "Máy nén tủ lạnh hỏng", "labor_min": 250000, "labor_max": 400000, "parts_min": 500000, "parts_max": 1500000, "cat": "Tủ lạnh"},
    {"fault_code": "FRIDGE-FROST-01", "name": "Đóng tuyết bất thường – lỗi xả đá", "labor_min": 150000, "labor_max": 250000, "parts_min": 50000, "parts_max": 200000, "cat": "Tủ lạnh"},
    {"fault_code": "FRIDGE-SEAL-01", "name": "Ron cao su cửa hỏng – mất lạnh", "labor_min": 80000, "labor_max": 150000, "parts_min": 80000, "parts_max": 200000, "cat": "Tủ lạnh"},
    {"fault_code": "FRIDGE-THERMOSTAT-01", "name": "Bộ điều nhiệt (thermostat) hỏng", "labor_min": 100000, "labor_max": 200000, "parts_min": 100000, "parts_max": 300000, "cat": "Tủ lạnh"},

    # ── Máy giặt ──────────────────────────────────────────────────────────────
    {"fault_code": "WASH-PUMP-01", "name": "Bơm nước máy giặt hỏng, không xả", "labor_min": 150000, "labor_max": 250000, "parts_min": 150000, "parts_max": 350000, "cat": "Máy giặt"},
    {"fault_code": "WASH-BEARING-01", "name": "Vòng bi lồng giặt mòn, kêu ồn", "labor_min": 200000, "labor_max": 350000, "parts_min": 100000, "parts_max": 250000, "cat": "Máy giặt"},
    {"fault_code": "WASH-VALVE-01", "name": "Van xả nước hỏng – rò rỉ", "labor_min": 100000, "labor_max": 200000, "parts_min": 80000, "parts_max": 200000, "cat": "Máy giặt"},
    {"fault_code": "WASH-MOTOR-01", "name": "Motor máy giặt yếu / cháy", "labor_min": 200000, "labor_max": 400000, "parts_min": 400000, "parts_max": 1000000, "cat": "Máy giặt"},
    {"fault_code": "WASH-PCB-01", "name": "Bo mạch điều khiển máy giặt lỗi", "labor_min": 200000, "labor_max": 400000, "parts_min": 300000, "parts_max": 800000, "cat": "Máy giặt"},

    # ── Điện dân dụng ─────────────────────────────────────────────────────────
    {"fault_code": "ELEC-OUTLET-01", "name": "Ổ cắm điện hỏng / cháy", "labor_min": 50000, "labor_max": 100000, "parts_min": 20000, "parts_max": 80000, "cat": "Điện dân dụng", "safety_notes": "Ngắt cầu dao trước khi kiểm tra, nguy hiểm điện giật"},
    {"fault_code": "ELEC-SWITCH-01", "name": "Công tắc đèn / quạt hỏng", "labor_min": 40000, "labor_max": 80000, "parts_min": 15000, "parts_max": 50000, "cat": "Điện dân dụng", "safety_notes": "Ngắt cầu dao trước khi sửa"},
    {"fault_code": "ELEC-CB-TRIP-01", "name": "Aptomat (CB) nhảy liên tục", "labor_min": 80000, "labor_max": 200000, "parts_min": 50000, "parts_max": 200000, "cat": "Điện dân dụng", "safety_notes": "Có thể do chập điện, không tự ý đóng lại"},
    {"fault_code": "ELEC-LIGHT-01", "name": "Bóng đèn / đèn LED hỏng", "labor_min": 30000, "labor_max": 60000, "parts_min": 30000, "parts_max": 150000, "cat": "Điện dân dụng"},
    {"fault_code": "ELEC-FAN-01", "name": "Quạt điện không quay / chạy yếu", "labor_min": 50000, "labor_max": 120000, "parts_min": 30000, "parts_max": 150000, "cat": "Điện dân dụng"},
    {"fault_code": "ELEC-WATER-HEATER-01", "name": "Bình nóng lạnh hỏng điện trở", "labor_min": 100000, "labor_max": 200000, "parts_min": 80000, "parts_max": 200000, "cat": "Điện dân dụng", "safety_notes": "Ngắt điện bình trước khi kiểm tra"},

    # ── Hệ thống nước ─────────────────────────────────────────────────────────
    {"fault_code": "PLUMB-TAP-01", "name": "Vòi nước bị chảy / rỉ", "labor_min": 50000, "labor_max": 100000, "parts_min": 20000, "parts_max": 100000, "cat": "Hệ thống nước"},
    {"fault_code": "PLUMB-DRAIN-01", "name": "Ống thoát nước bồn rửa / nhà vệ sinh tắc", "labor_min": 80000, "labor_max": 200000, "parts_min": 0, "parts_max": 50000, "cat": "Hệ thống nước"},
    {"fault_code": "PLUMB-TOILET-01", "name": "Toilet bị tắc / rò nước", "labor_min": 80000, "labor_max": 200000, "parts_min": 30000, "parts_max": 150000, "cat": "Hệ thống nước"},
    {"fault_code": "PLUMB-PUMP-01", "name": "Bơm nước không lên / yếu áp", "labor_min": 100000, "labor_max": 200000, "parts_min": 200000, "parts_max": 600000, "cat": "Hệ thống nước"},
    {"fault_code": "PLUMB-PIPE-LEAK-01", "name": "Ống nước âm tường bị vỡ / rò", "labor_min": 200000, "labor_max": 500000, "parts_min": 50000, "parts_max": 200000, "cat": "Hệ thống nước", "safety_notes": "Khóa van tổng ngay để tránh thiệt hại"},

    # ── Gia dụng khác ─────────────────────────────────────────────────────────
    {"fault_code": "APP-RICE-01", "name": "Nồi cơm điện không chín / nấu lâu", "labor_min": 50000, "labor_max": 120000, "parts_min": 30000, "parts_max": 100000, "cat": "Đồ gia dụng khác"},
    {"fault_code": "APP-MICROWAVE-01", "name": "Lò vi sóng không nóng", "labor_min": 100000, "labor_max": 250000, "parts_min": 80000, "parts_max": 300000, "cat": "Đồ gia dụng khác", "safety_notes": "Không tự ý tháo lò vi sóng, tụ điện giữ điện nguy hiểm"},
    {"fault_code": "APP-TV-01", "name": "Tivi không lên hình / mất tiếng", "labor_min": 150000, "labor_max": 300000, "parts_min": 100000, "parts_max": 500000, "cat": "Đồ gia dụng khác"},
]


# 12 technicians scattered around Hue (center: 16.4637, 107.5909)
import math
import random

random.seed(42)


def hue_coords(radius_km: float = 4.5) -> tuple[float, float]:
    r = radius_km * random.uniform(0.2, 1.0)
    theta = random.uniform(0, 2 * math.pi)
    lat = 16.4637 + (r / 111.0) * math.sin(theta)
    lng = 107.5909 + (r / (111.0 * math.cos(math.radians(16.4637)))) * math.cos(theta)
    return round(lat, 6), round(lng, 6)


TECHNICIAN_NAMES = [
    ("Nguyễn Văn An", ["motorbike"], ["Thành phố Huế"]),
    ("Trần Minh Khoa", ["motorbike"], ["Thành phố Huế", "Hương Thủy"]),
    ("Lê Quốc Hùng", ["motorbike", "electrical"], ["Thành phố Huế"]),
    ("Phạm Đình Tú", ["motorbike"], ["Phú Vang", "Thành phố Huế"]),
    ("Hoàng Văn Bình", ["motorbike"], ["Hương Trà", "Thành phố Huế"]),
    ("Đỗ Thanh Long", ["motorbike"], ["Thành phố Huế"]),
    ("Võ Thị Hoa", ["aircon", "appliance"], ["Thành phố Huế"]),
    ("Nguyễn Thị Mai", ["aircon", "refrigerator"], ["Thành phố Huế"]),
    ("Trần Văn Đức", ["electrical", "plumbing"], ["Thành phố Huế"]),
    ("Phan Văn Hải", ["aircon", "washing_machine"], ["Thành phố Huế", "Phú Vang"]),
    ("Lê Thị Thanh", ["appliance", "electrical"], ["Thành phố Huế"]),
    ("Bùi Quang Vinh", ["plumbing", "electrical"], ["Hương Thủy", "Thành phố Huế"]),
]

CUSTOMERS = [
    ("0905111001", "Nguyễn Hữu Nam"),
    ("0905111002", "Trần Thị Linh"),
    ("0905111003", "Lê Minh Tuấn"),
    ("0905111004", "Phạm Thị Hương"),
    ("0905111005", "Hoàng Văn Khải"),
]

ADMIN_PHONE = "0905000001"

QR_LOCATIONS = [
    {
        "id": uid(),
        "name": "KTX Đại học Phú Xuân",
        "location_type": "KTX",
        "address": "Số 9 Nguyễn Trung Ngạn, Phú Hội, Thành phố Huế",
        "lat": 16.4720,
        "lng": 107.5870,
        "owner_contact": "Ban quản lý KTX",
        "code": "PX-KTX-" + secrets.token_urlsafe(4).upper(),
    },
    {
        "id": uid(),
        "name": "Bãi xe Siêu thị BigC Huế",
        "location_type": "Bãi xe",
        "address": "50 Hùng Vương, Phú Hội, Thành phố Huế",
        "lat": 16.4680,
        "lng": 107.5920,
        "owner_contact": "An ninh BigC Huế",
        "code": "BIGC-HUE-" + secrets.token_urlsafe(3).upper(),
    },
    {
        "id": uid(),
        "name": "Khu nhà trọ sinh viên Vỹ Dạ",
        "location_type": "Khu trọ",
        "address": "Đường Bùi Thị Xuân, Vỹ Dạ, Thành phố Huế",
        "lat": 16.4550,
        "lng": 107.6000,
        "owner_contact": "Chủ trọ Nguyễn Văn Tài: 0905999888",
        "code": "VYDA-TRO-" + secrets.token_urlsafe(3).upper(),
    },
]

PLATFORM_CONFIG_DEFAULTS = [
    ("commission_rate", "0.10", "Tỷ lệ hoa hồng mặc định (10%)"),
    ("night_surcharge_amount", "15000", "Phụ thu đêm 22:00-05:00 (VND)"),
    ("night_surcharge_start_hour", "22", "Giờ bắt đầu phụ thu đêm"),
    ("night_surcharge_end_hour", "5", "Giờ kết thúc phụ thu đêm"),
    ("survey_fee", "30000", "Phí khảo sát khi KH từ chối báo giá (VND)"),
    ("travel_fee", "20000", "Phí di chuyển khi hủy sau khi thợ xuất phát (VND)"),
    ("dispatch_radius_km", "3.0", "Bán kính tìm thợ khẩn cấp ban đầu (km)"),
    ("dispatch_expand_radius_km", "5.0", "Bán kính mở rộng sau 90 giây (km)"),
    ("dispatch_timeout_seconds", "60", "Thời gian chờ thợ nhận đơn (giây)"),
    ("dispatch_expand_timeout_seconds", "90", "Thời gian trước khi mở rộng bán kính (giây)"),
    ("ai_diagnose_limit_auth", "10", "Số chẩn đoán AI tối đa/ngày cho user đăng nhập"),
    ("ai_diagnose_limit_anon", "2", "Số chẩn đoán AI tối đa/ngày cho khách vãng lai"),
    ("warranty_days_motorbike", "7", "Số ngày bảo hành cho xe máy"),
    ("warranty_days_home", "30", "Số ngày bảo hành cho thiết bị gia dụng"),
    ("max_assets_per_user", "10", "Số tài sản tối đa mỗi người dùng"),
]


# ── Seed function ─────────────────────────────────────────────────────────────

async def seed(session: AsyncSession) -> None:
    from app.core.encryption import encrypt

    print("🌱 Bắt đầu seed dữ liệu Fix 24/7...")

    # ── Categories ────────────────────────────────────────────────────────────
    for cat in CATEGORIES:
        await session.execute(
            text("""
                INSERT INTO service_categories (id, name, "group", icon, sort_order, is_active, created_at, updated_at)
                VALUES (:id, :name, :group, :icon, :sort_order, true, now(), now())
                ON CONFLICT DO NOTHING
            """),
            {"id": cat["id"], "name": cat["name"], "group": cat["group"],
             "icon": cat["icon"], "sort_order": cat["sort_order"]},
        )
    print(f"  ✅ {len(CATEGORIES)} danh mục dịch vụ")

    # ── Fault catalog ─────────────────────────────────────────────────────────
    for fault in FAULTS:
        cat_id = _cat(fault["cat"])
        await session.execute(
            text("""
                INSERT INTO fault_catalog
                    (id, category_id, fault_code, name, labor_min, labor_max, parts_min, parts_max,
                     safety_notes, is_active, version, created_at, updated_at)
                VALUES
                    (:id, :cat_id, :fault_code, :name, :labor_min, :labor_max, :parts_min, :parts_max,
                     :safety_notes, true, 1, now(), now())
                ON CONFLICT (fault_code) DO NOTHING
            """),
            {
                "id": uid(),
                "cat_id": cat_id,
                "fault_code": fault["fault_code"],
                "name": fault["name"],
                "labor_min": fault["labor_min"],
                "labor_max": fault["labor_max"],
                "parts_min": fault.get("parts_min", 0),
                "parts_max": fault.get("parts_max", 0),
                "safety_notes": fault.get("safety_notes"),
            },
        )
    print(f"  ✅ {len(FAULTS)} lỗi trong bảng giá chuẩn (fault_catalog)")

    # ── Admin user ────────────────────────────────────────────────────────────
    admin_id = uid()
    await session.execute(
        text("""
            INSERT INTO users (id, phone, name, role, status, terms_accepted_at, created_at, updated_at)
            VALUES (:id, :phone, :name, 'admin', 'active', now(), now(), now())
            ON CONFLICT (phone) DO NOTHING
        """),
        {"id": admin_id, "phone": ADMIN_PHONE, "name": "Quản trị viên Fix 24/7"},
    )
    # Fetch actual admin ID (might differ if already existed)
    result = await session.execute(text("SELECT id FROM users WHERE phone = :p"), {"p": ADMIN_PHONE})
    admin_id = result.scalar_one()
    print(f"  ✅ Admin: {ADMIN_PHONE} (ID: {admin_id[:8]}...)")

    # ── Customer users ────────────────────────────────────────────────────────
    for phone, name in CUSTOMERS:
        await session.execute(
            text("""
                INSERT INTO users (id, phone, name, role, status, terms_accepted_at, created_at, updated_at)
                VALUES (:id, :phone, :name, 'customer', 'active', now(), now(), now())
                ON CONFLICT (phone) DO NOTHING
            """),
            {"id": uid(), "phone": phone, "name": name},
        )
    print(f"  ✅ {len(CUSTOMERS)} khách hàng demo")

    # ── Technician users ──────────────────────────────────────────────────────
    tech_phones = [f"0905{200 + i:06d}" for i in range(len(TECHNICIAN_NAMES))]
    for i, ((name, specialties, areas), phone) in enumerate(zip(TECHNICIAN_NAMES, tech_phones)):
        tech_user_id = uid()
        lat, lng = hue_coords()

        # Insert user
        await session.execute(
            text("""
                INSERT INTO users (id, phone, name, role, status, terms_accepted_at, created_at, updated_at)
                VALUES (:id, :phone, :name, 'technician', 'active', now(), now(), now())
                ON CONFLICT (phone) DO NOTHING
            """),
            {"id": tech_user_id, "phone": phone, "name": name},
        )

        # Fetch actual user ID
        result = await session.execute(text("SELECT id FROM users WHERE phone = :p"), {"p": phone})
        actual_user_id = result.scalar_one()

        # Fake encrypted CCCD
        fake_cccd = f"0{34 + i:02d}0{i:08d}"
        encrypted_cccd = encrypt(fake_cccd)

        # Insert technician profile
        await session.execute(
            text("""
                INSERT INTO technician_profiles
                    (id, user_id, id_number_encrypted, specialties, service_areas,
                     approval_status, approved_at, approved_by_id,
                     is_online, rating_avg, rating_count,
                     total_earned, total_commission, debt_amount, created_at, updated_at)
                VALUES
                    (:id, :user_id, :id_num_enc, :specialties, :service_areas,
                     'approved', now(), :admin_id,
                     :is_online, :rating_avg, :rating_count,
                     :total_earned, :total_commission, 0, now(), now())
                ON CONFLICT (user_id) DO NOTHING
            """),
            {
                "id": uid(),
                "user_id": actual_user_id,
                "id_num_enc": encrypted_cccd,
                "specialties": specialties,
                "service_areas": areas,
                "admin_id": admin_id,
                "is_online": (i % 3 != 0),  # 8 out of 12 online
                "rating_avg": round(3.8 + random.uniform(0, 1.2), 2),
                "rating_count": random.randint(5, 50),
                "total_earned": random.randint(500000, 5000000),
                "total_commission": random.randint(50000, 500000),
            },
        )

        # Set PostGIS location
        await session.execute(
            text("""
                UPDATE technician_profiles
                SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    location_updated_at = now()
                WHERE user_id = :user_id
            """),
            {"lng": lng, "lat": lat, "user_id": actual_user_id},
        )

    print(f"  ✅ {len(TECHNICIAN_NAMES)} thợ kỹ thuật (đã duyệt, có vị trí GPS quanh Huế)")

    # ── QR Locations ──────────────────────────────────────────────────────────
    for qr in QR_LOCATIONS:
        await session.execute(
            text("""
                INSERT INTO qr_locations
                    (id, name, location_type, address, lat, lng, owner_contact, code,
                     scan_count, order_count, is_active, created_by_id, created_at, updated_at)
                VALUES
                    (:id, :name, :type, :address, :lat, :lng, :contact, :code,
                     0, 0, true, :admin_id, now(), now())
                ON CONFLICT (code) DO NOTHING
            """),
            {
                "id": qr["id"],
                "name": qr["name"],
                "type": qr["location_type"],
                "address": qr["address"],
                "lat": qr["lat"],
                "lng": qr["lng"],
                "contact": qr["owner_contact"],
                "code": qr["code"],
                "admin_id": admin_id,
            },
        )
    print(f"  ✅ {len(QR_LOCATIONS)} QR locations")

    # ── Platform Config ───────────────────────────────────────────────────────
    for key, value, description in PLATFORM_CONFIG_DEFAULTS:
        await session.execute(
            text("""
                INSERT INTO platform_config (key, value, description, updated_at)
                VALUES (:key, :value, :desc, now())
                ON CONFLICT (key) DO NOTHING
            """),
            {"key": key, "value": value, "desc": description},
        )
    print(f"  ✅ {len(PLATFORM_CONFIG_DEFAULTS)} platform config entries")

    await session.commit()
    print("\n🎉 Seed hoàn thành!")
    print("\n📋 Tài khoản demo:")
    print(f"  Admin:    {ADMIN_PHONE}")
    for phone, name in CUSTOMERS:
        print(f"  Khách:    {phone} ({name})")
    for i, ((name, _, _), phone) in enumerate(zip(TECHNICIAN_NAMES, tech_phones)):
        print(f"  Thợ {i+1:02d}:   {phone} ({name})")
    print("\n  → Tất cả dùng OTP (mock in ra console khi đăng nhập)")


async def main() -> None:
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
