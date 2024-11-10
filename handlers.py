# handlers.py

import logging
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta

from bot import dp, bot
from helpers import is_admin
from database import (
    async_session,
    User,
    Quiz,
    Question,
    Answer,
    UserAttempt,
    UserResponse,
    Admin,
)
from keyboards import admin_main_menu, confirm_keyboard, quiz_list_keyboard

# Состояния для FSM
class AdminStates(StatesGroup):
    waiting_for_quiz_data = State()
    confirming_quiz_activation = State()

class QuizStates(StatesGroup):
    answering_questions = State()
    waiting_for_email = State()

def register_handlers(dp: Dispatcher):
    # Обработчик команды /start
    @dp.message_handler(commands=['start'])
    async def send_welcome(message: types.Message):
        username = message.from_user.username
        if await is_admin(username):
            await message.reply(
                "Добро пожаловать в панель администратора.\nВведите /help для просмотра доступных команд.",
                reply_markup=admin_main_menu()
            )
        else:
            await message.reply(
                "Привет! Готовы начать квиз? Напишите /quiz, чтобы начать.\nВведите /help для просмотра доступных команд."
            )

    # Обработчик команды /help
    @dp.message_handler(commands=['help'])
    async def help_handler(message: types.Message):
        username = message.from_user.username
        if await is_admin(username):
            help_text = (
                "Доступные команды для администратора:\\n"
                "/add\\_quiz \\- Добавить новый квиз\\n"
                "/activate\\_quiz \\- Активировать квиз\\n"
                "/deactivate\\_quiz \\- Деактивировать квиз\\n"
                "/delete\\_quiz \\- Удалить квиз\\n"
                "/add\\_admin @username \\- Добавить администратора\\n"
                "/remove\\_admin @username \\- Удалить администратора\\n"
                "/help \\- Показать это сообщение\\n\\n"
                "**Добавление квиза\\:**\\n"
                "Чтобы добавить новый квиз, используйте команду /add\\_quiz и следуйте инструкциям\\. "
                "Вам нужно отправить данные квиза в следующем формате\\:\\n\\n"
                "Название квиза\\: Название вашего квиза\\n"
                "Вопросы\\:\\n"
                "1\\. Текст вопроса 1\\n"
                "Ответ\\: Правильный ответ на вопрос 1\\n"
                "2\\. Текст вопроса 2\\n"
                "Ответ\\: Правильный ответ на вопрос 2\\n"
                "\\.\\.\\.\\n\\n"
                "**Пример\\:**\\n"
                "Название квиза\\: Общие знания\\n"
                "Вопросы\\:\\n"
                "1\\. Столица Франции\\?\\n"
                "Ответ\\: Париж\\n"
                "2\\. 2 \\+ 2 \\= \\?\\n"
                "Ответ\\: 4\\n"
            )
            await message.reply(help_text, parse_mode='MarkdownV2')
        else:
            help_text = (
                "Доступные команды для пользователя:\\n"
                "/quiz \\- Начать квиз\\n"
                "/help \\- Показать это сообщение\\n"
            )
            await message.reply(help_text, parse_mode='MarkdownV2')

    # Обработчик команды /add_quiz
    async def add_quiz_handler(user_id):
        username = await get_username(user_id)
        if not await is_admin(username):
            await bot.send_message(user_id, "У вас нет прав для выполнения этой команды.")
            return
        instructions = (
            "Пожалуйста, отправьте данные квиза в следующем формате:\n\n"
            "Название квиза: Название вашего квиза\n"
            "Вопросы:\n"
            "1. Текст вопроса 1\n"
            "Ответ: Правильный ответ на вопрос 1\n"
            "2. Текст вопроса 2\n"
            "Ответ: Правильный ответ на вопрос 2\n"
            "...\n\n"
            "Пример:\n"
            "Название квиза: Общие знания\n"
            "Вопросы:\n"
            "1. Столица Франции?\n"
            "Ответ: Париж\n"
            "2. 2 + 2 = ?\n"
            "Ответ: 4\n"
        )
        await bot.send_message(user_id, instructions)
        await AdminStates.waiting_for_quiz_data.set()

    # Обработчик получения данных квиза
    @dp.message_handler(state=AdminStates.waiting_for_quiz_data)
    async def process_quiz_data(message: types.Message, state: FSMContext):
        quiz_data = message.text
        try:
            quiz_info = parse_quiz_data(quiz_data)
            await save_quiz_to_db(quiz_info)
            await message.reply("Квиз успешно создан и сохранен.")
            await state.finish()
        except Exception as e:
            logging.exception("Ошибка при парсинге квиза.")
            await message.reply(f"Ошибка при создании квиза: {str(e)}\nПожалуйста, проверьте формат и попробуйте снова.")
            await state.finish()

    # Функция для получения юзернейма по user_id
    async def get_username(user_id):
        user = await bot.get_chat(user_id)
        return user.username

    # Обработчик нажатий на кнопки меню администратора
    @dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
    async def process_admin_menu(callback_query: types.CallbackQuery):
        action = callback_query.data
        username = callback_query.from_user.username
        user_id = callback_query.from_user.id
        logging.info(f"Проверка администратора в CallbackQuery: '{username}'")
        if not await is_admin(username):
            await callback_query.answer("У вас нет прав для выполнения этой команды.", show_alert=True)
            return

        if action == 'admin_add_quiz':
            await add_quiz_handler(user_id)
        elif action == 'admin_activate_quiz':
            await activate_quiz_handler(user_id)
        elif action == 'admin_deactivate_quiz':
            await deactivate_quiz_handler(user_id)
        elif action == 'admin_delete_quiz':
            await delete_quiz_handler(user_id)
        elif action == 'admin_add_admin':
            await bot.send_message(user_id, "Пожалуйста, используйте команду:\n/add_admin @username")
        elif action == 'admin_help':
            await bot.send_message(user_id, "Введите /help для просмотра доступных команд.")
        await callback_query.answer()

    # Команда /activate_quiz
    async def activate_quiz_handler(user_id):
        username = await get_username(user_id)
        if not await is_admin(username):
            await bot.send_message(user_id, "У вас нет прав для выполнения этой команды.")
            return
        async with async_session() as session:
            result = await session.execute(
                Quiz.__table__.select().where(Quiz.is_active == False)
            )
            quizzes = result.fetchall()
            if not quizzes:
                await bot.send_message(user_id, "Нет неактивных квизов.")
                return
            await bot.send_message(user_id, "Выберите квиз для активации:", reply_markup=quiz_list_keyboard(quizzes, 'activate'))

    # Команда /deactivate_quiz
    async def deactivate_quiz_handler(user_id):
        username = await get_username(user_id)
        if not await is_admin(username):
            await bot.send_message(user_id, "У вас нет прав для выполнения этой команды.")
            return
        async with async_session() as session:
            result = await session.execute(
                Quiz.__table__.select().where(Quiz.is_active == True)
            )
            quizzes = result.fetchall()
            if not quizzes:
                await bot.send_message(user_id, "Нет активных квизов.")
                return
            await bot.send_message(user_id, "Выберите квиз для деактивации:", reply_markup=quiz_list_keyboard(quizzes, 'deactivate'))

    # Команда /delete_quiz
    async def delete_quiz_handler(user_id):
        username = await get_username(user_id)
        if not await is_admin(username):
            await bot.send_message(user_id, "У вас нет прав для выполнения этой команды.")
            return
        async with async_session() as session:
            result = await session.execute(
                Quiz.__table__.select()
            )
            quizzes = result.fetchall()
            if not quizzes:
                await bot.send_message(user_id, "Нет квизов для удаления.")
                return
            await bot.send_message(user_id, "Выберите квиз для удаления:", reply_markup=quiz_list_keyboard(quizzes, 'delete'))

    # Обработчик нажатий на кнопки активации, деактивации и удаления квиза
    @dp.callback_query_handler(lambda c: c.data.startswith(('activate_', 'deactivate_', 'delete_')))
    async def process_quiz_action(callback_query: types.CallbackQuery):
        action, quiz_id = callback_query.data.split('_')
        quiz_id = int(quiz_id)
        username = callback_query.from_user.username
        user_id = callback_query.from_user.id
        logging.info(f"Проверка администратора в CallbackQuery: '{username}'")
        if not await is_admin(username):
            await callback_query.answer("У вас нет прав для выполнения этой команды.", show_alert=True)
            return

        if action == 'activate':
            async with async_session() as session:
                await session.execute(
                    Quiz.__table__.update()
                    .where(Quiz.quiz_id == quiz_id)
                    .values(is_active=True)
                )
                await session.commit()
            await callback_query.answer("Квиз активирован.", show_alert=True)
        elif action == 'deactivate':
            async with async_session() as session:
                await session.execute(
                    Quiz.__table__.update()
                    .where(Quiz.quiz_id == quiz_id)
                    .values(is_active=False)
                )
                await session.commit()
            await callback_query.answer("Квиз деактивирован.", show_alert=True)
        elif action == 'delete':
            # Запрашиваем подтверждение
            await bot.send_message(
                user_id,
                "Вы уверены, что хотите удалить этот квиз?",
                reply_markup=confirm_keyboard(f'confirm_delete_confirm_{quiz_id}')
            )
        await callback_query.answer()

    # Обработчик подтверждения удаления квиза
    @dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete_confirm_'))
    async def confirm_delete_quiz(callback_query: types.CallbackQuery):
        quiz_id = int(callback_query.data.split('_')[-1])
        username = callback_query.from_user.username
        user_id = callback_query.from_user.id
        logging.info(f"Проверка администратора в CallbackQuery: '{username}'")
        if not await is_admin(username):
            await callback_query.answer("У вас нет прав для выполнения этой команды.", show_alert=True)
            return

        async with async_session() as session:
            # Удаляем ответы
            await session.execute(
                Answer.__table__.delete().where(
                    Answer.question_id.in_(
                        session.query(Question.question_id).filter(
                            Question.quiz_id == quiz_id
                        )
                    )
                )
            )
            # Удаляем вопросы
            await session.execute(
                Question.__table__.delete().where(Question.quiz_id == quiz_id)
            )
            # Удаляем квиз
            await session.execute(
                Quiz.__table__.delete().where(Quiz.quiz_id == quiz_id)
            )
            await session.commit()
        await callback_query.answer("Квиз успешно удален.", show_alert=True)

    # Обработчик команды /quiz для пользователей
    @dp.message_handler(commands=['quiz'])
    async def start_quiz(message: types.Message, state: FSMContext):
        async with async_session() as session:
            result = await session.execute(
                Quiz.__table__.select().where(Quiz.is_active == True)
            )
            quiz_row = result.fetchone()
            if not quiz_row:
                await message.reply("Сейчас нет доступных квизов.")
                return
            quiz = Quiz(**quiz_row)
            result = await session.execute(
                Question.__table__.select().where(Question.quiz_id == quiz.quiz_id)
            )
            questions = result.fetchall()
            await state.update_data(
                questions=[Question(**q) for q in questions],
                current_question=0,
                correct_answers=0,
                quiz_id=quiz.quiz_id
            )
            # Создаем попытку
            new_attempt = UserAttempt(
                user_id=message.from_user.id,
                quiz_id=quiz.quiz_id,
                timestamp=datetime.utcnow(),
                correct_answers=0,
                is_winner=False
            )
            session.add(new_attempt)
            await session.commit()
            await state.update_data(attempt_id=new_attempt.attempt_id)
            await send_question(message.chat.id, state)
            await QuizStates.answering_questions.set()

    # Функция отправки вопроса
    async def send_question(chat_id, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        current_question = data['current_question']

        if current_question < len(questions):
            question = questions[current_question]
            await bot.send_message(chat_id, question.text)
        else:
            # Квиз завершен
            await finish_quiz(chat_id, state)

    # Обработка ответов пользователей
    @dp.message_handler(state=QuizStates.answering_questions)
    async def process_answer(message: types.Message, state: FSMContext):
        user_answer = message.text.strip().lower()
        data = await state.get_data()
        correct_answers = data.get('correct_answers', 0)
        current_question = data.get('current_question', 0)
        questions = data['questions']
        attempt_id = data['attempt_id']
        question = questions[current_question]

        async with async_session() as session:
            result = await session.execute(
                Answer.__table__.select().where(Answer.question_id == question.question_id)
            )
            correct_answer_row = result.fetchone()
            if correct_answer_row:
                correct_answer = Answer(**correct_answer_row)
                correct_answer_text = correct_answer.text.strip().lower()
            else:
                await message.reply("Ошибка: не найден правильный ответ на вопрос.")
                await state.finish()
                return

            if user_answer == correct_answer_text:
                correct_answers += 1

            # Сохраняем ответ пользователя
            new_response = UserResponse(
                attempt_id=attempt_id,
                question_id=question.question_id,
                selected_answer_text=user_answer,
            )
            session.add(new_response)
            await session.commit()

        current_question += 1
        await state.update_data(
            correct_answers=correct_answers,
            current_question=current_question,
        )

        await send_question(message.chat.id, state)

    # Завершение квиза
    async def finish_quiz(chat_id, state: FSMContext):
        data = await state.get_data()
        correct_answers = data.get('correct_answers', 0)
        attempt_id = data['attempt_id']
        async with async_session() as session:
            # Обновляем попытку
            await session.execute(
                UserAttempt.__table__.update()
                .where(UserAttempt.attempt_id == attempt_id)
                .values(correct_answers=correct_answers)
            )
            await session.commit()
        await bot.send_message(chat_id, f"Квиз завершен! Вы ответили правильно на {correct_answers} вопросов.")
        await state.finish()

    # Обработчики для управления администраторами
    @dp.message_handler(commands=['add_admin'])
    async def add_admin_handler(message: types.Message):
        username = message.from_user.username
        if not await is_admin(username):
            await message.reply("У вас нет прав для выполнения этой команды.")
            return
        args = message.get_args()
        if not args:
            await message.reply("Пожалуйста, укажите юзернейм нового администратора после команды, например:\n/add_admin @username")
            return
        new_admin_username = args.strip().lstrip('@').lower()
        async with async_session() as session:
            # Проверяем, есть ли уже такой администратор
            result = await session.execute(
                Admin.__table__.select().where(Admin.username.ilike(new_admin_username))
            )
            existing_admin = result.fetchone()
            if existing_admin:
                await message.reply(f"Пользователь @{new_admin_username} уже является администратором.")
                return
            new_admin = Admin(username=new_admin_username)
            session.add(new_admin)
            try:
                await session.commit()
                await message.reply(f"Пользователь @{new_admin_username} добавлен в список администраторов.")
            except Exception as e:
                await message.reply(f"Ошибка при добавлении администратора: {e}")

    @dp.message_handler(commands=['remove_admin'])
    async def remove_admin_handler(message: types.Message):
        username = message.from_user.username
        if not await is_admin(username):
            await message.reply("У вас нет прав для выполнения этой команды.")
            return
        args = message.get_args()
        if not args:
            await message.reply("Пожалуйста, укажите юзернейм администратора для удаления после команды, например:\n/remove_admin @username")
            return
        admin_username = args.strip().lstrip('@').lower()
        async with async_session() as session:
            result = await session.execute(
                Admin.__table__.select().where(Admin.username.ilike(admin_username))
            )
            admin = result.fetchone()
            if admin:
                await session.execute(
                    Admin.__table__.delete().where(Admin.username.ilike(admin_username))
                )
                await session.commit()
                await message.reply(f"Пользователь @{admin_username} удален из списка администраторов.")
            else:
                await message.reply("Такой администратор не найден.")

    # Обработчик для всех сообщений (для тестирования)
    @dp.message_handler()
    async def handle_all_messages(message: types.Message):
        logging.info(f"Получено сообщение: {message.text}")
        await message.reply("Бот получил ваше сообщение.")

    # Функция для парсинга данных квиза из сообщения
    def parse_quiz_data(text):
        lines = text.strip().split('\n')
        quiz_info = {}
        questions = []
        current_question = None
        for line in lines:
            line = line.strip()
            if line.startswith('Название квиза:'):
                quiz_info['title'] = line[len('Название квиза:'):].strip()
            elif line.lower() == 'вопросы:':
                continue
            elif line.startswith(tuple(f"{i}." for i in range(1, 101))):
                if current_question:
                    questions.append(current_question)
                current_question = {'text': line[line.find('.') + 1:].strip(), 'answer': ''}
            elif line.startswith('Ответ:'):
                if current_question:
                    current_question['answer'] = line[len('Ответ:'):].strip()
        if current_question:
            questions.append(current_question)
        quiz_info['questions'] = questions
        return quiz_info

    # Функция для сохранения квиза в базу данных
    async def save_quiz_to_db(quiz_info):
        async with async_session() as session:
            new_quiz = Quiz(
                title=quiz_info['title'],
                is_active=False,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(days=7),
                question_count=len(quiz_info['questions']),
            )
            session.add(new_quiz)
            await session.commit()
            for q in quiz_info['questions']:
                new_question = Question(
                    quiz_id=new_quiz.quiz_id,
                    text=q['text']
                )
                session.add(new_question)
                await session.commit()
                new_answer = Answer(
                    question_id=new_question.question_id,
                    text=q['answer']
                )
                session.add(new_answer)
                await session.commit()
            quiz_info['quiz_id'] = new_quiz.quiz_id

# Регистрируем обработчики
register_handlers(dp)
