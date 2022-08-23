from time import sleep

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.service_for_base import *
from bot.database.telegram_func import toggle_buy, get_base_by_user
from bot.telegram.menu.tele_menu_message import *
from bot.telegram.menu.telegram_check_user import check_user

menu_message = global_var.menu_message
last_message_id = global_var.last_message_id


def redraw_menu(bot, redraw_force=False):
    global last_message_id
    menu_message_id = menu_message["id"]
    if last_message_id > menu_message_id or redraw_force:
        bot.callback_query.message.delete()
        menu_message_id = bot.callback_query.message.reply_text(
            text=menu_message["text"],
            reply_markup=menu_message["keyboard"]
        )
        menu_message["id"] = menu_message_id.message_id
    last_message_id = menu_message["id"]


def toggle_buy_sell(bot, update):
    global last_message_id
    response = bot.callback_query.data

    operation = response.split("!")[1]

    keyboard = []
    keyboard.append(
        [InlineKeyboardButton(
            "Подтверждаю",
            callback_data="toggle_buy_conf!%s" % operation
        )]
    )
    keyboard.append(
        [InlineKeyboardButton(
            "Назад",
            callback_data="settings"
        )]
    )
    if operation == "ON":
        data = "Вы собираетесь включить автопокупку. Средства будут в обороте."
    if operation == "OFF":
        data = "Вы собираетесь отключить автопокупку. Средства будут накапливаться для вывода денег."
    bot.callback_query.message.edit_text(text=data,
                                         reply_markup=InlineKeyboardMarkup(keyboard))


def toggle_buy_sell_confirm(bot, update):
    from bot.telegram.menu.tele_menu_main import main_menu_keyboard
    global last_message_id

    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = main_menu_message()
    menu_message["keyboard"] = main_menu_keyboard()
    chat_id = bot.effective_chat.id

    response = bot.callback_query.data
    operation = response.split("!")[1]

    user_id = check_user(chat_id)
    user = user_id.name

    if operation == "OFF":
        data = "Автопокупка акций отключена.\nАкции будут только продаваться."
        toggle_buy(operation="SET", value="OFF", user_id=user)
    if operation == "ON":
        data = "Автопокупка акций включена.\nАкции будут покупаться и продаваться."
        toggle_buy(operation="SET", value="ON", user_id=user)

    message = bot.callback_query.message.reply_text(
        text=data,
        parse_mode="markdown",
        disable_web_page_preview=True
    )
    last_message_id = message.message_id
    redraw_menu(bot)


def settings_menu(bot, update):
    global menu_message
    chat_id = bot.effective_chat.id
    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = settings_menu_message()
    menu_message["keyboard"] = settings_menu_keyboard(chat_id=chat_id)
    bot.callback_query.message.edit_text(settings_menu_message(),
                                         reply_markup=settings_menu_keyboard(chat_id=chat_id))


def do_redraw_menu(bot, update):
    from bot.telegram.menu.tele_menu_main import main_menu_keyboard

    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = main_menu_message()
    menu_message["keyboard"] = main_menu_keyboard()
    redraw_menu(bot, redraw_force=True)


def do_rebalance(bot, update):
    from bot.telegram.menu.tele_menu_main import main_menu_keyboard
    global last_message_id

    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = main_menu_message()
    menu_message["keyboard"] = main_menu_keyboard()
    chat_id = bot.effective_chat.id

    data = "Проводим ребаланс акций"

    message = bot.callback_query.message.reply_text(
        text=data,
        parse_mode="markdown",
        disable_web_page_preview=True
    )

    last_message_id = message.message_id

    user_id = check_user(chat_id)

    if user_id is not None:
        #base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.name
    else:
        return

    data = rebalance(base=base_name_private)

    if len(data) > 0:
        for text in data:
            text = text.replace("\n", "\n   ")
            message = bot.callback_query.message.reply_text(
                text=text,
                parse_mode="markdown",
                disable_web_page_preview=True
            )
            sleep(0.5)

    last_message_id = message.message_id

    redraw_menu(bot)


############################ Keyboards #########################################
def settings_menu_keyboard(chat_id):
    user_id = check_user(chat_id)
    user = user_id.name
    only_sell = toggle_buy(operation="GET", user_id=user)

    if only_sell == True:
        text = "Включить автопокупку акций"
        sell_edit = "ON"
    else:
        text = "Автопокупка активна"
        sell_edit = "OFF"

    keyboard = [[InlineKeyboardButton(text, callback_data="toggle_buy_sell!%s" % sell_edit)],
                [InlineKeyboardButton("Сделать ребаланс", callback_data="rebalance")],
                [InlineKeyboardButton("Перерисовать меню", callback_data="redraw_menu")],
                [InlineKeyboardButton("Назад", callback_data="main")],
                [InlineKeyboardButton("Выйти", callback_data="cancel")]
                ]
    return InlineKeyboardMarkup(keyboard)
