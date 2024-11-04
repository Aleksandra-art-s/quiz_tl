# handlers.py

from aiogram import types, Dispatcher
from config import ADMIN_USERNAMES
from database import (
    async_session,
    User,
    Quiz,
    Question,
    Answer,
    UserAttempt,
    UserResponse,
)
from datetime import datetime, timedelta
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from keyboards import admin_main_menu, confirm_keyboard
from aiogram.utils.exceptions import MessageNotModified

# Импортируем bot из bot.py
from bot import bot, dp

def is_admin(username):
    return username in ADMIN_USERNAMES

# Состояния для машины состояний
class AdminStates(StatesGroup):
    waiting_for_quiz_title = State()
    waiting_for_question_text = State()
    waiting_for_answer_options = State()
    confirming_quiz_activation = State()

class QuizStates(StatesGroup):
    answering_questions = State()
    waiting_for_email = State()

def register_handlers(dp: Dispatcher):
    # Обработчик команды /start
    @dp.message_handler(commands=['start'])
    async def send_welcome(message: types.Message):
        username = message.from_user.username
        if is_admin(username):
            await message.reply(
                "Добро пожаловать в панель администратора.",
                reply_markup=admin_main_menu()
            )
        else:
            await message.reply(
                "Привет! Готовы начать квиз? Напишите /quiz, чтобы начать."
            )

    # Обработчик команды /quiz для пользователей
    @dp.message_handler(commands=['quiz'])
    async def start_quiz(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        username = message.from_user.username

        async with async_session() as session:
            # Проверяем, есть ли активный квиз
            result = await session.execute(
                Quiz.__table__.select().where(Quiz.is_active == True)
            )
            quiz = result.fetchone()
            if not quiz:
                await message.reply("В данный момент нет активных квизов.")
                return

            # Проверяем, участвовал ли пользователь в этом квизе и выигрывал ли
            result = await session.execute(
                UserAttempt.__table__.select().where(
                    (UserAttempt.user_id == user_id)
                    & (UserAttempt.quiz_id == quiz.quiz_id)
                    & (UserAttempt.is_winner == True)
                )
            )
            attempt = result.fetchone()
            if attempt:
                await message.reply(
                    "Вы уже выиграли в этом квизе. Дождитесь следующего квиза!"
                )
                return

            # Проверяем, участвовал ли пользователь сегодня
            result = await session.execute(
                UserAttempt.__table__.select().where(
                    (UserAttempt.user_id == user_id)
                    & (UserAttempt.quiz_id == quiz.quiz_id)
                ).order_by(UserAttempt.attempt_time.desc())
            )
            attempt = result.fetchone()
            if attempt and attempt.attempt_time.date() == datetime.utcnow().date():
                await message.reply(
                    "Вы уже участвовали в квизе сегодня. Попробуйте снова завтра."
                )
                return

            # Если пользователь новый, добавляем его в базу данных
            result = await session.execute(
                User.__table__.select().where(User.user_id == user_id)
            )
            user = result.fetchone()
            if not user:
                new_user = User(user_id=user_id, username=username)
                session.add(new_user)
                await session.commit()

            # Начинаем квиз
            await message.reply("Начинаем квиз!")

            # Получаем вопросы
            result = await session.execute(
                Question.__table__.select().where(
                    Question.quiz_id == quiz.quiz_id
                )
            )
            questions = result.fetchall()

            # Сохраняем попытку пользователя
            new_attempt = UserAttempt(
                user_id=user_id,
                quiz_id=quiz.quiz_id,
                attempt_time=datetime.utcnow(),
                correct_answers=0,
                is_winner=False,
            )
            session.add(new_attempt)
            await session.commit()

            # Сохраняем данные в FSMContext
            await state.update_data(
                attempt_id=new_attempt.attempt_id,
                questions=questions,
                current_question=0,
                correct_answers=0,
            )

            # Устанавливаем состояние
            await QuizStates.answering_questions.set()

            # Отправляем первый вопрос
            await send_question(message.chat.id, state)

    # Функция для отправки вопроса
    async def send_question(chat_id, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        current_question = data['current_question']

        if current_question < len(questions):
            question = questions[current_question]

            async with async_session() as session:
                # Получаем ответы на вопрос
                result = await session.execute(
                    Answer.__table__.select().where(
                        Answer.question_id == question.question_id
                    )
                )
                answers = result.fetchall()

            # Создаем кнопки с вариантами ответов
            buttons = []
            for a in answers:
                buttons.append(
                    types.InlineKeyboardButton(
                        a.text,
                        callback_data=f"answer_{a.answer_id}"
                    )
                )

            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(*buttons)

            await bot.send_message(chat_id, question.text, reply_markup=keyboard)
        else:
            # Квиз завершен
            await finish_quiz(chat_id, state)

    # Обработчик ответов на вопросы
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('answer_'), state=QuizStates.answering_questions)
    async def process_answer(callback_query: types.CallbackQuery, state: FSMContext):
        data = callback_query.data.split('_')
        answer_id = int(data[1])
        user_id = callback_query.from_user.id

        async with async_session() as session:
            # Проверяем, правильный ли ответ
            result = await session.execute(
                Answer.__table__.select().where(Answer.answer_id == answer_id)
            )
            answer = result.fetchone()

            data = await state.get_data()
            correct_answers = data['correct_answers']
            current_question = data['current_question']
            questions = data['questions']
            attempt_id = data['attempt_id']

            if answer.is_correct:
                correct_answers += 1

            current_question += 1

            # Обновляем данные в FSMContext
            await state.update_data(
                correct_answers=correct_answers,
                current_question=current_question,
            )

            # Сохраняем ответ пользователя
            new_response = UserResponse(
                attempt_id=attempt_id,
                question_id=answer.question_id,
                selected_answer_id=answer.answer_id,
            )
            session.add(new_response)
            await session.commit()

            await bot.answer_callback_query(callback_query.id)
            await send_question(callback_query.from_user.id, state)

    # Функция для завершения квиза
    async def finish_quiz(chat_id, state: FSMContext):
        data = await state.get_data()
        correct_answers = data['correct_answers']
        total_questions = len(data['questions'])
        attempt_id = data['attempt_id']

        async with async_session() as session:
            # Обновляем информацию о попытке
            is_winner = correct_answers == total_questions
            await session.execute(
                UserAttempt.__table__.update()
                .where(UserAttempt.attempt_id == attempt_id)
                .values(
                    correct_answers=correct_answers,
                    is_winner=is_winner,
                )
            )
            await session.commit()

        if is_winner:
            await bot.send_message(
                chat_id,
                f'Поздравляем! Вы ответили правильно на все вопросы.',
            )
            await bot.send_message(
                chat_id,
                'Пожалуйста, введите ваш email для получения приза:'
            )
            # Устанавливаем состояние ожидания email
            await QuizStates.waiting_for_email.set()
        else:
            await bot.send_message(
                chat_id,
                f'Вы ответили правильно на {correct_answers} из {total_questions} вопросов. Попробуйте снова завтра!',
            )
            # Сбрасываем состояние
            await state.finish()

    # Обработчик ввода email
    @dp.message_handler(state=QuizStates.waiting_for_email)
    async def process_email(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        email = message.text.strip()

        # Простая проверка на наличие символа '@' и '.'
        if '@' in email and '.' in email:
            async with async_session() as session:
                # Обновляем email пользователя
                await session.execute(
                    User.__table__.update()
                    .where(User.user_id == user_id)
                    .values(email=email)
                )
                await session.commit()

            await message.reply(
                'Спасибо! Ваш email сохранен. Мы свяжемся с вами для получения приза.'
            )
            # Сбрасываем состояние
            await state.finish()
        else:
            await message.reply(
                'Похоже, вы ввели некорректный email. Пожалуйста, попробуйте снова.'
            )

    # Обработчик нажатий на кнопки администратора
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('admin_'))
    async def process_admin_callback(callback_query: types.CallbackQuery, state: FSMContext):
        username = callback_query.from_user.username
        if not is_admin(username):
            await callback_query.answer("У вас нет прав для выполнения этой команды.", show_alert=True)
            return

        action = callback_query.data

        if action == 'admin_add_quiz':
            await callback_query.message.edit_text("Введите название нового квиза:")
            await AdminStates.waiting_for_quiz_title.set()
        elif action == 'admin_list_quizzes':
            async with async_session() as session:
                result = await session.execute(
                    Quiz.__table__.select()
                )
                quizzes = result.fetchall()

                if not quizzes:
                    await callback_query.message.edit_text("Квизы не найдены.")
                    return

                response = "Список квизов:\n"
                for quiz in quizzes:
                    status = "Активен" if quiz.is_active else "Не активен"
                    response += f"ID: {quiz.quiz_id}, Название: {quiz.title}, Статус: {status}\n"

                await callback_query.message.edit_text(response)
        elif action == 'admin_help':
            await callback_query.message.edit_text(
                "Доступные команды:\n"
                "/start - Главное меню\n"
                "Используйте кнопки для управления квизами."
            )
        await callback_query.answer()

    # Обработчик ввода названия квиза
    @dp.message_handler(state=AdminStates.waiting_for_quiz_title)
    async def process_quiz_title(message: types.Message, state: FSMContext):
        quiz_title = message.text.strip()
        await state.update_data(quiz_title=quiz_title)

        async with async_session() as session:
            new_quiz = Quiz(
                title=quiz_title,
                is_active=False,  # По умолчанию квиз не активен
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(days=7),
                question_count=0,  # Пока вопросов нет
            )
            session.add(new_quiz)
            await session.commit()

            await state.update_data(quiz_id=new_quiz.quiz_id)

        await message.reply("Квиз создан. Теперь введите текст первого вопроса:")
        await AdminStates.waiting_for_question_text.set()

    # Обработчик ввода текста вопроса
    @dp.message_handler(state=AdminStates.waiting_for_question_text)
    async def process_question_text(message: types.Message, state: FSMContext):
        question_text = message.text.strip()
        await state.update_data(question_text=question_text, answers=[])

        await message.reply(
            "Введите варианты ответов в формате:\n"
            "Текст ответа | правильный (да/нет)\n"
            "Вводите по одному варианту на сообщение. Когда закончите, отправьте команду /done."
        )
        await AdminStates.waiting_for_answer_options.set()

    # Обработчик ввода вариантов ответов
    @dp.message_handler(state=AdminStates.waiting_for_answer_options)
    async def process_answer_options(message: types.Message, state: FSMContext):
        if message.text.strip() == '/done':
            data = await state.get_data()
            answers = data['answers']
            if len(answers) < 2:
                await message.reply("Должно быть минимум 2 варианта ответа.")
                return

            correct_answers = [ans for ans in answers if ans['is_correct']]
            if len(correct_answers) == 0:
                await message.reply("Должен быть хотя бы один правильный ответ.")
                return

            quiz_id = data['quiz_id']
            question_text = data['question_text']

            async with async_session() as session:
                # Создаем вопрос
                new_question = Question(
                    quiz_id=quiz_id,
                    text=question_text
                )
                session.add(new_question)
                await session.commit()

                # Добавляем ответы
                for ans in answers:
                    new_answer = Answer(
                        question_id=new_question.question_id,
                        text=ans['text'],
                        is_correct=ans['is_correct']
                    )
                    session.add(new_answer)
                await session.commit()

                # Обновляем количество вопросов в квизе
                await session.execute(
                    Quiz.__table__.update()
                    .where(Quiz.quiz_id == quiz_id)
                    .values(question_count=Quiz.question_count + 1)
                )
                await session.commit()

            await message.reply("Вопрос и ответы сохранены. Хотите добавить еще один вопрос?", reply_markup=confirm_keyboard('add_another_question'))
            await AdminStates.confirming_quiz_activation.set()
        else:
            # Обрабатываем вариант ответа
            parts = message.text.strip().split('|')
            if len(parts) != 2:
                await message.reply("Пожалуйста, используйте формат:\nТекст ответа | правильный (да/нет)")
                return

            answer_text = parts[0].strip()
            is_correct_str = parts[1].strip().lower()
            is_correct = is_correct_str == 'да'

            data = await state.get_data()
            answers = data['answers']
            answers.append({
                'text': answer_text,
                'is_correct': is_correct
            })
            await state.update_data(answers=answers)

            await message.reply("Ответ сохранен. Введите следующий вариант или отправьте /done, чтобы закончить.")

    # Обработчик подтверждения активации квиза или добавления еще вопросов
    @dp.callback_query_handler(lambda c: c.data.startswith('confirm_') or c.data == 'cancel_action', state=AdminStates.confirming_quiz_activation)
    async def process_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
        if callback_query.data == 'confirm_add_another_question':
            await callback_query.message.edit_text("Введите текст следующего вопроса:")
            await AdminStates.waiting_for_question_text.set()
        elif callback_query.data == 'confirm_activate_quiz':
            data = await state.get_data()
            quiz_id = data['quiz_id']

            async with async_session() as session:
                await session.execute(
                    Quiz.__table__.update()
                    .where(Quiz.quiz_id == quiz_id)
                    .values(is_active=True)
                )
                await session.commit()

            await callback_query.message.edit_text("Квиз активирован и готов для пользователей.")
            await state.finish()
        elif callback_query.data == 'cancel_action':
            await callback_query.message.edit_text("Действие отменено. Возвращаюсь в главное меню.", reply_markup=admin_main_menu())
            await state.finish()
        await callback_query.answer()

    # Обработчик любых сообщений от администратора для возврата в главное меню
    @dp.message_handler(lambda message: is_admin(message.from_user.username))
    async def admin_default(message: types.Message):
        await message.reply("Выберите действие из меню ниже.", reply_markup=admin_main_menu())

