# helpers.py

from database import async_session, Admin
import logging

async def is_admin(username):
    if not username:
        logging.info("Пользователь без юзернейма.")
        return False
    normalized_username = username.lstrip('@').lower()
    async with async_session() as session:
        result = await session.execute(
            Admin.__table__.select().where(Admin.username.ilike(normalized_username))
        )
        admin = result.fetchone()
        is_admin = admin is not None
        logging.info(f"Проверка администратора '{normalized_username}': {is_admin}")
        return is_admin
