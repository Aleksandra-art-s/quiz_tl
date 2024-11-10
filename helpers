# helpers.py

from database import async_session, Admin

async def is_admin(username):
    async with async_session() as session:
        result = await session.execute(
            Admin.__table__.select().where(Admin.username == username)
        )
        admin = result.fetchone()
        return admin is not None
