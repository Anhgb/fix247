"""
SQLAlchemy 2 ORM Models – Fix 24/7
All tables per PRD §12 + SRS §8.
UUID v7 PKs, created_at/updated_at on every table.
Soft delete on users and assets only (SRS §8).
"""
import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import foreign, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    customer = "customer"
    technician = "technician"
    admin = "admin"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"


class OrderStatus(str, enum.Enum):
    # SRS §6 – state machine
    CREATED = "CREATED"
    SEARCHING = "SEARCHING"
    SCHEDULED = "SCHEDULED"
    ACCEPTED = "ACCEPTED"
    ON_THE_WAY = "ON_THE_WAY"
    SURVEYING = "SURVEYING"
    QUOTE_PENDING = "QUOTE_PENDING"
    QUOTE_REJECTED = "QUOTE_REJECTED"
    IN_REPAIR = "IN_REPAIR"
    AWAITING_CONFIRM = "AWAITING_CONFIRM"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"
    NO_TECH = "NO_TECH"
    WARRANTY = "WARRANTY"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class OrderMode(str, enum.Enum):
    emergency = "emergency"
    scheduled = "scheduled"


class ItemType(str, enum.Enum):
    labor = "labor"
    part = "part"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    vietqr = "vietqr"
    momo = "momo"
    vnpay = "vnpay"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class AssetType(str, enum.Enum):
    vehicle = "vehicle"
    appliance = "appliance"


class ServiceGroup(str, enum.Enum):
    motorbike = "motorbike"
    home = "home"


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DisputeStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"
    closed = "closed"


class WarrantyStatus(str, enum.Enum):
    open = "open"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class NotificationChannel(str, enum.Enum):
    push = "push"
    sms = "sms"
    in_app = "in_app"


# ── Helpers ───────────────────────────────────────────────────────────────────

def uuid7() -> str:
    """Generate UUID v7 (monotonic). Falls back to UUID v4 if uuid6 not installed."""
    try:
        import uuid6
        return str(uuid6.uuid7())
    except ImportError:
        return str(uuid.uuid4())


def _uuid_default() -> str:
    return uuid7()


# ── Mixins ────────────────────────────────────────────────────────────────────

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── Tables ────────────────────────────────────────────────────────────────────

class User(TimestampMixin, Base):
    """
    FR-AUTH-01..04: Users table.
    Soft delete via deleted_at (SRS §8).
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    avatar_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)  # FR-AUTH-04
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft delete

    # Relationships
    technician_profile = relationship("TechnicianProfile", back_populates="user", uselist=False, foreign_keys="TechnicianProfile.user_id")
    assets = relationship("Asset", back_populates="owner")
    orders_as_customer = relationship("Order", foreign_keys="Order.customer_id", back_populates="customer")
    notifications = relationship("Notification", back_populates="user")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'blocked', 'pending')", name="ck_users_status"),
    )


class TechnicianProfile(TimestampMixin, Base):
    """
    FR-TECH-01/02/03: Technician registration and verification.
    CCCD stored encrypted (NFR-04, D-10).
    GIST index on location (SRS §8).
    """
    __tablename__ = "technician_profiles"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Encrypted CCCD – NFR-04
    id_number_encrypted = Column(Text, nullable=False)

    portrait_url = Column(String(500), nullable=True)
    certificate_urls = Column(ARRAY(String), server_default="{}", nullable=False)

    # Specialties: ["motorbike", "aircon", "electrical", "plumbing", "appliance"]
    specialties = Column(ARRAY(String), server_default="{}", nullable=False)
    service_areas = Column(ARRAY(String), server_default="{}", nullable=False)

    approval_status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.pending)
    approval_note = Column(Text, nullable=True)
    approved_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    is_online = Column(Boolean, nullable=False, default=False)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)  # PostGIS
    location_updated_at = Column(DateTime(timezone=True), nullable=True)

    rating_avg = Column(Numeric(3, 2), nullable=False, default=0)
    rating_count = Column(Integer, nullable=False, default=0)

    # Wallet
    total_earned = Column(Integer, nullable=False, default=0)  # VND
    total_commission = Column(Integer, nullable=False, default=0)  # VND
    debt_amount = Column(Integer, nullable=False, default=0)  # VND
    debt_overdue_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="technician_profile")
    orders = relationship("Order", primaryjoin="TechnicianProfile.user_id == foreign(Order.technician_id)", back_populates="technician")

    __table_args__ = (
        # GIST index on location for PostGIS radius queries (SRS §8)
        Index("ix_tech_profile_location_gist", "location", postgresql_using="gist"),
    )


class Asset(TimestampMixin, Base):
    """
    FR-HEALTH-01: Customer vehicle/appliance assets.
    Soft delete (SRS §8). Max 10/user enforced in service layer.
    """
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    plate_or_serial = Column(String(50), nullable=True)
    location_label = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft delete

    # Relationships
    owner = relationship("User", back_populates="assets")
    maintenance_logs = relationship("MaintenanceLog", back_populates="asset")
    reminders = relationship("Reminder", back_populates="asset")
    orders = relationship("Order", back_populates="asset")

    __table_args__ = (
        UniqueConstraint("owner_id", "plate_or_serial", name="uq_asset_owner_serial"),
    )


class ServiceCategory(TimestampMixin, Base):
    """
    DIAG-1: Service categories (xe máy / gia dụng groups).
    """
    __tablename__ = "service_categories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    name = Column(String(150), nullable=False)
    group = Column(Enum(ServiceGroup), nullable=False)
    icon = Column(String(100), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    fault_catalog = relationship("FaultCatalog", back_populates="category")


class FaultCatalog(TimestampMixin, Base):
    """
    FR-DIAG-05: Price lookup table. Prices ALWAYS come from here, never AI output.
    AGENTS.md: AI price rule.
    """
    __tablename__ = "fault_catalog"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    category_id = Column(UUID(as_uuid=False), ForeignKey("service_categories.id"), nullable=False)
    fault_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    labor_min = Column(Integer, nullable=False)   # VND – D-07: integer
    labor_max = Column(Integer, nullable=False)
    parts_min = Column(Integer, nullable=False, default=0)
    parts_max = Column(Integer, nullable=False, default=0)
    safety_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)  # FR-ADM-02

    category = relationship("ServiceCategory", back_populates="fault_catalog")

    __table_args__ = (
        CheckConstraint("labor_min >= 0", name="ck_fault_labor_min"),
        CheckConstraint("labor_max >= labor_min", name="ck_fault_labor_max"),
        CheckConstraint("parts_max >= parts_min", name="ck_fault_parts"),
    )


class Diagnosis(TimestampMixin, Base):
    """
    UC-02: AI diagnosis record.
    """
    __tablename__ = "diagnoses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)  # nullable for anonymous diagnosis (FR-DIAG-07)
    asset_id = Column(UUID(as_uuid=False), ForeignKey("assets.id"), nullable=True)
    category_id = Column(UUID(as_uuid=False), ForeignKey("service_categories.id"), nullable=True)

    # Input references
    media_urls = Column(ARRAY(String), server_default="{}", nullable=False)
    description = Column(Text, nullable=True)
    input_hash = Column(String(64), nullable=True, index=True)  # FR-DIAG-08: cache key

    # AI output (JSON validated against schema in SRS §7.2)
    ai_output = Column(JSON, nullable=True)
    ai_provider = Column(String(50), nullable=True)  # "mock" | "gemini" | "openai"
    confidence_max = Column(Numeric(4, 3), nullable=True)  # highest candidate confidence
    has_safety_warnings = Column(Boolean, nullable=False, default=False)

    # After repair: tech labels accuracy (FR-DIAG-09)
    verified_label = Column(String(20), nullable=True)  # "correct" | "partial" | "wrong"
    verified_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # QR location context
    qr_location_id = Column(UUID(as_uuid=False), ForeignKey("qr_locations.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class Order(TimestampMixin, Base):
    """
    SRS §6: Order state machine. All status values enforced via CHECK constraint.
    order_events written on every transition (AGENTS.md rule).
    """
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    customer_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    technician_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    asset_id = Column(UUID(as_uuid=False), ForeignKey("assets.id"), nullable=True)
    diagnosis_id = Column(UUID(as_uuid=False), ForeignKey("diagnoses.id"), nullable=True)
    qr_location_id = Column(UUID(as_uuid=False), ForeignKey("qr_locations.id"), nullable=True)

    mode = Column(Enum(OrderMode), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.CREATED)

    # Location
    address = Column(Text, nullable=False)
    lat = Column(Numeric(10, 7), nullable=True)
    lng = Column(Numeric(10, 7), nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    # Pricing (all VND integers – D-07)
    est_min = Column(Integer, nullable=True)
    est_max = Column(Integer, nullable=True)
    night_surcharge = Column(Integer, nullable=False, default=0)    # BR-04
    survey_fee = Column(Integer, nullable=False, default=0)         # BR-07
    final_quote = Column(Integer, nullable=True)
    commission_rate = Column(Numeric(5, 4), nullable=True)          # e.g. 0.1000
    commission_amount = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)

    # Notes
    customer_note = Column(Text, nullable=True)
    cancel_reason = Column(Text, nullable=True)

    # Timestamps
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="orders_as_customer")
    technician = relationship("TechnicianProfile", primaryjoin="foreign(Order.technician_id) == TechnicianProfile.user_id", back_populates="orders")
    asset = relationship("Asset", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)
    review_by_customer = relationship(
        "Review",
        primaryjoin="and_(Order.id==Review.order_id, Review.from_role=='customer')",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in OrderStatus)})",
            name="ck_orders_status",
        ),
        CheckConstraint("final_quote IS NULL OR final_quote >= 0", name="ck_orders_final_quote"),
        Index("ix_orders_status_created", "status", "created_at"),
    )


class OrderItem(TimestampMixin, Base):
    """Order line items: labor or parts. BR-10: parts >100k need name + photo."""
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(Enum(ItemType), nullable=False)
    name = Column(String(200), nullable=False)
    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False)   # VND
    photo_url = Column(String(500), nullable=True)  # BR-10

    order = relationship("Order", back_populates="items")

    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_order_item_qty"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_price"),
    )


class OrderEvent(Base):
    """
    SRS §6: Every state transition writes one OrderEvent.
    AGENTS.md: Order status changes only go through one state-machine function.
    """
    __tablename__ = "order_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(Enum(OrderStatus), nullable=True)
    to_status = Column(Enum(OrderStatus), nullable=False)
    actor_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)  # NULL = system
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="events")

    __table_args__ = (
        Index("ix_order_events_order_id", "order_id"),
    )


class Payment(TimestampMixin, Base):
    """
    FR-PAY-01..05: Payment record per order.
    Webhook idempotency on provider_ref (FR-PAY-02).
    """
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id"), unique=True, nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Integer, nullable=False)  # VND
    commission_amount = Column(Integer, nullable=False, default=0)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    provider_ref = Column(String(200), unique=True, nullable=True, index=True)  # idempotency key
    paid_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="payment")


class Review(TimestampMixin, Base):
    """
    FR-RATE-01..03: Bidirectional reviews.
    UNIQUE per (order_id, from_role) – SRS §8.
    """
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id"), nullable=False)
    from_user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    to_user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    from_role = Column(String(20), nullable=False)  # "customer" | "technician"
    stars = Column(Integer, nullable=False)
    tags = Column(ARRAY(String), server_default="{}", nullable=False)
    comment = Column(String(500), nullable=True)   # FR-RATE-01: ≤500 ký tự

    __table_args__ = (
        UniqueConstraint("order_id", "from_user_id", name="uq_reviews_order_reviewer"),
        CheckConstraint("stars BETWEEN 1 AND 5", name="ck_reviews_stars"),
    )


class WarrantyClaim(TimestampMixin, Base):
    """FR-PAY-06: Warranty claims."""
    __tablename__ = "warranty_claims"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id"), nullable=False)
    opened_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    media_urls = Column(ARRAY(String), server_default="{}", nullable=False)
    status = Column(Enum(WarrantyStatus), nullable=False, default=WarrantyStatus.open)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)


class MaintenanceLog(TimestampMixin, Base):
    """
    FR-HEALTH-02: Auto-created when order reaches COMPLETED.
    Index on (asset_id, performed_at) per SRS §8.
    """
    __tablename__ = "maintenance_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    asset_id = Column(UUID(as_uuid=False), ForeignKey("assets.id"), nullable=False)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id"), nullable=True)
    summary = Column(Text, nullable=False)
    parts_replaced = Column(JSON, nullable=True)    # [{name, qty, unit_price}]
    labor_cost = Column(Integer, nullable=False, default=0)
    parts_cost = Column(Integer, nullable=False, default=0)
    total_cost = Column(Integer, nullable=False, default=0)
    technician_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    photo_before_urls = Column(ARRAY(String), server_default="{}", nullable=False)
    photo_after_urls = Column(ARRAY(String), server_default="{}", nullable=False)
    performed_at = Column(DateTime(timezone=True), nullable=False)

    asset = relationship("Asset", back_populates="maintenance_logs")

    __table_args__ = (
        Index("ix_maintenance_logs_asset_performed", "asset_id", "performed_at"),
    )


class Reminder(TimestampMixin, Base):
    """FR-HEALTH-03: Maintenance reminders per asset."""
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    asset_id = Column(UUID(as_uuid=False), ForeignKey("assets.id"), nullable=False)
    rule = Column(String(200), nullable=False)       # e.g. "Thay nhớt mỗi 3 tháng"
    next_due_at = Column(DateTime(timezone=True), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False, default=NotificationChannel.push)
    is_sent = Column(Boolean, nullable=False, default=False)

    asset = relationship("Asset", back_populates="reminders")


class QRLocation(TimestampMixin, Base):
    """
    FR-QR-01/02: QR location codes.
    Code ≥10 random chars (A-03).
    """
    __tablename__ = "qr_locations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    name = Column(String(200), nullable=False)
    location_type = Column(String(50), nullable=True)   # KTX, bãi xe, khu trọ...
    address = Column(Text, nullable=False)
    lat = Column(Numeric(10, 7), nullable=True)
    lng = Column(Numeric(10, 7), nullable=True)
    owner_contact = Column(String(200), nullable=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # ≥10 chars
    scan_count = Column(Integer, nullable=False, default=0)
    order_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)


class Dispute(TimestampMixin, Base):
    """ADM-3: Dispute management."""
    __tablename__ = "disputes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    order_id = Column(UUID(as_uuid=False), ForeignKey("orders.id"), nullable=False)
    opened_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(DisputeStatus), nullable=False, default=DisputeStatus.open)
    resolution = Column(Text, nullable=True)
    resolved_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Notification(TimestampMixin, Base):
    """Push / SMS / in-app notifications per user."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(50), nullable=False)  # order_status, reminder, etc.
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    channel = Column(Enum(NotificationChannel), nullable=False, default=NotificationChannel.in_app)
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
    )


class PlatformConfig(Base):
    """
    FR-ADM-04: Configurable platform settings.
    A-06: default fees stored here.
    """
    __tablename__ = "platform_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)


class AdminActionLog(Base):
    """Audit trail for all admin actions (FR-ADM-01)."""
    __tablename__ = "admin_action_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    admin_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(50), nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_admin_logs_admin_created", "admin_id", "created_at"),
    )
