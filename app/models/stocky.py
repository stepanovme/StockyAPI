from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid_pk() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )


class RoleDB(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    users: Mapped[list["UserDB"]] = relationship(back_populates="role")


class UserDB(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    surname: Mapped[str] = mapped_column(String(255), nullable=False)
    patronymic: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    login: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    role: Mapped[RoleDB] = relationship(back_populates="users")


class LocationDB(TimestampMixin, Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ComponentTemplateDB(TimestampMixin, Base):
    __tablename__ = "component_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    items: Mapped[list["ComponentTemplateItemDB"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ComponentTemplateItemDB.sort_order",
    )


class ComponentTemplateItemDB(TimestampMixin, Base):
    __tablename__ = "component_template_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    template_id: Mapped[str] = mapped_column(
        ForeignKey("component_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("1.00"))
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    template: Mapped[ComponentTemplateDB] = relationship(back_populates="items")


class ItemDB(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    inventory_number: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    responsible_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    holder_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), nullable=False)
    storage_box: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    operational_status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("component_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    responsible_user: Mapped[UserDB] = relationship(foreign_keys=[responsible_user_id])
    holder_user: Mapped[UserDB] = relationship(foreign_keys=[holder_user_id])
    location: Mapped[LocationDB] = relationship()
    template: Mapped[ComponentTemplateDB | None] = relationship()
    photos: Mapped[list["ItemPhotoDB"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ItemPhotoDB.sort_order",
        foreign_keys="ItemPhotoDB.item_id",
    )
    components: Mapped[list["ItemComponentDB"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        foreign_keys="ItemComponentDB.parent_item_id",
    )
    history_entries: Mapped[list["ItemHistoryDB"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="desc(ItemHistoryDB.created_at)",
        foreign_keys="ItemHistoryDB.item_id",
    )


class ItemPhotoDB(Base):
    __tablename__ = "item_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="image/jpeg")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    item: Mapped[ItemDB] = relationship(back_populates="photos")


class ItemComponentDB(Base):
    __tablename__ = "item_components"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    parent_item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("1.00"))
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    linked_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    item: Mapped[ItemDB] = relationship(back_populates="components", foreign_keys=[parent_item_id])
    linked_item: Mapped[ItemDB | None] = relationship(foreign_keys=[linked_item_id])


class ItemHistoryDB(Base):
    __tablename__ = "item_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    item: Mapped[ItemDB] = relationship(back_populates="history_entries")
    person: Mapped[UserDB | None] = relationship()


class TransferDB(Base):
    __tablename__ = "transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    from_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    to_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_request: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    item: Mapped[ItemDB] = relationship()
    from_user: Mapped[UserDB] = relationship(foreign_keys=[from_user_id])
    to_user: Mapped[UserDB] = relationship(foreign_keys=[to_user_id])


class WriteOffDB(Base):
    __tablename__ = "write_offs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    person_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    item: Mapped[ItemDB] = relationship()
    person: Mapped[UserDB] = relationship()


class RepairDB(Base):
    __tablename__ = "repairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    service_provider: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expected_return_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    item: Mapped[ItemDB] = relationship()
    created_by_user: Mapped[UserDB] = relationship(foreign_keys=[created_by_user_id])


class RentalDB(Base):
    __tablename__ = "rentals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    renter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    renter_contact: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_period: Mapped[str] = mapped_column(String(32), nullable=False, default="fixed")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    item: Mapped[ItemDB] = relationship()
    created_by_user: Mapped[UserDB] = relationship(foreign_keys=[created_by_user_id])


class DeviceTokenDB(Base):
    __tablename__ = "device_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="ios")
    device_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    user: Mapped[UserDB] = relationship()


class NotificationDB(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[UserDB] = relationship()
