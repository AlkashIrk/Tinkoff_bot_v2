from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.service_for_base import *
from bot.database.telegram_func import get_base_by_user
from bot.market_operations.special_func import *
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


def orders_menu(bot, update):
    from bot.telegram.menu.tele_menu_main import main_menu_keyboard
    global menu_message
    menu_message_id = bot.effective_message.message_id
    menu_message["id"] = menu_message_id
    menu_message["text"] = main_menu_message()
    menu_message["keyboard"] = main_menu_keyboard()

    chat_id = bot.effective_chat.id
    user_id = check_user(chat_id)

    if user_id is not None:
        #base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.base
    else:
        return

    bot.callback_query.message.edit_text(orders_menu_message(),
                                         reply_markup=orders_menu_keyboard(base=base_name_private))


def order_decline_confirm(bot, update):
    global last_message_id

    response = bot.callback_query.data

    ticker = response.split("!")[1]
    order_id = response.split("!")[2]
    lots = response.split("!")[3]
    price = response.split("!")[4]

    keyboard = []
    keyboard.append(
        [InlineKeyboardButton(
            "Подтверждаю",
            callback_data="stock_order_del!%s"
                          % order_id)]
    )
    keyboard.append(
        [InlineKeyboardButton(
            "Назад",
            callback_data="orders"
        )]
    )
    data = "Вы собираетесь отменить ордер:\n%s\n   id: %s\n   lots: %s\n   price: %s" \
           % (ticker, split_by_n(order_id, 4), lots, price)
    bot.callback_query.message.edit_text(text=data,
                                         reply_markup=InlineKeyboardMarkup(keyboard))


def order_delete(bot, update):
    global last_message_id

    chat_id = bot.effective_chat.id

    response = bot.callback_query.data
    order_id = response.split("!")[1]

    user_id = check_user(chat_id)

    if user_id is not None:
        #base_name_private = get_base_by_user(user_id)
        base_name_private = user_id.base
    else:
        return

    result, data_dict = try_decline_order(
        order_id,
        base=base_name_private,
        user_id=user_id
    )
    reply_to = None
    if result:
        data = "Ордер отменен\n  id: %s" % split_by_n(order_id, 4)
        try:
            reply_to = data_dict["telegram_mess_id"]
        except:
            reply_to = None
    else:
        data = "Невозможно отменить ордер\n  id: %s" % split_by_n(order_id, 4)
    if reply_to is not None and chat_id == 463139346:
        message = bot.callback_query.message.reply_text(
            text=data,
            parse_mode="markdown",
            disable_web_page_preview=True,
            reply_to_message_id=reply_to
        )
    else:
        message = bot.callback_query.message.reply_text(
            text=data,
            parse_mode="markdown",
            disable_web_page_preview=True
        )
    last_message_id = message.message_id
    redraw_menu(bot)


############################ Keyboards #########################################

def orders_menu_keyboard(base):
    lots_to_sell = stock_in_order_info(action="dict", base_name=base)

    orders_count = 0
    keyboard = []
    for stock in lots_to_sell:
        for order in lots_to_sell[stock]:
            orders_count += 1
            keyboard.append(
                [InlineKeyboardButton(
                    "%s: %s (%s шт.)\n%.2f$" % (order["operation"], stock, order["lots"], order["price"]),
                    callback_data="stock_order_dec!%s!%s!%s!%.2f$"
                                  % (stock, order["id"], order["lots"], order["price"]))]
            )
            # "%s (%s шт.) +%.2f$\nid=%s" % (stock, order["lots"], order["price"], order["id"]),
    if orders_count == 0:
        keyboard = [[InlineKeyboardButton("Активных ордеров нет", callback_data="main")]]

    keyboard.append([InlineKeyboardButton("Назад", callback_data="main")])
    return InlineKeyboardMarkup(keyboard)
