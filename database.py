# database.py

import asyncio
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    create_engine,
    func,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

# Определяем таблицы базы данных

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    last_attempt = Column(DateTime)
    is_winner = Column(Boolean, default=False)
    attempts = relationship('UserAttempt', back_populates='user')


class Quiz(Base):
    __tablename__ = 'quizzes'
    quiz_id = Column(Integer, primary_key=True)
    title = Column(String)
    is_active = Column(Boolean, default=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    question_count = Column(Integer)
    questions = relationship('Question', back_populates='quiz')
    attempts = relationship('UserAttempt', back_populates='quiz')


class Question(Base):
    __tablename__ = 'questions'
    question_id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.quiz_id'))
    text = Column(String)
    quiz = relationship('Quiz', back_populates='questions')
    answers = relationship('Answer', back_populates='question')


class Answer(Base):
    __tablename__ = 'answers'
    answer_id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.question_id'))
    text = Column(String)
    is_correct = Column(Boolean)
    question = relationship('Question', back_populates='answers')


class UserAttempt(Base):
    __tablename__ = 'user_attempts'
    attempt_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    quiz_id = Column(Integer, ForeignKey('quizzes.quiz_id'))
    attempt_time = Column(DateTime, default=datetime.utcnow)
    correct_answers = Column(Integer)
    is_winner = Column(Boolean)
    user = relationship('User', back_populates='attempts')
    quiz = relationship('Quiz', back_populates='attempts')
    responses = relationship('UserResponse', back_populates='attempt')


class UserResponse(Base):
    __tablename__ = 'user_responses'
    response_id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey('user_attempts.attempt_id'))
    question_id = Column(Integer, ForeignKey('questions.question_id'))
    selected_answer_id = Column(Integer, ForeignKey('answers.answer_id'))
    attempt = relationship('UserAttempt', back_populates='responses')
    question = relationship('Question')
    selected_answer = relationship('Answer')

# Настраиваем соединение с базой данных

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'data', 'quiz.db')}"


engine = create_async_engine(
    DATABASE_URL, echo=False,
)

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
