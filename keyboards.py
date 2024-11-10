# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура для администратора
def admin_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Добавить квиз", callback_data="admin_add_quiz"),
        InlineKeyboardButton("Активация квиза", callback_data="admin_activate_quiz"),
        InlineKeyboardButton("Деактивация квиза", callback_data="admin_deactivate_quiz"),
        InlineKeyboardButton("Удалить квиз", callback_data="admin_delete_quiz"),
        InlineKeyboardButton("Помощь", callback_data="admin_help"),
    )
    return keyboard

# Клавиатура для подтверждения действий
def confirm_keyboard(action):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Да", callback_data=f"confirm_{action}"),
        InlineKeyboardButton("Нет", callback_data="confirm_cancel"),
    )
    return keyboard

# Клавиатура для списка квизов
def quiz_list_keyboard(quizzes, action):
    keyboard = InlineKeyboardMarkup(row_width=1)
    for quiz in quizzes:
        keyboard.add(
            InlineKeyboardButton(
                f"{quiz.title} (ID: {quiz.quiz_id})",
                callback_data=f"{action}_{quiz.quiz_id}"
            )
        )
    return keyboard
