from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import scripts.globals as global_var
from bot.telegram.menu.tele_menu_message import *

menu_message = global_var.menu_message
last_message_id = global_var.last_message_id


def main_menu(bot, update):
    global menu_message
    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = main_menu_message()
    menu_message["keyboard"] = main_menu_keyboard()
    bot.callback_query.message.edit_text(main_menu_message(),
                                         reply_markup=main_menu_keyboard())


def cancel_menu(bot, update):
    bot.callback_query.message.delete()


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Статистика", callback_data="statistic")],
                [InlineKeyboardButton("Продажа", callback_data="sell")],
                [InlineKeyboardButton("Заявки", callback_data="orders")],
                [InlineKeyboardButton("Настройки", callback_data="settings")]
                # [InlineKeyboardButton("Выйти", callback_data="cancel")]
                ]
    return InlineKeyboardMarkup(keyboard)
