import os
from time import sleep

from bot.DB.edit.share import add_share
from bot.DB.queries.user.initial import get_curr_list
from bot.api_v2 import authorize
from bot.cfg.parse_params import get_params
from bot.daemons.daemon_service import thread_schedule, update_stock_info
from bot.database.service_for_base import rebalance
from bot.database.stat_info import user_stat_info
from bot.database.telegram_func import get_account_id_by_user, get_balance_info
from bot.market_operations.market_operations import *
from bot.market_operations.signals.calculate.day import calculate_signals_day
from bot.model.BalanceInfo import BalanceInfo
from bot.telegram.send_to_telegram import *

global_var.init()

token = global_var.token
orders_active_in_base = {}
orders_active_in_market = {}

args = get_params()
mode = None
if args.mode:
    mode = args.mode
else:
    print("Select mode")
    exit()

if mode == "debug":
    # rebalance()

    # db_session_shared = connect("shared")
    add_share("OZON")
    # add_share("BBG004Z2RGW8","ROLO")

    # info = db_session_shared.query(InitialShared).filter(InitialShared.figi == "BBG004Z2RGW8").all()
    # calculate_signals_day(info)

    update_stock_info()
    calculate_signals_day()
    exit(0)

    test = user_stat_info()

    # calculate_profit()
    '''
    #--------------------------------------------
    with authorize(global_var.token) as client:
        up_port(client=client, user="Alkash")
    # --------------------------------------------
    '''

elif mode == "test_decline":
    global_var.account_id = get_account_id_by_user(global_var.user_login)

    order_id = '32343080631'

    with authorize(global_var.token) as client:
        decline_order(client=client, account_id=global_var.account_id, order_id=order_id)

        a = 0

if mode == "signals":
    from bot.daemons.daemon_signals import daemon_check_signals
    import sys

    print('\33]0;Signals\a', end='')
    sys.stdout.flush()
    daemon_check_signals()

elif mode == "buy_and_sell":
    import threading
    from bot.daemons.daemon_buy_and_sell import daemon_buy_and_sell

    global_var.account_id = get_account_id_by_user(global_var.user_login)
    sleep(5)
    import sys

    print('\33]0;Buy_and_Sell_%s\a' % global_var.user_login, end='')
    sys.stdout.flush()

    os.system("Title Buy_and_Sell %s" % global_var.user_login)
    os.system("cls")

    thread_dict = {
        "a": threading.Thread(target=daemon_buy_and_sell, args=(global_var,), name="a"),
        "b": threading.Thread(target=thread_schedule, args=(global_var,), name="b")
    }
    for t in thread_dict:
        thread_dict[t].start()

elif mode == "watchdog":
    from bot.daemons.daemon_watchdog import watchdog

    watchdog()

else:
    import threading
    from bot.daemons.daemon_candles import daemon_candles
    from bot.daemons.daemon_watchdog import watchdog

    daemon_candles(global_var.token)
