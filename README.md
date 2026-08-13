# Answer Controller

## Запуск

Нужны Docker и Docker Compose. Скопируйте конфигурацию, при необходимости измените пороги SLA и запустите сервис:

```bash
cp .env.example .env
docker compose up --build
```

Compose самостоятельно поднимет PostgreSQL и Redis, выполнит миграции, затем запустит API и фоновые процессы. Интерфейс будет доступен на <http://localhost:8000>, документация API — на <http://localhost:8000/docs>.

## Наполнение данными

Создать два открытых обращения:

```bash
curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "9e93ebc8-fd86-4cda-8d48-8067971989c9",
    "event_type": "customer_message",
    "occurred_at": "2026-08-13T10:00:00+03:00",
    "payload": {
      "message_id": "1d7fbfd7-f83c-4db0-aa5f-d38d056be435",
      "client_id": "customer-1",
      "channel": "chat",
      "direction": "sales",
      "text": "Нужна консультация по продукту"
    }
  }'

curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "8a36b28b-55b7-40a3-83dd-233f9e91203c",
    "event_type": "customer_message",
    "occurred_at": "2026-08-13T10:01:00+03:00",
    "payload": {
      "message_id": "cc4baf1f-3f80-4587-9ef7-a04ea84c90fb",
      "client_id": "customer-2",
      "channel": "email",
      "direction": "support",
      "text": "Не получается войти в личный кабинет"
    }
  }'
```

Чтобы закрыть первое обращение, событие ответа ссылается на `message_id` исходного сообщения клиента:

```bash
curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "e93df565-f97e-4691-8e8b-0c8e0d16db67",
    "event_type": "employee_response",
    "occurred_at": "2026-08-13T10:02:00+03:00",
    "payload": {
      "reply_to_message_id": "1d7fbfd7-f83c-4db0-aa5f-d38d056be435",
      "employee_id": "employee-1",
      "text": "Здравствуйте! Чем можем помочь?"
    }
  }'
```

`event_id` должен быть уникальным UUID. `message_id` идентифицирует исходное сообщение клиента, а `reply_to_message_id` связывает с ним ответ сотрудника. `occurred_at` должен содержать часовой пояс.
