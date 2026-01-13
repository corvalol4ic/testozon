from fastapi import FastAPI, HTTPException, Header
import uvicorn
from database.db import database

app = FastAPI(title="Telegram Bot API")


@app.get("/")
async def root():
    return {"message": "Bot API is running"}


@app.get("/user/info")
async def get_user_info(access_key: str = Header(..., alias="X-Access-Key")):
    """Получение информации о пользователе по ключу"""
    user = await database.get_user(access_key=access_key)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем доступ
    access = await database.check_user_access(user['user_id'])

    if not access['has_access']:
        raise HTTPException(status_code=403, detail="Access denied: " + access['reason'])

    # Увеличиваем счетчик запросов
    await database.increment_user_requests(user['user_id'])

    # Логируем запрос
    await database.add_user_request(
        user_id=user['user_id'],
        request_type="api_info",
        request_data="GET /user/info",
        response_data="User info retrieved"
    )

    return {
        "success": True,
        "user": {
            "user_id": user['user_id'],
            "username": user['username'],
            "full_name": user['full_name'],
            "subscription": user['plan_name'],
            "requests_used": user['requests_used'],
            "requests_limit": user['requests_limit'],
            "subscription_end": user['subscription_end']
        }
    }


@app.post("/bot/send")
async def send_via_bot(
        message: str,
        access_key: str = Header(..., alias="X-Access-Key")
):
    """Отправка сообщения через бота (пример)"""
    user = await database.get_user(access_key=access_key)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем доступ
    access = await database.check_user_access(user['user_id'])

    if not access['has_access']:
        raise HTTPException(status_code=403, detail="Access denied")

    # Увеличиваем счетчик запросов
    await database.increment_user_requests(user['user_id'])

    # Логируем запрос
    await database.add_user_request(
        user_id=user['user_id'],
        request_type="api_send",
        request_data=f"Message: {message}",
        response_data="Message processed"
    )

    # Здесь можно добавить логику отправки через бота
    return {
        "success": True,
        "message": "Request processed",
        "requests_remaining": access['requests_limit'] - access['requests_used'] - 1
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)