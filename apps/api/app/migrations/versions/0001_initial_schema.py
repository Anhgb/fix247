"""Initial schema – all tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-23

SRS §8: UUID PKs, timestamps, GIST index on technician location,
constraints, soft delete on users/assets.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("phone", sa.String(15), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=True),
        sa.Column(
            "role",
            sa.Enum("customer", "technician", "admin", name="userrole"),
            nullable=False,
            server_default="customer",
        ),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('active','blocked','pending')", name="ck_users_status"),
    )
    op.create_index("ix_users_phone", "users", ["phone"])

    # ── service_categories ────────────────────────────────────────────────────
    op.create_table(
        "service_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column(
            "group",
            sa.Enum("motorbike", "home", name="servicegroup"),
            nullable=False,
        ),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # ── fault_catalog ─────────────────────────────────────────────────────────
    op.create_table(
        "fault_catalog",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("service_categories.id"),
            nullable=False,
        ),
        sa.Column("fault_code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("labor_min", sa.Integer, nullable=False),
        sa.Column("labor_max", sa.Integer, nullable=False),
        sa.Column("parts_min", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parts_max", sa.Integer, nullable=False, server_default="0"),
        sa.Column("safety_notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("labor_min >= 0", name="ck_fault_labor_min"),
        sa.CheckConstraint("labor_max >= labor_min", name="ck_fault_labor_max"),
        sa.CheckConstraint("parts_max >= parts_min", name="ck_fault_parts"),
    )
    op.create_index("ix_fault_catalog_code", "fault_catalog", ["fault_code"])

    # ── qr_locations ──────────────────────────────────────────────────────────
    op.create_table(
        "qr_locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location_type", sa.String(50), nullable=True),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("owner_contact", sa.String(200), nullable=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("scan_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("order_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(code) >= 10", name="ck_qr_code_length"),
    )
    op.create_index("ix_qr_locations_code", "qr_locations", ["code"])

    # ── technician_profiles ───────────────────────────────────────────────────
    op.create_table(
        "technician_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("id_number_encrypted", sa.Text, nullable=False),
        sa.Column("portrait_url", sa.String(500), nullable=True),
        sa.Column(
            "certificate_urls",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "specialties",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "service_areas",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "approval_status",
            sa.Enum("pending", "approved", "rejected", "suspended", name="approvalstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("approval_note", sa.Text, nullable=True),
        sa.Column("approved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_online", sa.Boolean, nullable=False, server_default="false"),
        # PostGIS geography point – GIST index below
        sa.Column("location", sa.Text, nullable=True),   # stored as WKT; PostGIS handles it
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("rating_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_commission", sa.Integer, nullable=False, server_default="0"),
        sa.Column("debt_amount", sa.Integer, nullable=False, server_default="0"),
        sa.Column("debt_overdue_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    # Add PostGIS geography column separately
    op.execute(
        """
        ALTER TABLE technician_profiles
        DROP COLUMN IF EXISTS location;
        """
    )
    op.execute(
        """
        ALTER TABLE technician_profiles
        ADD COLUMN location geography(POINT, 4326);
        """
    )
    # GIST index on location (SRS §8)
    op.execute(
        """
        CREATE INDEX ix_tech_profile_location_gist
        ON technician_profiles USING GIST (location);
        """
    )

    # ── assets ────────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_type",
            sa.Enum("vehicle", "appliance", name="assettype"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("plate_or_serial", sa.String(50), nullable=True),
        sa.Column("location_label", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("owner_id", "plate_or_serial", name="uq_asset_owner_serial"),
    )

    # ── diagnoses ─────────────────────────────────────────────────────────────
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("service_categories.id"),
            nullable=True,
        ),
        sa.Column(
            "media_urls",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("ai_output", sa.JSON, nullable=True),
        sa.Column("ai_provider", sa.String(50), nullable=True),
        sa.Column("confidence_max", sa.Numeric(4, 3), nullable=True),
        sa.Column("has_safety_warnings", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verified_label", sa.String(20), nullable=True),
        sa.Column("verified_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "qr_location_id",
            sa.String(36),
            sa.ForeignKey("qr_locations.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_diagnoses_input_hash", "diagnoses", ["input_hash"])
    op.create_index("ix_diagnoses_user_id", "diagnoses", ["user_id"])

    # ── orders ────────────────────────────────────────────────────────────────
    order_statuses = (
        "CREATED,SEARCHING,SCHEDULED,ACCEPTED,ON_THE_WAY,SURVEYING,"
        "QUOTE_PENDING,QUOTE_REJECTED,IN_REPAIR,AWAITING_CONFIRM,"
        "COMPLETED,DISPUTED,NO_TECH,WARRANTY,CLOSED,CANCELLED,REFUNDED"
    ).split(",")
    status_check = "status IN (" + ", ".join(f"'{s}'" for s in order_statuses) + ")"

    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("technician_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("diagnosis_id", sa.String(36), sa.ForeignKey("diagnoses.id"), nullable=True),
        sa.Column(
            "qr_location_id",
            sa.String(36),
            sa.ForeignKey("qr_locations.id"),
            nullable=True,
        ),
        sa.Column(
            "mode", sa.Enum("emergency", "scheduled", name="ordermode"), nullable=False
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="CREATED"),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("est_min", sa.Integer, nullable=True),
        sa.Column("est_max", sa.Integer, nullable=True),
        sa.Column("night_surcharge", sa.Integer, nullable=False, server_default="0"),
        sa.Column("survey_fee", sa.Integer, nullable=False, server_default="0"),
        sa.Column("final_quote", sa.Integer, nullable=True),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("commission_amount", sa.Integer, nullable=True),
        sa.Column("total", sa.Integer, nullable=True),
        sa.Column("customer_note", sa.Text, nullable=True),
        sa.Column("cancel_reason", sa.Text, nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(status_check, name="ck_orders_status"),
        sa.CheckConstraint(
            "final_quote IS NULL OR final_quote >= 0", name="ck_orders_final_quote"
        ),
    )
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    # ── order_items ───────────────────────────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_type", sa.Enum("labor", "part", name="itemtype"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("qty", sa.Integer, nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Integer, nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("qty > 0", name="ck_order_item_qty"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_item_price"),
    )

    # ── order_events ──────────────────────────────────────────────────────────
    op.create_table(
        "order_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column(
            "method",
            sa.Enum("cash", "vietqr", "momo", "vnpay", name="paymentmethod"),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("commission_amount", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", "failed", "refunded", name="paymentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("provider_ref", sa.String(200), nullable=True, unique=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_payments_provider_ref", "payments", ["provider_ref"])

    # ── reviews ───────────────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("from_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("to_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("from_role", sa.String(20), nullable=False),
        sa.Column("stars", sa.Integer, nullable=False),
        sa.Column(
            "tags", postgresql.ARRAY(sa.String), server_default="{}", nullable=False
        ),
        sa.Column("comment", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("order_id", "from_user_id", name="uq_reviews_order_reviewer"),
        sa.CheckConstraint("stars BETWEEN 1 AND 5", name="ck_reviews_stars"),
    )

    # ── warranty_claims ───────────────────────────────────────────────────────
    op.create_table(
        "warranty_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("opened_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column(
            "media_urls",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "accepted", "rejected", "completed", name="warrantystatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # ── maintenance_logs ──────────────────────────────────────────────────────
    op.create_table(
        "maintenance_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("parts_replaced", sa.JSON, nullable=True),
        sa.Column("labor_cost", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parts_cost", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Integer, nullable=False, server_default="0"),
        sa.Column("technician_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "photo_before_urls",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "photo_after_urls",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_maintenance_logs_asset_performed",
        "maintenance_logs",
        ["asset_id", "performed_at"],
    )

    # ── reminders ─────────────────────────────────────────────────────────────
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("rule", sa.String(200), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("push", "sms", "in_app", name="notificationchannel"),
            nullable=False,
            server_default="push",
        ),
        sa.Column("is_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # ── disputes ──────────────────────────────────────────────────────────────
    op.create_table(
        "disputes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("opened_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "resolved", "closed", name="disputestatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column(
            "channel",
            sa.Enum("push", "sms", "in_app", name="notificationchannel"),
            nullable=False,
            server_default="in_app",
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])

    # ── platform_config ───────────────────────────────────────────────────────
    op.create_table(
        "platform_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )

    # ── admin_action_logs ─────────────────────────────────────────────────────
    op.create_table(
        "admin_action_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("admin_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(50), nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_admin_logs_admin_created", "admin_action_logs", ["admin_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("admin_action_logs")
    op.drop_table("platform_config")
    op.drop_table("notifications")
    op.drop_table("disputes")
    op.drop_table("reminders")
    op.drop_table("maintenance_logs")
    op.drop_table("warranty_claims")
    op.drop_table("reviews")
    op.drop_table("payments")
    op.drop_table("order_events")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("diagnoses")
    op.drop_table("assets")
    op.drop_table("technician_profiles")
    op.drop_table("qr_locations")
    op.drop_table("fault_catalog")
    op.drop_table("service_categories")
    op.drop_table("users")

    # Drop enums
    for enum_name in [
        "userrole", "servicegroup", "assettype", "ordermode",
        "itemtype", "paymentmethod", "paymentstatus", "approvalstatus",
        "warrantystatus", "disputestatus", "notificationchannel",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    op.execute("DROP EXTENSION IF EXISTS postgis")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
