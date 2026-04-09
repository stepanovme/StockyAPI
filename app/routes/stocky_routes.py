from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Form, UploadFile

from app.auth import CurrentUser
from app.database import DbSession
from app.schemas import (
    ErrorEnvelope,
    ItemComponentCreate,
    ItemComponentUpdate,
    ItemCreate,
    ItemUpdate,
    LocationCreate,
    LocationUpdate,
    LoginRequest,
    RegisterRequest,
    RoleCreate,
    RoleUpdate,
    TemplateCreate,
    TemplateUpdate,
    TransferCreate,
    UserCreate,
    UserUpdate,
    WriteOffCreate,
)
from app.services.stocky_service import StockyService

router = APIRouter(prefix="/api/v1")


def ok(data: object) -> dict[str, object]:
    return {"success": True, "data": data}


auth_router = APIRouter(prefix="/auth", tags=["Auth"])
roles_router = APIRouter(prefix="/roles", tags=["Roles"])
users_router = APIRouter(prefix="/users", tags=["Users"])
locations_router = APIRouter(prefix="/locations", tags=["Locations"])
items_router = APIRouter(prefix="/items", tags=["Items"])
transfers_router = APIRouter(prefix="/transfers", tags=["Transfers"])
write_offs_router = APIRouter(prefix="/write-offs", tags=["Write-offs"])
templates_router = APIRouter(prefix="/templates", tags=["Templates"])


@auth_router.post("/register", responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def register(payload: RegisterRequest, db: DbSession):
    return ok(StockyService(db).register(payload))


@auth_router.post("/login", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def login(payload: LoginRequest, db: DbSession):
    return ok(StockyService(db).login(payload))


@auth_router.get("/me", responses={401: {"model": ErrorEnvelope}})
def me(db: DbSession, current_user: CurrentUser):
    return ok(StockyService(db).current_user(current_user))


@roles_router.get("", responses={401: {"model": ErrorEnvelope}})
def list_roles(db: DbSession, _: CurrentUser):
    return ok(StockyService(db).list_roles())


@roles_router.post("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def create_role(payload: RoleCreate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).create_role(payload))


@roles_router.patch("/{role_id}", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def update_role(role_id: int, payload: RoleUpdate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).update_role(role_id, payload))


@roles_router.delete("/{role_id}", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_role(role_id: int, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_role(role_id))


@users_router.get("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def list_users(
    db: DbSession,
    _: CurrentUser,
    active_only: bool | None = None,
    search: str | None = None,
    role_id: int | None = None,
):
    return ok(StockyService(db).list_users(active_only, search, role_id))


@users_router.post("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def create_user(payload: UserCreate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).create_user(payload))


@users_router.get("/{user_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def get_user(user_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).get_user(user_id))


@users_router.patch("/{user_id}", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def update_user(user_id: str, payload: UserUpdate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).update_user(user_id, payload))


@users_router.delete("/{user_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_user(user_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_user(user_id))


@locations_router.get("", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def list_locations(db: DbSession, _: CurrentUser):
    return ok(StockyService(db).list_locations())


@locations_router.post("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def create_location(payload: LocationCreate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).create_location(payload))


@locations_router.get("/{location_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def get_location(location_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).get_location(location_id))


@locations_router.patch("/{location_id}", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def update_location(location_id: str, payload: LocationUpdate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).update_location(location_id, payload))


@locations_router.delete("/{location_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_location(location_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_location(location_id))


@items_router.get("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def list_items(
    db: DbSession,
    _: CurrentUser,
    status: str | None = None,
    search: str | None = None,
    category: str | None = None,
    responsible_user_id: str | None = None,
    holder_user_id: str | None = None,
    location_id: str | None = None,
    page: int = 1,
    per_page: int = 20,
    sort: str = "created_at",
    order: str = "desc",
):
    return ok(
        StockyService(db).list_items(
            status=status,
            search=search,
            category=category,
            responsible_user_id=responsible_user_id,
            holder_user_id=holder_user_id,
            location_id=location_id,
            page=page,
            per_page=per_page,
            sort=sort,
            order=order,
        )
    )


@items_router.post("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def create_item(payload: ItemCreate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).create_item(payload))


@items_router.get("/{item_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def get_item(item_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).get_item(item_id))


@items_router.patch("/{item_id}", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def update_item(item_id: str, payload: ItemUpdate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).update_item(item_id, payload))


@items_router.delete("/{item_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_item(item_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_item(item_id))


@items_router.post("/{item_id}/photos", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def upload_item_photos(
    item_id: str,
    db: DbSession,
    _: CurrentUser,
    files: list[UploadFile] = File(...),
    sort_order: int = Form(default=0),
):
    return ok(StockyService(db).upload_item_photos(item_id, files, sort_order))


@items_router.delete("/{item_id}/photos/{photo_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_item_photo(item_id: str, photo_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_item_photo(item_id, photo_id))


@items_router.post("/{item_id}/components", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def add_component(item_id: str, payload: ItemComponentCreate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).add_component(item_id, payload))


@items_router.patch(
    "/{item_id}/components/{component_id}",
    responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
)
def update_component(
    item_id: str,
    component_id: str,
    payload: ItemComponentUpdate,
    db: DbSession,
    _: CurrentUser,
):
    return ok(StockyService(db).update_component(item_id, component_id, payload))


@items_router.delete("/{item_id}/components/{component_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_component(item_id: str, component_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_component(item_id, component_id))


@items_router.get("/{item_id}/history", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def get_item_history(item_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).get_item_history(item_id))


@items_router.post("/{item_id}/transfers", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def create_transfer(item_id: str, payload: TransferCreate, db: DbSession, current_user: CurrentUser):
    return ok(StockyService(db).create_transfer(item_id, payload, current_user))


@items_router.post("/{item_id}/write-offs", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def create_write_off(item_id: str, payload: WriteOffCreate, db: DbSession, current_user: CurrentUser):
    return ok(StockyService(db).create_write_off(item_id, payload, current_user))


@transfers_router.get("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def list_transfers(
    db: DbSession,
    _: CurrentUser,
    status: str | None = None,
    item_id: str | None = None,
    from_user_id: str | None = None,
    to_user_id: str | None = None,
    is_request: bool | None = None,
    page: int = 1,
    per_page: int = 20,
):
    return ok(
        StockyService(db).list_transfers(
            status=status,
            item_id=item_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            is_request=is_request,
            page=page,
            per_page=per_page,
        )
    )


@transfers_router.post("/{transfer_id}/accept", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def accept_transfer(transfer_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).accept_transfer(transfer_id))


@transfers_router.post("/{transfer_id}/reject", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def reject_transfer(transfer_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).reject_transfer(transfer_id))


@write_offs_router.get("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def list_write_offs(
    db: DbSession,
    _: CurrentUser,
    item_id: str | None = None,
    person_id: str | None = None,
    reason: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    return ok(StockyService(db).list_write_offs(item_id, person_id, reason, date_from, date_to))


@templates_router.get("", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def list_templates(db: DbSession, _: CurrentUser):
    return ok(StockyService(db).list_templates())


@templates_router.post("", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
def create_template(payload: TemplateCreate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).create_template(payload))


@templates_router.get("/{template_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def get_template(template_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).get_template(template_id))


@templates_router.patch("/{template_id}", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def update_template(template_id: str, payload: TemplateUpdate, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).update_template(template_id, payload))


@templates_router.delete("/{template_id}", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
def delete_template(template_id: str, db: DbSession, _: CurrentUser):
    return ok(StockyService(db).delete_template(template_id))


router.include_router(auth_router)
router.include_router(roles_router)
router.include_router(users_router)
router.include_router(locations_router)
router.include_router(items_router)
router.include_router(transfers_router)
router.include_router(write_offs_router)
router.include_router(templates_router)
