# Stocky API

Интеграционная документация backend API для приложения Stocky.

Документ описывает:
- как запустить API;
- как подключиться к БД `stocky`;
- как работает авторизация;
- какие endpoint'ы доступны;
- какие поля отправлять в запросах;
- какие ответы получает клиент;
- какой порядок интеграции использовать в мобильном приложении.

## 1. Назначение API

Stocky API управляет:
- ролями пользователей;
- пользователями;
- местами хранения;
- товарами;
- комплектующими товаров;
- фотографиями товаров;
- историей изменений товаров;
- передачами товаров;
- списаниями товаров;
- шаблонами комплектующих.

## 2. Технологии

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- MySQL 8+

## 3. Конфигурация

Пример `.env`:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=stocky
DB_USER=root
DB_PASSWORD=secret
AUTH_SECRET_KEY=change-me-stocky-secret
AUTH_TOKEN_EXPIRE_MINUTES=480
STOCKY_UPLOAD_DIR=storage/uploads
```

Описание переменных:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: подключение к MySQL.
- `AUTH_SECRET_KEY`: секрет для подписи access token.
- `AUTH_TOKEN_EXPIRE_MINUTES`: время жизни токена в минутах.
- `STOCKY_UPLOAD_DIR`: директория для сохранения фото товаров.

## 4. Запуск

Установка зависимостей:

```bash
pip install -r requirements.txt
```

Запуск:

```bash
python run.py
```

По умолчанию сервер стартует на:

```text
http://0.0.0.0:8388
```

Swagger UI:

```text
http://localhost:8388/docs
```

## 5. Базовые правила API

Базовый префикс:

```text
/api/v1
```

Формат:
- `Content-Type: application/json`
- даты приходят в ISO 8601
- UUID передаются строками

Общий успешный ответ:

```json
{
  "success": true,
  "data": {}
}
```

Ответ с ошибкой:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Текст ошибки"
  }
}
```

Типовые `error.code`:
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `AUTH_ERROR`
- `HTTP_ERROR`

## 6. Авторизация

### 6.1 Как работает

После регистрации или логина сервер возвращает:
- `access_token`
- `token_type`
- `expires_at`
- `user`

Дальше этот токен нужно передавать в каждый защищённый endpoint.

### 6.2 Рекомендуемый способ

Через заголовок:

```http
Authorization: Bearer <access_token>
```

Пример:

```http
Authorization: Bearer eyJzdWIiOiJ...signature
```

### 6.3 Поддерживаемые способы передачи токена

Сейчас API принимает токен тремя способами:

1. `Authorization: Bearer <token>`
2. `X-Access-Token: <token>`
3. query parameter: `?access_token=<token>`

Для приложения рекомендуется использовать только `Authorization: Bearer`.

## 7. Порядок интеграции клиента

Рекомендуемый сценарий:

1. Выполнить `POST /api/v1/auth/login`
2. Сохранить `access_token`
3. Подставлять токен в `Authorization: Bearer <token>`
4. Получить справочники:
   - `GET /api/v1/roles`
   - `GET /api/v1/users`
   - `GET /api/v1/locations`
   - `GET /api/v1/templates`
5. Работать с товарами, передачами и списаниями

## 8. Роли

### `GET /api/v1/roles`

Возвращает список ролей.

Требует авторизацию: `Да`

Пример ответа:

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Пользователь"
    },
    {
      "id": 2,
      "name": "Администратор"
    }
  ]
}
```

### `POST /api/v1/roles`

Создаёт роль.

Требует авторизацию: `Да`

Тело:

```json
{
  "name": "Кладовщик"
}
```

### `PATCH /api/v1/roles/{role_id}`

Обновляет имя роли.

Тело:

```json
{
  "name": "Старший кладовщик"
}
```

### `DELETE /api/v1/roles/{role_id}`

Удаляет роль.

Ограничение:
- если роль назначена пользователям, сервер вернёт ошибку.

## 9. Авторизация и аккаунт

### `POST /api/v1/auth/register`

Регистрирует пользователя и сразу возвращает токен.

Тело:

```json
{
  "name": "Степан",
  "surname": "Степанов",
  "patronymic": "Александрович",
  "login": "st.stepanov57@gmail.com",
  "password": "secret123",
  "role_id": 2
}
```

Обязательные поля:
- `name`
- `surname`
- `login`
- `password`
- `role_id`

Ответ:

```json
{
  "success": true,
  "data": {
    "access_token": "token",
    "token_type": "bearer",
    "expires_at": "2026-04-17T22:24:51.808442+00:00",
    "user": {
      "id": "uuid",
      "name": "Степан",
      "surname": "Степанов",
      "patronymic": "Александрович",
      "login": "st.stepanov57@gmail.com",
      "role_id": 2,
      "is_active": true,
      "created_at": "2026-04-09T14:24:11",
      "updated_at": "2026-04-09T14:24:11",
      "full_name": "Степанов Степан Александрович",
      "role": {
        "id": 2,
        "name": "Администратор"
      }
    }
  }
}
```

### `POST /api/v1/auth/login`

Логин пользователя.

Тело:

```json
{
  "login": "st.stepanov57@gmail.com",
  "password": "secret123"
}
```

Ответ аналогичен `register`.

### `GET /api/v1/auth/me`

Возвращает текущего авторизованного пользователя.

Требует авторизацию: `Да`

Пример:

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

## 10. Пользователи

### Структура пользователя

Поля пользователя:
- `id`
- `name`
- `surname`
- `patronymic`
- `login`
- `role_id`
- `is_active`
- `created_at`
- `updated_at`
- `full_name`
- `role`

### `GET /api/v1/users`

Список пользователей.

Требует авторизацию: `Да`

Query params:
- `active_only=true|false`
- `search=...`
- `role_id=2`

Пример:

```http
GET /api/v1/users?active_only=true&search=step
Authorization: Bearer <token>
```

### `POST /api/v1/users`

Создаёт пользователя.

Тело:

```json
{
  "name": "Иван",
  "surname": "Иванов",
  "patronymic": "Иванович",
  "login": "ivan@example.com",
  "password": "secret123",
  "role_id": 1
}
```

### `GET /api/v1/users/{user_id}`

Возвращает одного пользователя.

### `PATCH /api/v1/users/{user_id}`

Обновляет пользователя.

Можно передавать:
- `name`
- `surname`
- `patronymic`
- `login`
- `password`
- `role_id`
- `is_active`

Пример:

```json
{
  "role_id": 2,
  "is_active": true
}
```

### `DELETE /api/v1/users/{user_id}`

Не удаляет пользователя физически, а деактивирует через `is_active = false`.

## 11. Места хранения

### `GET /api/v1/locations`

Список мест хранения.

### `POST /api/v1/locations`

Создаёт место хранения.

Тело:

```json
{
  "name": "Основной склад",
  "description": "Склад на первом этаже"
}
```

### `GET /api/v1/locations/{location_id}`

Возвращает одно место хранения.

### `PATCH /api/v1/locations/{location_id}`

Можно обновлять:
- `name`
- `description`
- `is_active`

### `DELETE /api/v1/locations/{location_id}`

Деактивирует место хранения.

## 12. Шаблоны комплектующих

### `GET /api/v1/templates`

Список шаблонов.

### `POST /api/v1/templates`

Создаёт шаблон.

Тело:

```json
{
  "name": "Компьютер стандарт",
  "items": [
    {
      "name": "SSD",
      "specs": "Samsung 500 GB",
      "quantity": 1,
      "unit": "шт",
      "serial_number": "",
      "sort_order": 0
    }
  ]
}
```

### `GET /api/v1/templates/{template_id}`

Возвращает шаблон вместе со строками.

### `PATCH /api/v1/templates/{template_id}`

Можно обновлять:
- `name`
- `items`

Если передан `items`, шаблон пересобирается полностью.

### `DELETE /api/v1/templates/{template_id}`

Удаляет шаблон.

Если он был привязан к товарам, у товаров поле `template_id` будет очищено.

## 13. Товары

### Структура товара

Основные поля:
- `id`
- `name`
- `category`
- `inventory_number`
- `quantity`
- `unit`
- `responsible_user_id`
- `holder_user_id`
- `location_id`
- `storage_box`
- `status`
- `notes`
- `template_id`
- `created_at`
- `updated_at`

Статусы:
- `active`
- `written_off`

Допустимые `unit`:
- `шт`
- `м`
- `см`
- `кг`
- `г`
- `л`
- `мл`
- `компл.`
- `кор.`
- `рул.`
- `пар`
- `ед.`

### `GET /api/v1/items`

Список товаров.

Query params:
- `status=active|written_off`
- `search=...`
- `category=...`
- `responsible_user_id=...`
- `holder_user_id=...`
- `location_id=...`
- `page=1`
- `per_page=20`
- `sort=name|created_at|updated_at`
- `order=asc|desc`

Пример:

```http
GET /api/v1/items?status=active&page=1&per_page=20&sort=updated_at&order=desc
Authorization: Bearer <token>
```

Формат ответа:

```json
{
  "success": true,
  "data": {
    "items": [],
    "page": 1,
    "per_page": 20,
    "total": 0
  }
}
```

### `POST /api/v1/items`

Создаёт товар.

Тело:

```json
{
  "name": "Dell OptiPlex 7090",
  "category": "Компьютеры",
  "inventory_number": "ПК-001",
  "quantity": 1,
  "unit": "шт",
  "responsible_user_id": "uuid-user-1",
  "holder_user_id": "uuid-user-1",
  "location_id": "uuid-location-1",
  "storage_box": "Стол 4",
  "status": "active",
  "notes": "Рабочая станция",
  "template_id": null,
  "components": [
    {
      "name": "SSD",
      "specs": "Samsung 970 EVO 500 GB",
      "quantity": 1,
      "unit": "шт",
      "serial_number": "SN123456",
      "linked_item_id": null
    }
  ]
}
```

Что делает сервер:
- создаёт товар;
- создаёт комплектующие;
- добавляет запись в историю `created`.

### `GET /api/v1/items/{item_id}`

Возвращает полную карточку товара:
- товар;
- ответственного;
- текущего держателя;
- место хранения;
- фото;
- комплектующие;
- историю.

### `PATCH /api/v1/items/{item_id}`

Обновляет товар.

Можно обновлять:
- `name`
- `category`
- `inventory_number`
- `quantity`
- `unit`
- `responsible_user_id`
- `holder_user_id`
- `location_id`
- `storage_box`
- `status`
- `notes`
- `template_id`

Если изменяются поля, в истории создаётся событие:
- `edited`
- либо `location_changed`, если изменилось только место хранения

### `DELETE /api/v1/items/{item_id}`

Физически удаляет товар вместе с зависимостями.

## 14. Комплектующие товара

### `POST /api/v1/items/{item_id}/components`

Добавляет комплектующую к товару.

Тело:

```json
{
  "name": "SSD",
  "specs": "Samsung 500 GB",
  "quantity": 1,
  "unit": "шт",
  "serial_number": "SN123",
  "linked_item_id": null
}
```

### `PATCH /api/v1/items/{item_id}/components/{component_id}`

Обновляет комплектующую.

### `DELETE /api/v1/items/{item_id}/components/{component_id}`

Удаляет комплектующую.

При добавлении, изменении и удалении сервер пишет событие в историю товара.

## 15. История товара

### `GET /api/v1/items/{item_id}/history`

Возвращает историю товара в обратном порядке.

Типы событий:
- `created`
- `transferred`
- `transfer_requested`
- `written_off`
- `partial_write_off`
- `location_changed`
- `edited`

## 16. Фото товара

### `POST /api/v1/items/{item_id}/photos`

Загружает фото товара.

Формат:
- `multipart/form-data`

Поля формы:
- `files`: один или несколько файлов
- `sort_order`: начальный порядок, опционально

Пример cURL:

```bash
curl -X POST "http://localhost:8388/api/v1/items/<item_id>/photos" \
  -H "Authorization: Bearer <token>" \
  -F "files=@/path/to/photo1.jpg" \
  -F "files=@/path/to/photo2.jpg" \
  -F "sort_order=0"
```

Сервер:
- сохраняет файлы в `STOCKY_UPLOAD_DIR`;
- создаёт записи в `item_photos`.

### `DELETE /api/v1/items/{item_id}/photos/{photo_id}`

Удаляет фото и запись в БД.

### `GET /api/v1/items/{item_id}/photos/{photo_id}/view`

Возвращает файл фотографии для отображения.

Особенности:
- требует авторизацию;
- возвращает бинарный файл;
- `Content-Type` берётся из `mime_type` фотографии;
- подходит для предпросмотра изображения в приложении.

Пример:

```http
GET /api/v1/items/{item_id}/photos/{photo_id}/view
Authorization: Bearer <token>
```

### `GET /api/v1/items/{item_id}/photos/{photo_id}/download`

Возвращает файл фотографии как скачиваемое вложение.

Особенности:
- требует авторизацию;
- возвращает бинарный файл;
- выставляет `Content-Disposition: attachment`;
- подходит, если приложение хочет сохранить файл локально.

Пример:

```http
GET /api/v1/items/{item_id}/photos/{photo_id}/download
Authorization: Bearer <token>
```

## 17. Передачи

### `GET /api/v1/transfers`

Список передач.

Query params:
- `status=pending|completed|rejected`
- `item_id=...`
- `from_user_id=...`
- `to_user_id=...`
- `is_request=true|false`
- `page=1`
- `per_page=20`

### `POST /api/v1/items/{item_id}/transfers`

Создаёт передачу или запрос на получение.

Тело:

```json
{
  "to_user_id": "uuid-user-2",
  "notes": "Передаю для настройки",
  "is_request": false
}
```

Логика:
- если `is_request = false`, создаётся обычная передача от текущего держателя;
- если `is_request = true`, создаётся запрос на получение от текущего пользователя.

Сервер пока не меняет `holder_user_id` сразу, а только после подтверждения.

### `POST /api/v1/transfers/{transfer_id}/accept`

Подтверждает передачу.

Что делает сервер:
- ставит `status = completed`;
- заполняет `completed_at`;
- меняет `items.holder_user_id`.

### `POST /api/v1/transfers/{transfer_id}/reject`

Отклоняет передачу.

Что делает сервер:
- ставит `status = rejected`;
- заполняет `completed_at`;
- не меняет держателя товара.

## 18. Списания

### `GET /api/v1/write-offs`

Возвращает журнал списаний.

Query params:
- `item_id=...`
- `person_id=...`
- `reason=broken|used|lost|expired|other`
- `date_from=...`
- `date_to=...`

### `POST /api/v1/items/{item_id}/write-offs`

Создаёт списание.

Тело:

```json
{
  "reason": "broken",
  "amount": 1,
  "notes": "Поврежден корпус",
  "person_id": "uuid-user-1"
}
```

Поле `person_id` можно не передавать, тогда сервер возьмёт текущего авторизованного пользователя.

Что делает сервер:
- создаёт запись в `write_offs`;
- если `amount >= quantity`, переводит товар в `written_off`;
- если `amount < quantity`, уменьшает количество;
- добавляет событие в историю.

Причины списания:
- `broken`
- `used`
- `lost`
- `expired`
- `other`

## 19. Что важно валидировать на клиенте

Рекомендуется валидировать до отправки:
- пустые строки в обязательных полях;
- корректный `role_id` при создании пользователя;
- `quantity > 0`;
- `amount > 0` при списании;
- обязательные UUID-ссылки для товара;
- корректный формат email/login, если в приложении `login` используется как email;
- наличие токена перед обращением к защищённым endpoint'ам.

## 20. Что сервер уже делает сам

Сервер проверяет:
- существование пользователей, ролей, мест хранения и шаблонов;
- уникальность `login`;
- корректность токена;
- невозможность подтвердить уже завершённую передачу;
- невозможность списать больше текущего количества;
- невозможность удалить роль, если она назначена пользователям.

## 21. Практический сценарий интеграции

Пример типового потока в приложении:

1. Выполнить `POST /api/v1/auth/login`
2. Сохранить `access_token`
3. Выполнить `GET /api/v1/auth/me`
4. Получить справочники:
   - `GET /api/v1/roles`
   - `GET /api/v1/users`
   - `GET /api/v1/locations`
   - `GET /api/v1/templates`
5. Показать список товаров через `GET /api/v1/items`
6. Создавать и редактировать товары
7. При необходимости делать передачи, списания и загрузку фото

## 22. Полезные примеры

### Логин

```bash
curl -X POST "http://localhost:8388/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "st.stepanov57@gmail.com",
    "password": "secret123"
  }'
```

### Получение текущего пользователя

```bash
curl -X GET "http://localhost:8388/api/v1/auth/me" \
  -H "Authorization: Bearer <token>"
```

### Создание товара

```bash
curl -X POST "http://localhost:8388/api/v1/items" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ноутбук Lenovo",
    "category": "Ноутбуки",
    "inventory_number": "NB-001",
    "quantity": 1,
    "unit": "шт",
    "responsible_user_id": "uuid-user-1",
    "holder_user_id": "uuid-user-1",
    "location_id": "uuid-location-1",
    "storage_box": "Кабинет 2",
    "status": "active",
    "notes": "Новый",
    "template_id": null,
    "components": []
  }'
```

### Частичное списание

```bash
curl -X POST "http://localhost:8388/api/v1/items/<item_id>/write-offs" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "used",
    "amount": 1,
    "notes": "Израсходовано в работе"
  }'
```

## 23. Текущее поведение, которое важно знать

- Пароли в ответах никогда не возвращаются.
- Токен сейчас самописный, подписывается через `AUTH_SECRET_KEY`.
- Разделение прав по ролям пока не включено: роль хранится и возвращается, но жёстких ACL-проверок ещё нет.
- Удаление пользователя и места хранения реализовано как деактивация.
- Удаление товара и шаблона выполняется физически.
- Фото сохраняются локально на диске.

## 24. Куда смотреть в коде

Основные файлы:
- `app/api.py` — инициализация FastAPI и обработчики ошибок
- `app/routes/stocky_routes.py` — все endpoint'ы
- `app/services/stocky_service.py` — бизнес-логика
- `app/models/stocky.py` — SQLAlchemy модели
- `app/auth.py` — токены и текущий пользователь
- `app/schemas.py` — Pydantic схемы запросов и ответов

## 25. Расширение: Статусы, Ремонт, Аренда

### 25.1 Новый столбец `items.operational_status`

`status` по-прежнему отвечает за жизненный цикл товара:
- `active`
- `written_off`

Новый `operational_status` отвечает за текущее рабочее состояние товара:
- `available` — доступен
- `broken` — сломан, но не списан
- `under_repair` — находится в ремонте
- `rented` — находится в аренде

Это позволяет хранить, например:
- товар `active`, но `broken`
- товар `active`, но `under_repair`
- товар `active`, но `rented`

### 25.2 Новая таблица `repairs`

Таблица хранит ремонты товаров:
- `id`
- `item_id`
- `status`
- `issue_description`
- `service_provider`
- `cost`
- `started_at`
- `expected_return_at`
- `completed_at`
- `notes`
- `created_by_user_id`
- `created_at`
- `updated_at`

Статусы ремонта:
- `in_progress`
- `completed`
- `cancelled`

### 25.3 Новая таблица `rentals`

Таблица хранит аренды товаров:
- `id`
- `item_id`
- `status`
- `renter_name`
- `renter_contact`
- `start_at`
- `end_at`
- `returned_at`
- `price_amount`
- `price_period`
- `currency`
- `notes`
- `created_by_user_id`
- `created_at`
- `updated_at`

Статусы аренды:
- `active`
- `completed`
- `overdue`
- `cancelled`

Периоды тарифа:
- `hour`
- `day`
- `week`
- `month`
- `fixed`

### 25.4 SQL-миграция

Примените SQL-скрипт:

[`migrations/2026_04_13_repairs_and_rentals.sql`](/Users/stepanovme/PycharmProjects/ApiStocky/migrations/2026_04_13_repairs_and_rentals.sql)

Он добавляет:
- `items.operational_status`
- таблицу `repairs`
- таблицу `rentals`

### 25.5 Новые endpoint'ы

#### Товары

`POST /api/v1/items/{item_id}/repairs`
- создать ремонт для товара

`POST /api/v1/items/{item_id}/rentals`
- создать аренду для товара

`GET /api/v1/items`
- теперь можно фильтровать ещё и по `operational_status`

Пример:

```http
GET /api/v1/items?status=active&operational_status=under_repair
Authorization: Bearer <token>
```

#### Ремонты

`GET /api/v1/repairs`
- список ремонтов
- query params: `item_id`, `status`, `active_only`

`GET /api/v1/repairs/{repair_id}`
- получить один ремонт

`PATCH /api/v1/repairs/{repair_id}`
- обновить ремонт

`POST /api/v1/repairs/{repair_id}/complete`
- завершить ремонт

Пример создания ремонта:

```json
{
  "issue_description": "Не включается",
  "service_provider": "Сервисный центр",
  "cost": 3500,
  "started_at": "2026-04-13T10:00:00Z",
  "expected_return_at": "2026-04-20T18:00:00Z",
  "notes": "Срочный ремонт"
}
```

Логика:
- при создании ремонта товар получает `operational_status = under_repair`
- при завершении ремонта товар получает `operational_status = available`
- при отмене ремонта товар получает `operational_status = broken`

#### Аренды

`GET /api/v1/rentals`
- список аренд
- query params: `item_id`, `status`, `active_only`

`GET /api/v1/rentals/{rental_id}`
- получить одну аренду

`PATCH /api/v1/rentals/{rental_id}`
- обновить аренду

`POST /api/v1/rentals/{rental_id}/return`
- завершить аренду и вернуть товар

Пример создания аренды:

```json
{
  "renter_name": "ООО Партнер",
  "renter_contact": "+7 999 000-00-00",
  "start_at": "2026-04-13T10:00:00Z",
  "end_at": "2026-04-27T18:00:00Z",
  "price_amount": 12000,
  "price_period": "month",
  "currency": "RUB",
  "notes": "Аренда оборудования"
}
```

Логика:
- при создании аренды товар получает `operational_status = rented`
- при возврате аренды товар получает `operational_status = available`, если у него нет активного ремонта

### 25.6 Ограничения и валидация

Сервер не позволит:
- создать вторую активную аренду на один товар
- создать второй активный ремонт на один товар
- отправить в ремонт товар, который сейчас в аренде
- сдать в аренду товар, который сломан или находится в ремонте
- создать аренду с датой окончания раньше даты начала

### 25.7 Практический сценарий

Если товар просто сломан:
- обновите товар через `PATCH /api/v1/items/{item_id}`
- передайте `"operational_status": "broken"`

Если товар отправили на ремонт:
- вызовите `POST /api/v1/items/{item_id}/repairs`

Если товар сдали в аренду:
- вызовите `POST /api/v1/items/{item_id}/rentals`

Если товар вернули из аренды:
- вызовите `POST /api/v1/rentals/{rental_id}/return`

## 26. Realtime и уведомления

### 26.1 WebSocket

Для realtime обновлений доступен WebSocket:

```text
ws://localhost:8388/api/v1/ws?access_token=<token>
```

После подключения клиент будет получать JSON-события:
- `item.created`
- `item.updated`
- `transfer.created`
- `transfer.completed`
- `transfer.rejected`
- `writeoff.created`
- `repair.created`
- `repair.updated`
- `rental.created`
- `rental.updated`

Формат сообщения:

```json
{
  "type": "event",
  "event_type": "transfer.created",
  "created_at": "2026-04-13T12:00:00Z",
  "payload": {}
}
```

Клиент может отправлять `ping`, сервер ответит `pong`.

### 26.2 Device token для push

Для хранения iOS device token:

`POST /api/v1/devices/tokens`

Тело:

```json
{
  "device_token": "apns-device-token",
  "platform": "ios",
  "device_name": "iPhone 15 Pro"
}
```

### 26.3 Внутренние уведомления

Сервер сохраняет уведомления в БД для персональных событий, например:
- создан запрос на передачу
- передача подтверждена
- передача отклонена

Ручки:
- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{notification_id}/read`

### 26.4 SQL-миграция для realtime и уведомлений

Примените:

[`migrations/2026_04_13_realtime_and_notifications.sql`](/Users/stepanovme/PycharmProjects/ApiStocky/migrations/2026_04_13_realtime_and_notifications.sql)

Скрипт создаёт:
- `device_tokens`
- `notifications`
