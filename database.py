# database.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Admin(Base):
    __tablename__ = 'admins'
    admin_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)

# Остальные модели остаются без изменений

# Инициализация базы данных
from config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Добавляем суперпользователя (замените 'your_username' на ваш реальный юзернейм)
    async with async_session() as session:
        result = await session.execute(Admin.__table__.select())
        admins = result.fetchall()
        if not admins:
            new_admin = Admin(username='MaierrA'.lower())  # Замените на ваш юзернейм
            session.add(new_admin)
            await session.commit()
