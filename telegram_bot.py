from pathlib import Path

import scripts.globals as global_var

global_var.init()
from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackQueryHandler
from bot.telegram.menu.tele_menu_main import *
from bot.telegram.menu.tele_menu_stat import *
from bot.telegram.menu.tele_menu_sell import *
from bot.telegram.menu.tele_menu_orders import *
from bot.telegram.menu.tele_menu_settings import *
from bot.telegram.menu.tele_picture_fun import *

import sys

print('\33]0;Telegram bot\a', end='')
sys.stdout.flush()

log_me = True
token = global_var.telegram_token

if token is None:
    exit()

updater = global_var.updater
last_message_id = global_var.last_message_id

menu_message = {}
white_list = [1366431620, 463139346, 271874166, 704513860]
black_list = {}
photo_path = ["data/photo.jpg", "data/fuck_off.png"]


def log_telegram(message):
    global log_me
    if log_me:
        time_now = datetime.now().strftime("%d-%m-%Y")

        file_name = "logs/telegram/log_%s.log" % time_now
        file_path = Path(file_name)
        Path(file_path.parent).mkdir(parents=True, exist_ok=True)

        with open(file_name, "a+", encoding="utf-8") as full_log:
            print(message, file=full_log)


############################### Bot ############################################
def start(bot, update):
    global black_list
    message_id = bot.message.message_id
    chat_id = bot.message.chat.id

    log_telegram(bot.message)

    if chat_id in black_list:
        black_list[chat_id] += 1
        if black_list[chat_id] == 5:
            text = ""
            updater.bot.send_photo(chat_id=chat_id, photo=open(photo_path[1], "rb"), caption=text)
            # send_picture(bot, chat_id, picture=1)
        updater.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return

    if chat_id not in white_list:
        try:
            black_list[chat_id] += 1
        except:
            black_list[chat_id] = 1
        text = "Вы кто такие, я вас не звал!"
        updater.bot.send_photo(chat_id=chat_id, photo=open(photo_path[0], "rb"), caption=text)
        # updater.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return
    bot.message.reply_text(main_menu_message(),
                           reply_markup=main_menu_keyboard())
    updater.bot.delete_message(chat_id=chat_id, message_id=message_id)


def error(update, context):
    print(f"Update {update} caused error {context.error}")


############################# Handlers #########################################


updater = Updater(token, use_context=True)
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CallbackQueryHandler(main_menu, pattern="main"))
updater.dispatcher.add_handler(CallbackQueryHandler(statistic_menu, pattern="statistic"))
updater.dispatcher.add_handler(CallbackQueryHandler(stocks_menu, pattern="stocks_orders"))
updater.dispatcher.add_handler(CallbackQueryHandler(stock_stat_menu, pattern="stock_order_stat!"))
updater.dispatcher.add_handler(CallbackQueryHandler(stock_force_sell, pattern="stock_force_sell!"))

updater.dispatcher.add_handler(CallbackQueryHandler(order_decline_confirm, pattern="stock_order_dec!"))
updater.dispatcher.add_handler(CallbackQueryHandler(order_delete, pattern="stock_order_del!"))

updater.dispatcher.add_handler(CallbackQueryHandler(sell_menu, pattern="sell"))
updater.dispatcher.add_handler(CallbackQueryHandler(orders_menu, pattern="orders"))
updater.dispatcher.add_handler(CallbackQueryHandler(settings_menu, pattern="settings"))
updater.dispatcher.add_handler(CallbackQueryHandler(do_redraw_menu, pattern="redraw_menu"))

updater.dispatcher.add_handler(CallbackQueryHandler(toggle_buy_sell, pattern="toggle_buy_sell"))
updater.dispatcher.add_handler(CallbackQueryHandler(toggle_buy_sell_confirm, pattern="toggle_buy_conf!"))
updater.dispatcher.add_handler(CallbackQueryHandler(do_rebalance, pattern="rebalance"))

updater.dispatcher.add_handler(CallbackQueryHandler(stat_today, pattern="stat_today"))
updater.dispatcher.add_handler(CallbackQueryHandler(stat_yesterday, pattern="stat_yesterday"))
updater.dispatcher.add_handler(CallbackQueryHandler(balance_submenu, pattern="info_balance"))

updater.dispatcher.add_handler(CallbackQueryHandler(cancel_menu, pattern="cancel"))
updater.dispatcher.add_error_handler(error)

updater.start_polling()
################################################################################
