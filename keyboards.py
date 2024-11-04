# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура для администратора
def admin_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Добавить квиз", callback_data="admin_add_quiz"),
        InlineKeyboardButton("Список квизов", callback_data="admin_list_quizzes"),
        InlineKeyboardButton("Помощь", callback_data="admin_help"),
    )
    return keyboard

# Клавиатура для подтверждения действий
def confirm_keyboard(action):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Да", callback_data=f"confirm_{action}"),
        InlineKeyboardButton("Нет", callback_data="cancel_action"),
    )
    return keyboard
