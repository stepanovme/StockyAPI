from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UnitType = Literal["шт", "м", "см", "кг", "г", "л", "мл", "компл.", "кор.", "рул.", "пар", "ед."]
ItemStatus = Literal["active", "written_off"]
OperationalStatus = Literal["available", "broken", "under_repair", "rented"]
WriteOffReason = Literal["broken", "used", "lost", "expired", "other"]
RepairStatus = Literal["in_progress", "completed", "cancelled"]
RentalStatus = Literal["active", "completed", "overdue", "cancelled"]
RentalPricePeriod = Literal["hour", "day", "week", "month", "fixed"]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApiEnvelope(BaseModel):
    success: bool = True
    data: object


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorDetail


class RoleCreate(BaseModel):
    name: str = Field(min_length=1)


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1)


class RoleRead(OrmModel):
    id: int
    name: str


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    surname: str = Field(min_length=1)
    patronymic: str = ""
    login: str = Field(min_length=3)
    password: str = Field(min_length=6)
    role_id: int


class RegisterRequest(UserCreate):
    pass


class LoginRequest(BaseModel):
    login: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: object


class DeviceTokenCreate(BaseModel):
    device_token: str = Field(min_length=10)
    platform: str = "ios"
    device_name: str = ""


class DeviceTokenRead(OrmModel):
    id: str
    user_id: str
    platform: str
    device_token: str
    device_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NotificationRead(OrmModel):
    id: str
    user_id: str
    event_type: str
    title: str
    body: str
    payload_json: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class UserUpdate(BaseModel):
    name: str | None = None
    surname: str | None = None
    patronymic: str | None = None
    login: str | None = Field(default=None, min_length=3)
    password: str | None = Field(default=None, min_length=6)
    role_id: int | None = None
    is_active: bool | None = None


class UserRead(OrmModel):
    id: str
    name: str
    surname: str
    patronymic: str
    login: str
    role_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserBrief(OrmModel):
    id: str
    name: str
    surname: str
    patronymic: str
    login: str
    role_id: int


class AuthUserRead(UserRead):
    full_name: str
    role: RoleRead | None = None


class LocationCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


class LocationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class LocationRead(OrmModel):
    id: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LocationBrief(OrmModel):
    id: str
    name: str
    description: str


class ComponentBase(BaseModel):
    name: str = Field(min_length=1)
    specs: str = ""
    quantity: Decimal = Field(gt=0)
    unit: UnitType
    serial_number: str = ""
    linked_item_id: str | None = None


class ItemComponentCreate(ComponentBase):
    pass


class ItemComponentUpdate(BaseModel):
    name: str | None = None
    specs: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: UnitType | None = None
    serial_number: str | None = None
    linked_item_id: str | None = None


class ItemComponentRead(OrmModel):
    id: str
    parent_item_id: str
    name: str
    specs: str
    quantity: Decimal
    unit: str
    serial_number: str
    linked_item_id: str | None
    created_at: datetime
    updated_at: datetime


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str = ""
    inventory_number: str = ""
    quantity: Decimal = Field(gt=0)
    unit: UnitType
    responsible_user_id: str
    holder_user_id: str
    location_id: str
    storage_box: str = ""
    status: ItemStatus = "active"
    operational_status: OperationalStatus = "available"
    notes: str = ""
    template_id: str | None = None
    components: list[ItemComponentCreate] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    inventory_number: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: UnitType | None = None
    responsible_user_id: str | None = None
    holder_user_id: str | None = None
    location_id: str | None = None
    storage_box: str | None = None
    status: ItemStatus | None = None
    operational_status: OperationalStatus | None = None
    notes: str | None = None
    template_id: str | None = None


class ItemPhotoRead(OrmModel):
    id: str
    item_id: str
    file_name: str
    file_path: str
    mime_type: str
    sort_order: int
    created_at: datetime


class ItemHistoryRead(OrmModel):
    id: str
    item_id: str
    action: str
    description: str
    person_id: str | None
    created_at: datetime


class ItemListRead(OrmModel):
    id: str
    name: str
    category: str
    inventory_number: str
    quantity: Decimal
    unit: str
    responsible_user_id: str
    holder_user_id: str
    location_id: str
    storage_box: str
    status: str
    operational_status: str
    notes: str
    template_id: str | None
    created_at: datetime
    updated_at: datetime


class ItemDetailRead(ItemListRead):
    responsible_user: UserBrief
    holder_user: UserBrief
    location: LocationBrief
    photos: list[ItemPhotoRead]
    components: list[ItemComponentRead]
    history: list[ItemHistoryRead]


class TransferCreate(BaseModel):
    to_user_id: str
    notes: str = ""
    is_request: bool = False


class TransferRead(OrmModel):
    id: str
    item_id: str
    from_user_id: str
    to_user_id: str
    status: str
    notes: str
    is_request: bool
    created_at: datetime
    completed_at: datetime | None


class WriteOffCreate(BaseModel):
    reason: WriteOffReason
    amount: Decimal = Field(gt=0)
    notes: str = ""
    person_id: str | None = None


class WriteOffRead(OrmModel):
    id: str
    item_id: str
    reason: str
    amount: Decimal
    unit: str
    notes: str
    person_id: str
    created_at: datetime


class RepairCreate(BaseModel):
    issue_description: str = Field(min_length=1)
    service_provider: str = ""
    cost: Decimal | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    expected_return_at: datetime | None = None
    notes: str = ""


class RepairUpdate(BaseModel):
    status: RepairStatus | None = None
    issue_description: str | None = None
    service_provider: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    expected_return_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None


class RepairRead(OrmModel):
    id: str
    item_id: str
    status: str
    issue_description: str
    service_provider: str
    cost: Decimal | None
    started_at: datetime
    expected_return_at: datetime | None
    completed_at: datetime | None
    notes: str
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class RentalCreate(BaseModel):
    renter_name: str = Field(min_length=1)
    renter_contact: str = ""
    start_at: datetime
    end_at: datetime
    price_amount: Decimal = Field(gt=0)
    price_period: RentalPricePeriod
    currency: str = "RUB"
    notes: str = ""


class RentalUpdate(BaseModel):
    status: RentalStatus | None = None
    renter_name: str | None = None
    renter_contact: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    returned_at: datetime | None = None
    price_amount: Decimal | None = Field(default=None, gt=0)
    price_period: RentalPricePeriod | None = None
    currency: str | None = None
    notes: str | None = None


class RentalRead(OrmModel):
    id: str
    item_id: str
    status: str
    renter_name: str
    renter_contact: str
    start_at: datetime
    end_at: datetime
    returned_at: datetime | None
    price_amount: Decimal
    price_period: str
    currency: str
    notes: str
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class TemplateItemCreate(BaseModel):
    name: str = Field(min_length=1)
    specs: str = ""
    quantity: Decimal = Field(gt=0)
    unit: UnitType
    serial_number: str = ""
    sort_order: int = 0


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1)
    items: list[TemplateItemCreate] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: str | None = None
    items: list[TemplateItemCreate] | None = None


class TemplateItemRead(OrmModel):
    id: str
    template_id: str
    name: str
    specs: str
    quantity: Decimal
    unit: str
    serial_number: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class TemplateRead(OrmModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    items: list[TemplateItemRead]


class PaginatedResponse(BaseModel):
    items: list[object]
    page: int
    per_page: int
    total: int
