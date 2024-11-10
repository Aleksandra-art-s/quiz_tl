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

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    email = Column(String)

class Quiz(Base):
    __tablename__ = 'quizzes'
    quiz_id = Column(Integer, primary_key=True)
    title = Column(String)
    is_active = Column(Boolean)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    question_count = Column(Integer)

class Question(Base):
    __tablename__ = 'questions'
    question_id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.quiz_id'))
    text = Column(Text)

class Answer(Base):
    __tablename__ = 'answers'
    answer_id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.question_id'))
    text = Column(Text, nullable=False)  # Хранит правильный ответ

class UserAttempt(Base):
    __tablename__ = 'user_attempts'
    attempt_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    quiz_id = Column(Integer, ForeignKey('quizzes.quiz_id'))
    timestamp = Column(DateTime, default=func.now())
    correct_answers = Column(Integer)
    is_winner = Column(Boolean)

class UserResponse(Base):
    __tablename__ = 'user_responses'
    response_id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey('user_attempts.attempt_id'))
    question_id = Column(Integer, ForeignKey('questions.question_id'))
    selected_answer_text = Column(Text)

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
