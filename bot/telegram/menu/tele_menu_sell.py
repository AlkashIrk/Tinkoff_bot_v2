from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.service_for_base import *
from bot.database.telegram_func import force_sell
from bot.telegram.menu.tele_menu_message import *
from bot.telegram.menu.telegram_check_user import check_user

menu_message = global_var.menu_message
last_message_id = global_var.last_message_id


def redraw_menu(bot):
    menu_message_id = menu_message["id"]
    if last_message_id > menu_message_id:
        bot.callback_query.message.delete()
        menu_message_id = bot.callback_query.message.reply_text(
            text=menu_message["text"],
            reply_markup=menu_message["keyboard"]
        )
        menu_message["id"] = menu_message_id.message_id


def sell_menu(bot, update):
    from bot.telegram.menu.tele_menu_main import main_menu_keyboard
    global menu_message
    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        # base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.base
    else:
        return

    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = main_menu_message()
    menu_message["keyboard"] = main_menu_keyboard()
    bot.callback_query.message.edit_text(sell_menu_message(),
                                         reply_markup=sell_menu_keyboard(base=base_name_private))


def stock_force_sell(bot, update):
    '''
    Принудительная продажа акции
    '''
    global menu_message
    global last_message_id

    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        # base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.base
    else:
        return

    response = bot.callback_query.data
    ticker = response.split("!")[1]
    if ticker is not None:
        force_sell(
            ticker,
            user_id=user_id
        )

    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        base_name_private = user_id.base
    else:
        return

    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = sell_menu_message()  # main_menu_message()
    menu_message["keyboard"] = sell_menu_keyboard(base=base_name_private)  # main_menu_keyboard()
    last_message_id = menu_message["id"] + 1

    redraw_menu(bot)


############################ Keyboards #########################################

def sell_menu_keyboard(base):
    lots_to_sell = last_candle_info(base=base)

    force_sell_count = 0
    keyboard = []
    for stock in lots_to_sell:
        share_info: InitialShared = lots_to_sell[stock]["object"]
        if lots_to_sell[stock]["lots"] > 0:
            force_sell_count += 1
            keyboard.append(
                [InlineKeyboardButton(
                    "%s (%s шт.)\n+%.2f%s" % (stock, lots_to_sell[stock]["lots"], lots_to_sell[stock]["profit"],
                                              CurrencySign.value_of(share_info.currency)),
                    callback_data="stock_force_sell!%s" % stock)]
            )

    if force_sell_count == 0:
        keyboard = [[InlineKeyboardButton("Акций на продажу нет", callback_data="main")]]

    keyboard.append([InlineKeyboardButton("Назад", callback_data="main")])

    return InlineKeyboardMarkup(keyboard)
