# bot.py

from aiogram import Bot, Dispatcher
from config import API_TOKEN
from database import init_db
from handlers import register_handlers
from aiogram.contrib.fsm_storage.memory import MemoryStorage

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрируем обработчики
register_handlers(dp)

# Функция для добавления тестовых данных в базу данных
async def add_test_data():
    from database import async_session, Quiz, Question, Answer
    from datetime import datetime, timedelta

    async with async_session() as session:
        # Проверяем, есть ли уже квиз в базе данных
        result = await session.execute(
            Quiz.__table__.select().where(Quiz.title == 'Тестовый Квиз')
        )
        quiz = result.fetchone()

        if not quiz:
            # Создаем новый квиз
            new_quiz = Quiz(
                title='Тестовый Квиз',
                is_active=True,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(days=7),
                question_count=3,
            )
            session.add(new_quiz)
            await session.commit()

            # Добавляем вопросы
            questions = [
                Question(quiz_id=new_quiz.quiz_id, text='Столица Франции?'),
                Question(quiz_id=new_quiz.quiz_id, text='5 + 7 = ?'),
                Question(quiz_id=new_quiz.quiz_id, text='Цвет неба?'),
            ]
            session.add_all(questions)
            await session.commit()

            # Получаем ID вопросов
            question_ids = [q.question_id for q in questions]

            # Добавляем ответы
            answers = [
                # Вопрос 1
                Answer(
                    question_id=question_ids[0], text='Париж', is_correct=True
                ),
                Answer(
                    question_id=question_ids[0], text='Лондон', is_correct=False
                ),
                Answer(
                    question_id=question_ids[0], text='Берлин', is_correct=False
                ),
                # Вопрос 2
                Answer(
                    question_id=question_ids[1], text='12', is_correct=True
                ),
                Answer(
                    question_id=question_ids[1], text='10', is_correct=False
                ),
                Answer(
                    question_id=question_ids[1], text='13', is_correct=False
                ),
                # Вопрос 3
                Answer(
                    question_id=question_ids[2], text='Синий', is_correct=True
                ),
                Answer(
                    question_id=question_ids[2], text='Зеленый', is_correct=False
                ),
                Answer(
                    question_id=question_ids[2], text='Красный', is_correct=False
                ),
            ]
            session.add_all(answers)
            await session.commit()


# При старте бота инициализируем базу данных и добавляем тестовые данные
async def on_startup(_):
    await init_db()
    await add_test_data()
    print('Бот запущен и готов к работе.')

