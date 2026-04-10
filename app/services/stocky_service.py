from __future__ import annotations

import os
import shutil
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import create_access_token, hash_password, verify_password
from app.models.stocky import (
    ComponentTemplateDB,
    ComponentTemplateItemDB,
    ItemComponentDB,
    ItemDB,
    ItemHistoryDB,
    ItemPhotoDB,
    LocationDB,
    RoleDB,
    TransferDB,
    UserDB,
    WriteOffDB,
)
from app.schemas import (
    AuthUserRead,
    ItemComponentCreate,
    ItemComponentRead,
    ItemComponentUpdate,
    ItemCreate,
    ItemDetailRead,
    ItemHistoryRead,
    ItemListRead,
    ItemPhotoRead,
    ItemUpdate,
    LocationCreate,
    LocationRead,
    LocationUpdate,
    LoginRequest,
    PaginatedResponse,
    RegisterRequest,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    TemplateCreate,
    TemplateItemCreate,
    TemplateRead,
    TemplateUpdate,
    TransferCreate,
    TransferRead,
    UserBrief,
    UserCreate,
    UserRead,
    UserUpdate,
    WriteOffCreate,
    WriteOffRead,
)

ITEM_STATUSES = {"active", "written_off"}
TRANSFER_STATUSES = {"pending", "completed", "rejected"}
WRITE_OFF_REASONS = {"broken", "used", "lost", "expired", "other"}
HISTORY_ACTIONS = {
    "created",
    "transferred",
    "transfer_requested",
    "written_off",
    "partial_write_off",
    "location_changed",
    "edited",
}


def _bad_request(message: str, code: str = "VALIDATION_ERROR") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": code, "message": message},
    )


def _not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NOT_FOUND", "message": message},
    )


class StockyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.upload_root = Path(os.getenv("STOCKY_UPLOAD_DIR", "storage/uploads"))

    def _commit(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise _bad_request("Нарушено ограничение БД или уникальность данных") from exc

    def _get_role(self, role_id: int) -> RoleDB:
        role = self.db.get(RoleDB, role_id)
        if not role:
            raise _not_found("Роль не найдена")
        return role

    def _get_user(self, user_id: str) -> UserDB:
        user = (
            self.db.query(UserDB)
            .options(joinedload(UserDB.role))
            .filter(UserDB.id == user_id)
            .first()
        )
        if not user:
            raise _not_found("Пользователь не найден")
        return user

    def _get_location(self, location_id: str) -> LocationDB:
        location = self.db.get(LocationDB, location_id)
        if not location:
            raise _not_found("Место хранения не найдено")
        return location

    def _get_item(self, item_id: str, with_related: bool = False) -> ItemDB:
        stmt: Select[tuple[ItemDB]] = select(ItemDB).where(ItemDB.id == item_id)
        if with_related:
            stmt = stmt.options(
                joinedload(ItemDB.responsible_user).joinedload(UserDB.role),
                joinedload(ItemDB.holder_user).joinedload(UserDB.role),
                joinedload(ItemDB.location),
                joinedload(ItemDB.photos),
                joinedload(ItemDB.components),
                joinedload(ItemDB.history_entries),
            )
        item = self.db.execute(stmt).unique().scalar_one_or_none()
        if not item:
            raise _not_found("Товар не найден")
        return item

    def _get_transfer(self, transfer_id: str) -> TransferDB:
        transfer = self.db.get(TransferDB, transfer_id)
        if not transfer:
            raise _not_found("Передача не найдена")
        return transfer

    def _serialize_user(self, user: UserDB) -> dict[str, Any]:
        return AuthUserRead(
            **UserRead.model_validate(user).model_dump(),
            full_name=self._user_full_name(user),
            role=RoleRead.model_validate(user.role) if user.role else None,
        ).model_dump()

    def _user_full_name(self, user: UserDB) -> str:
        parts = [user.surname, user.name, user.patronymic]
        return " ".join(part for part in parts if part)

    def _get_user_by_login(self, login: str) -> UserDB | None:
        return (
            self.db.query(UserDB)
            .options(joinedload(UserDB.role))
            .filter(func.lower(UserDB.login) == login.lower())
            .first()
        )

    def _ensure_unique_login(self, login: str, exclude_user_id: str | None = None) -> None:
        query = self.db.query(UserDB).filter(func.lower(UserDB.login) == login.lower())
        if exclude_user_id:
            query = query.filter(UserDB.id != exclude_user_id)
        if query.first():
            raise _bad_request("Пользователь с таким login уже существует")

    def _add_history(
        self,
        item_id: str,
        action: str,
        description: str,
        person_id: str | None = None,
    ) -> ItemHistoryDB:
        if action not in HISTORY_ACTIONS:
            raise _bad_request("Недопустимый тип события истории")
        entry = ItemHistoryDB(
            item_id=item_id,
            action=action,
            description=description,
            person_id=person_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def _validate_item_refs(
        self,
        responsible_user_id: str,
        holder_user_id: str,
        location_id: str,
        template_id: str | None = None,
    ) -> None:
        self._get_user(responsible_user_id)
        self._get_user(holder_user_id)
        self._get_location(location_id)
        if template_id and not self.db.get(ComponentTemplateDB, template_id):
            raise _not_found("Шаблон не найден")

    def register(self, payload: RegisterRequest) -> dict[str, Any]:
        user_data = UserCreate.model_validate(payload)
        created_user = self.create_user(user_data)
        db_user = self._get_user(created_user["id"])
        token, expires_at = create_access_token(db_user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at.astimezone(UTC).isoformat(),
            "user": self._serialize_user(db_user),
        }

    def login(self, payload: LoginRequest) -> dict[str, Any]:
        user = self._get_user_by_login(payload.login.strip())
        if not user or not verify_password(payload.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_ERROR", "message": "Неверный login или password"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "AUTH_ERROR", "message": "Пользователь деактивирован"},
            )
        token, expires_at = create_access_token(user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at.astimezone(UTC).isoformat(),
            "user": self._serialize_user(user),
        }

    def current_user(self, user: UserDB) -> dict[str, Any]:
        return self._serialize_user(user)

    def list_roles(self) -> list[dict[str, Any]]:
        roles = self.db.scalars(select(RoleDB).order_by(RoleDB.id)).all()
        return [RoleRead.model_validate(role).model_dump() for role in roles]

    def create_role(self, payload: RoleCreate) -> dict[str, Any]:
        role = RoleDB(name=payload.name.strip())
        self.db.add(role)
        self.db.flush()
        self._commit()
        self.db.refresh(role)
        return RoleRead.model_validate(role).model_dump()

    def update_role(self, role_id: int, payload: RoleUpdate) -> dict[str, Any]:
        role = self._get_role(role_id)
        role.name = payload.name.strip()
        self._commit()
        self.db.refresh(role)
        return RoleRead.model_validate(role).model_dump()

    def delete_role(self, role_id: int) -> dict[str, Any]:
        role = self._get_role(role_id)
        has_users = self.db.query(UserDB.id).filter(UserDB.role_id == role_id).first()
        if has_users:
            raise _bad_request("Нельзя удалить роль, которая назначена пользователям")
        self.db.delete(role)
        self._commit()
        return {"id": role_id, "deleted": True}

    def list_users(
        self,
        active_only: bool | None = None,
        search: str | None = None,
        role_id: int | None = None,
    ) -> list[dict[str, Any]]:
        stmt = select(UserDB).options(joinedload(UserDB.role)).order_by(UserDB.surname, UserDB.name)
        if active_only is True:
            stmt = stmt.where(UserDB.is_active.is_(True))
        if role_id is not None:
            stmt = stmt.where(UserDB.role_id == role_id)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    UserDB.name.ilike(like),
                    UserDB.surname.ilike(like),
                    UserDB.patronymic.ilike(like),
                    UserDB.login.ilike(like),
                )
            )
        users = self.db.scalars(stmt).all()
        return [self._serialize_user(user) for user in users]

    def create_user(self, payload: UserCreate) -> dict[str, Any]:
        login = payload.login.strip()
        self._ensure_unique_login(login)
        self._get_role(payload.role_id)
        user = UserDB(
            name=payload.name.strip(),
            surname=payload.surname.strip(),
            patronymic=payload.patronymic.strip(),
            login=login,
            password=hash_password(payload.password),
            role_id=payload.role_id,
        )
        self.db.add(user)
        self.db.flush()
        self._commit()
        return self._serialize_user(self._get_user(user.id))

    def get_user(self, user_id: str) -> dict[str, Any]:
        return self._serialize_user(self._get_user(user_id))

    def update_user(self, user_id: str, payload: UserUpdate) -> dict[str, Any]:
        user = self._get_user(user_id)
        updates = payload.model_dump(exclude_unset=True)
        if "role_id" in updates and updates["role_id"] is not None:
            self._get_role(updates["role_id"])
        if "login" in updates and updates["login"] is not None:
            login = updates["login"].strip()
            self._ensure_unique_login(login, exclude_user_id=user.id)
            user.login = login
            updates.pop("login")
        if "password" in updates and updates["password"] is not None:
            user.password = hash_password(updates["password"])
            updates.pop("password")
        for field, value in updates.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(user, field, value)
        self._commit()
        return self._serialize_user(self._get_user(user.id))

    def delete_user(self, user_id: str) -> dict[str, Any]:
        user = self._get_user(user_id)
        user.is_active = False
        self._commit()
        return self._serialize_user(self._get_user(user.id))

    def _serialize_user_brief(self, user: UserDB) -> dict[str, Any]:
        return UserBrief.model_validate(user).model_dump()

    def list_locations(self) -> list[dict[str, Any]]:
        locations = self.db.scalars(select(LocationDB).order_by(LocationDB.name)).all()
        return [LocationRead.model_validate(location).model_dump() for location in locations]

    def create_location(self, payload: LocationCreate) -> dict[str, Any]:
        location = LocationDB(name=payload.name.strip(), description=payload.description.strip())
        self.db.add(location)
        self.db.flush()
        self._commit()
        self.db.refresh(location)
        return LocationRead.model_validate(location).model_dump()

    def get_location(self, location_id: str) -> dict[str, Any]:
        return LocationRead.model_validate(self._get_location(location_id)).model_dump()

    def update_location(self, location_id: str, payload: LocationUpdate) -> dict[str, Any]:
        location = self._get_location(location_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if isinstance(value, str):
                value = value.strip()
            setattr(location, field, value)
        self._commit()
        self.db.refresh(location)
        return LocationRead.model_validate(location).model_dump()

    def delete_location(self, location_id: str) -> dict[str, Any]:
        location = self._get_location(location_id)
        location.is_active = False
        self._commit()
        self.db.refresh(location)
        return LocationRead.model_validate(location).model_dump()

    def _serialize_item_list(self, item: ItemDB) -> dict[str, Any]:
        preview = item.photos[0].file_path if item.photos else None
        return {
            **ItemListRead.model_validate(item).model_dump(),
            "responsible_user": self._serialize_user_brief(item.responsible_user),
            "holder_user": self._serialize_user_brief(item.holder_user),
            "location": {
                "id": item.location.id,
                "name": item.location.name,
                "description": item.location.description,
            },
            "preview_photo": preview,
            "components_count": len(item.components),
        }

    def _serialize_item_detail(self, item: ItemDB) -> dict[str, Any]:
        return ItemDetailRead(
            **ItemListRead.model_validate(item).model_dump(),
            responsible_user=self._serialize_user_brief(item.responsible_user),
            holder_user=self._serialize_user_brief(item.holder_user),
            location={
                "id": item.location.id,
                "name": item.location.name,
                "description": item.location.description,
            },
            photos=[ItemPhotoRead.model_validate(photo) for photo in item.photos],
            components=[ItemComponentRead.model_validate(component) for component in item.components],
            history=[ItemHistoryRead.model_validate(entry) for entry in item.history_entries],
        ).model_dump()

    def list_items(
        self,
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
    ) -> dict[str, Any]:
        if status and status not in ITEM_STATUSES:
            raise _bad_request("Недопустимый статус товара")
        sort_column = getattr(ItemDB, sort, None)
        if sort_column is None or sort not in {"name", "created_at", "updated_at"}:
            raise _bad_request("Недопустимое поле сортировки")
        if order not in {"asc", "desc"}:
            raise _bad_request("Недопустимое направление сортировки")

        stmt = select(ItemDB).options(
            joinedload(ItemDB.responsible_user),
            joinedload(ItemDB.holder_user),
            joinedload(ItemDB.location),
            joinedload(ItemDB.photos),
            joinedload(ItemDB.components),
        )
        if status:
            stmt = stmt.where(ItemDB.status == status)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(ItemDB.name.ilike(like), ItemDB.inventory_number.ilike(like)))
        if category:
            stmt = stmt.where(ItemDB.category == category)
        if responsible_user_id:
            stmt = stmt.where(ItemDB.responsible_user_id == responsible_user_id)
        if holder_user_id:
            stmt = stmt.where(ItemDB.holder_user_id == holder_user_id)
        if location_id:
            stmt = stmt.where(ItemDB.location_id == location_id)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        sort_expr = sort_column.asc() if order == "asc" else sort_column.desc()
        items = self.db.execute(
            stmt.order_by(sort_expr, ItemDB.id).offset((page - 1) * per_page).limit(per_page)
        ).unique().scalars().all()
        return PaginatedResponse(
            items=[self._serialize_item_list(item) for item in items],
            page=page,
            per_page=per_page,
            total=total,
        ).model_dump()

    def create_item(self, payload: ItemCreate) -> dict[str, Any]:
        self._validate_item_refs(
            payload.responsible_user_id,
            payload.holder_user_id,
            payload.location_id,
            payload.template_id,
        )
        item = ItemDB(
            name=payload.name.strip(),
            category=payload.category.strip(),
            inventory_number=payload.inventory_number.strip(),
            quantity=payload.quantity,
            unit=payload.unit,
            responsible_user_id=payload.responsible_user_id,
            holder_user_id=payload.holder_user_id,
            location_id=payload.location_id,
            storage_box=payload.storage_box.strip(),
            status=payload.status,
            notes=payload.notes.strip(),
            template_id=payload.template_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(item)
        self.db.flush()

        for component_payload in payload.components:
            self._create_component_record(item.id, component_payload)

        self._add_history(item.id, "created", "Товар создан", payload.responsible_user_id)
        self._commit()
        return self.get_item(item.id)

    def get_item(self, item_id: str) -> dict[str, Any]:
        return self._serialize_item_detail(self._get_item(item_id, with_related=True))

    def update_item(self, item_id: str, payload: ItemUpdate) -> dict[str, Any]:
        item = self._get_item(item_id)
        updates = payload.model_dump(exclude_unset=True)
        tracked_changes: list[str] = []

        if "responsible_user_id" in updates and updates["responsible_user_id"] is not None:
            self._get_user(updates["responsible_user_id"])
        if "holder_user_id" in updates and updates["holder_user_id"] is not None:
            self._get_user(updates["holder_user_id"])
        if "location_id" in updates and updates["location_id"] is not None:
            self._get_location(updates["location_id"])
        if "template_id" in updates and updates["template_id"] and not self.db.get(ComponentTemplateDB, updates["template_id"]):
            raise _not_found("Шаблон не найден")

        for field, value in updates.items():
            if isinstance(value, str):
                value = value.strip()
            if getattr(item, field) != value:
                tracked_changes.append(field)
            setattr(item, field, value)

        if tracked_changes:
            action = "location_changed" if tracked_changes == ["location_id"] else "edited"
            self._add_history(item.id, action, f"Изменены поля: {', '.join(tracked_changes)}")

        self._commit()
        return self.get_item(item_id)

    def delete_item(self, item_id: str) -> dict[str, Any]:
        item = self._get_item(item_id)
        self.db.delete(item)
        self._commit()
        return {"id": item_id, "deleted": True}

    def upload_item_photos(
        self,
        item_id: str,
        files: list[UploadFile],
        sort_order: int = 0,
    ) -> list[dict[str, Any]]:
        self._get_item(item_id)
        item_dir = self.upload_root / item_id
        item_dir.mkdir(parents=True, exist_ok=True)

        photos: list[ItemPhotoDB] = []
        for index, file in enumerate(files):
            photo_id = str(uuid.uuid4())
            file_ext = Path(file.filename or "").suffix
            stored_name = f"{photo_id}{file_ext}"
            destination = item_dir / stored_name
            with destination.open("wb") as target:
                shutil.copyfileobj(file.file, target)
            photo = ItemPhotoDB(
                id=photo_id,
                item_id=item_id,
                file_name=file.filename or stored_name,
                file_path=str(destination),
                mime_type=file.content_type or "application/octet-stream",
                sort_order=sort_order + index,
                created_at=datetime.utcnow(),
            )
            self.db.add(photo)
            photos.append(photo)

        self._commit()
        return [ItemPhotoRead.model_validate(photo).model_dump() for photo in photos]

    def delete_item_photo(self, item_id: str, photo_id: str) -> dict[str, Any]:
        photo = self.db.get(ItemPhotoDB, photo_id)
        if not photo or photo.item_id != item_id:
            raise _not_found("Фотография не найдена")
        file_path = Path(photo.file_path)
        self.db.delete(photo)
        self._commit()
        if file_path.exists():
            file_path.unlink()
        return {"id": photo_id, "deleted": True}

    def get_item_photo_file(self, item_id: str, photo_id: str) -> ItemPhotoDB:
        photo = self.db.get(ItemPhotoDB, photo_id)
        if not photo or photo.item_id != item_id:
            raise _not_found("Фотография не найдена")
        file_path = Path(photo.file_path)
        if not file_path.exists():
            raise _not_found("Файл фотографии не найден на диске")
        return photo

    def _create_component_record(self, item_id: str, payload: ItemComponentCreate) -> ItemComponentDB:
        linked_item_id = payload.linked_item_id
        if linked_item_id and not self.db.get(ItemDB, linked_item_id):
            raise _not_found("Связанный товар не найден")
        component = ItemComponentDB(
            parent_item_id=item_id,
            name=payload.name.strip(),
            specs=payload.specs.strip(),
            quantity=payload.quantity,
            unit=payload.unit,
            serial_number=payload.serial_number.strip(),
            linked_item_id=linked_item_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(component)
        self.db.flush()
        return component

    def add_component(self, item_id: str, payload: ItemComponentCreate) -> dict[str, Any]:
        self._get_item(item_id)
        component = self._create_component_record(item_id, payload)
        self._add_history(item_id, "edited", f"Добавлена комплектующая: {component.name}")
        self._commit()
        self.db.refresh(component)
        return ItemComponentRead.model_validate(component).model_dump()

    def update_component(self, item_id: str, component_id: str, payload: ItemComponentUpdate) -> dict[str, Any]:
        component = self.db.get(ItemComponentDB, component_id)
        if not component or component.parent_item_id != item_id:
            raise _not_found("Комплектующая не найдена")
        updates = payload.model_dump(exclude_unset=True)
        if "linked_item_id" in updates and updates["linked_item_id"]:
            if not self.db.get(ItemDB, updates["linked_item_id"]):
                raise _not_found("Связанный товар не найден")
        for field, value in updates.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(component, field, value)
        component.updated_at = datetime.utcnow()
        self._add_history(item_id, "edited", f"Обновлена комплектующая: {component.name}")
        self._commit()
        self.db.refresh(component)
        return ItemComponentRead.model_validate(component).model_dump()

    def delete_component(self, item_id: str, component_id: str) -> dict[str, Any]:
        component = self.db.get(ItemComponentDB, component_id)
        if not component or component.parent_item_id != item_id:
            raise _not_found("Комплектующая не найдена")
        self.db.delete(component)
        self._add_history(item_id, "edited", f"Удалена комплектующая: {component.name}")
        self._commit()
        return {"id": component_id, "deleted": True}

    def get_item_history(self, item_id: str) -> list[dict[str, Any]]:
        self._get_item(item_id)
        entries = self.db.scalars(
            select(ItemHistoryDB)
            .where(ItemHistoryDB.item_id == item_id)
            .order_by(ItemHistoryDB.created_at.desc())
        ).all()
        return [ItemHistoryRead.model_validate(entry).model_dump() for entry in entries]

    def list_transfers(
        self,
        status: str | None = None,
        item_id: str | None = None,
        from_user_id: str | None = None,
        to_user_id: str | None = None,
        is_request: bool | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        if status and status not in TRANSFER_STATUSES:
            raise _bad_request("Недопустимый статус передачи")
        stmt = select(TransferDB)
        if status:
            stmt = stmt.where(TransferDB.status == status)
        if item_id:
            stmt = stmt.where(TransferDB.item_id == item_id)
        if from_user_id:
            stmt = stmt.where(TransferDB.from_user_id == from_user_id)
        if to_user_id:
            stmt = stmt.where(TransferDB.to_user_id == to_user_id)
        if is_request is not None:
            stmt = stmt.where(TransferDB.is_request.is_(is_request))

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        transfers = self.db.scalars(
            stmt.order_by(TransferDB.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        ).all()
        return PaginatedResponse(
            items=[TransferRead.model_validate(transfer).model_dump() for transfer in transfers],
            page=page,
            per_page=per_page,
            total=total,
        ).model_dump()

    def create_transfer(self, item_id: str, payload: TransferCreate, actor: UserDB) -> dict[str, Any]:
        item = self._get_item(item_id)
        self._get_user(payload.to_user_id)
        actor_id = actor.id

        if payload.is_request:
            from_user_id = actor_id
            to_user_id = item.holder_user_id
        else:
            from_user_id = item.holder_user_id
            to_user_id = payload.to_user_id

        if from_user_id == to_user_id:
            raise _bad_request("Нельзя создавать передачу самому себе")

        transfer = TransferDB(
            item_id=item_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            status="pending",
            notes=payload.notes.strip(),
            is_request=payload.is_request,
            created_at=datetime.utcnow(),
        )
        self.db.add(transfer)
        self.db.flush()
        action = "transfer_requested" if payload.is_request else "transferred"
        description = "Создан запрос на передачу" if payload.is_request else "Создана передача товара"
        self._add_history(item_id, action, description, actor_id)
        self._commit()
        self.db.refresh(transfer)
        return TransferRead.model_validate(transfer).model_dump()

    def accept_transfer(self, transfer_id: str) -> dict[str, Any]:
        transfer = self._get_transfer(transfer_id)
        if transfer.status != "pending":
            raise _bad_request("Можно подтверждать только передачу в статусе pending")
        item = self._get_item(transfer.item_id)
        new_holder_id = transfer.from_user_id if transfer.is_request else transfer.to_user_id
        item.holder_user_id = new_holder_id
        item.updated_at = datetime.utcnow()
        transfer.status = "completed"
        transfer.completed_at = datetime.utcnow()
        self._add_history(item.id, "transferred", "Передача подтверждена", new_holder_id)
        self._commit()
        return TransferRead.model_validate(transfer).model_dump()

    def reject_transfer(self, transfer_id: str) -> dict[str, Any]:
        transfer = self._get_transfer(transfer_id)
        if transfer.status != "pending":
            raise _bad_request("Можно отклонять только передачу в статусе pending")
        transfer.status = "rejected"
        transfer.completed_at = datetime.utcnow()
        self._commit()
        return TransferRead.model_validate(transfer).model_dump()

    def list_write_offs(
        self,
        item_id: str | None = None,
        person_id: str | None = None,
        reason: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if reason and reason not in WRITE_OFF_REASONS:
            raise _bad_request("Недопустимая причина списания")
        stmt = select(WriteOffDB).order_by(WriteOffDB.created_at.desc())
        if item_id:
            stmt = stmt.where(WriteOffDB.item_id == item_id)
        if person_id:
            stmt = stmt.where(WriteOffDB.person_id == person_id)
        if reason:
            stmt = stmt.where(WriteOffDB.reason == reason)
        if date_from:
            stmt = stmt.where(WriteOffDB.created_at >= date_from)
        if date_to:
            stmt = stmt.where(WriteOffDB.created_at <= date_to)
        write_offs = self.db.scalars(stmt).all()
        return [WriteOffRead.model_validate(write_off).model_dump() for write_off in write_offs]

    def create_write_off(self, item_id: str, payload: WriteOffCreate, actor: UserDB) -> dict[str, Any]:
        item = self._get_item(item_id)
        person_id = payload.person_id or actor.id
        self._get_user(person_id)
        if item.status == "written_off":
            raise _bad_request("Товар уже полностью списан")
        if payload.amount > item.quantity:
            raise _bad_request("Сумма списания больше текущего количества товара")

        write_off = WriteOffDB(
            item_id=item_id,
            reason=payload.reason,
            amount=payload.amount,
            unit=item.unit,
            notes=payload.notes.strip(),
            person_id=person_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(write_off)

        new_quantity = item.quantity - payload.amount
        if new_quantity <= Decimal("0"):
            item.quantity = Decimal("0.00")
            item.status = "written_off"
            history_action = "written_off"
            history_description = "Товар полностью списан"
        else:
            item.quantity = new_quantity
            history_action = "partial_write_off"
            history_description = f"Товар частично списан на {payload.amount}"
        item.updated_at = datetime.utcnow()

        self._add_history(item_id, history_action, history_description, person_id)
        self._commit()
        self.db.refresh(write_off)
        return WriteOffRead.model_validate(write_off).model_dump()

    def list_templates(self) -> list[dict[str, Any]]:
        templates = self.db.scalars(
            select(ComponentTemplateDB)
            .options(joinedload(ComponentTemplateDB.items))
            .order_by(ComponentTemplateDB.name)
        ).unique().all()
        return [TemplateRead.model_validate(template).model_dump() for template in templates]

    def create_template(self, payload: TemplateCreate) -> dict[str, Any]:
        template = ComponentTemplateDB(name=payload.name.strip())
        self.db.add(template)
        self.db.flush()
        self._replace_template_items(template, payload.items)
        self._commit()
        self.db.refresh(template)
        return self.get_template(template.id)

    def get_template(self, template_id: str) -> dict[str, Any]:
        template = self.db.execute(
            select(ComponentTemplateDB)
            .options(joinedload(ComponentTemplateDB.items))
            .where(ComponentTemplateDB.id == template_id)
        ).unique().scalar_one_or_none()
        if not template:
            raise _not_found("Шаблон не найден")
        return TemplateRead.model_validate(template).model_dump()

    def _replace_template_items(self, template: ComponentTemplateDB, items: list[TemplateItemCreate]) -> None:
        template.items.clear()
        self.db.flush()
        for index, item_payload in enumerate(items):
            template.items.append(
                ComponentTemplateItemDB(
                    name=item_payload.name.strip(),
                    specs=item_payload.specs.strip(),
                    quantity=item_payload.quantity,
                    unit=item_payload.unit,
                    serial_number=item_payload.serial_number.strip(),
                    sort_order=item_payload.sort_order if item_payload.sort_order is not None else index,
                )
            )

    def update_template(self, template_id: str, payload: TemplateUpdate) -> dict[str, Any]:
        template = self.db.execute(
            select(ComponentTemplateDB)
            .options(joinedload(ComponentTemplateDB.items))
            .where(ComponentTemplateDB.id == template_id)
        ).unique().scalar_one_or_none()
        if not template:
            raise _not_found("Шаблон не найден")
        if payload.name is not None:
            template.name = payload.name.strip()
        if payload.items is not None:
            self._replace_template_items(template, payload.items)
        self._commit()
        return self.get_template(template_id)

    def delete_template(self, template_id: str) -> dict[str, Any]:
        template = self.db.get(ComponentTemplateDB, template_id)
        if not template:
            raise _not_found("Шаблон не найден")
        for item in self.db.scalars(select(ItemDB).where(ItemDB.template_id == template_id)).all():
            item.template_id = None
        self.db.delete(template)
        self._commit()
        return {"id": template_id, "deleted": True}
