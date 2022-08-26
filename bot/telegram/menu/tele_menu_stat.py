from time import sleep

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.service_for_base import *
from bot.database.stat_info import money_profit
from bot.telegram.menu.tele_menu_message import *
from bot.telegram.menu.telegram_check_user import check_user

menu_message = global_var.menu_message
last_message_id = global_var.last_message_id


def redraw_menu(bot):
    global menu_message
    menu_message_id = menu_message["id"]
    if last_message_id > menu_message_id:
        bot.callback_query.message.delete()
        menu_message_id = bot.callback_query.message.reply_text(
            text=menu_message["text"],
            reply_markup=menu_message["keyboard"]
        )
        menu_message["id"] = menu_message_id.message_id


def statistic_menu(bot, update):
    global menu_message
    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = statistic_menu_message()
    menu_message["keyboard"] = statistic_menu_keyboard()
    bot.callback_query.message.edit_text(statistic_menu_message(),
                                         reply_markup=statistic_menu_keyboard())


def stocks_menu(bot, update):
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
    menu_message["text"] = statistic_menu_message()
    menu_message["keyboard"] = statistic_menu_keyboard()
    bot.callback_query.message.edit_text(statistic_menu_message(),
                                         reply_markup=stocks_menu_keyboard(base=base_name_private))


def stock_stat_menu(bot, update):
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
    if ticker == "All":
        message_list = stock_info(base_name=base_name_private)
    else:
        message_list = stock_info(ticker=ticker, base_name=base_name_private)

    for data in message_list:
        message = bot.callback_query.message.reply_text(
            text=data,
            parse_mode="markdown",
            disable_web_page_preview=True
        )
        last_message_id = message.message_id
        sleep(0.75)
    redraw_menu(bot)


def stat_today(bot, update):
    global last_message_id

    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        # base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.base
    else:
        return

    profit = money_profit(today_open=1, today_close=0, base=base_name_private)
    data = "Прибыль за сегодня:"

    for currency in profit:
        text = "\n\t\t\t\t\t%s %.2f%s" % (currency, profit.get(currency), CurrencySign.value_of(currency))
        data = data + text

    message = bot.callback_query.message.reply_text(
        text=data,
        parse_mode="html",
        disable_web_page_preview=True
    )
    last_message_id = message.message_id
    sleep(0.75)

    redraw_menu(bot)


def stat_yesterday(bot, update):
    global last_message_id

    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        # base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.base
    else:
        return

    profit = money_profit(today_open=0, today_close=-1, base=base_name_private)

    data = "Прибыль за вчерашний день:" % profit
    for currency in profit:
        text = "\n\t\t\t\t\t%s %.2f%s" % (currency, profit.get(currency), CurrencySign.value_of(currency))
        data = data + text

    message = bot.callback_query.message.reply_text(
        text=data,
        parse_mode="html",
        disable_web_page_preview=True
    )
    last_message_id = message.message_id
    sleep(0.75)

    redraw_menu(bot)


def balance_submenu(bot, update):
    global last_message_id

    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        base_name_private = user_id.base
    else:
        return

    info = UserBalance(base=base_name_private)
    info_message = info.get_info()

    for info_m in info_message:
        message = bot.callback_query.message.reply_text(
            text=info_m,
            parse_mode="html",
            disable_web_page_preview=True
        )

        last_message_id = message.message_id
        sleep(0.75)

    redraw_menu(bot)


############################ Keyboards #########################################
def statistic_menu_keyboard():
    keyboard = [[InlineKeyboardButton("На текущий день", callback_data="stat_today")],
                [InlineKeyboardButton("За вчерашний день", callback_data="stat_yesterday")],
                [InlineKeyboardButton("Распределение баланса", callback_data="info_balance")],
                [InlineKeyboardButton("Подробно по акциям", callback_data="stocks_orders")],
                [InlineKeyboardButton("Назад", callback_data="main")]
                # [InlineKeyboardButton("Выйти", callback_data="cancel")]
                ]
    return InlineKeyboardMarkup(keyboard)


def stocks_menu_keyboard(base):
    all_stocks = stock_info(action="dict", base_name=base)
    keyboard = []

    for stock in all_stocks:
        if stock is None:
            continue
        keyboard.append([InlineKeyboardButton("%s" % stock, callback_data="stock_order_stat!%s" % stock)])

    if len(all_stocks) > 1:
        keyboard.append([InlineKeyboardButton("Все акции", callback_data="stock_order_stat!All")])
    else:
        keyboard.append([InlineKeyboardButton("Акций нет", callback_data="statistic_menu")])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="statistic_menu")])

    return InlineKeyboardMarkup(keyboard)
