# Refactored
from datetime import datetime
from time import sleep

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.User import InitialUser, SettingsEnum
from bot.DB.queries.shared.initial import get_shared_init, get_shared_init_by_figi
from bot.DB.queries.user.initial import get_user_init
from bot.DB.queries.user.settings import get_user_settings_by_name
from bot.cfg.logs_work import debuginfo
from bot.database import base_sqlite
from bot.market_operations.buy_sell.check_complete_orders import check_complete
from bot.market_operations.buy_sell.do_buy import do_buy
from bot.market_operations.buy_sell.do_sell import do_sell
from bot.market_operations.special_func import check_buy_time
from bot.model.DayParams import DayParams
from bot.model.OrderParam import OrderParam

# интервал в секундах между проверками
from bot.settings import daemon_b_s_sleep


# проверка наличия возможности покупки\продажи
def daemon_buy_and_sell(global_var):
    base_sqlite.check_column(base="private", table="initial",
                             column="enable", column_type="integer", default_value=0)
    base_sqlite.check_column(base="private", table="initial",
                             column="enable_buy", column_type="integer", default_value=0)
    base_sqlite.check_column(base="private", table="initial",
                             column="enable_sell", column_type="integer", default_value=0)

    while True:
        # значение осцилятора, для каждой акции храним в словаре
        signals = {}
        db_session = connect("shared")

        try:
            orders_active = get_shared_init(db_session).all()
            for element in orders_active:
                element: InitialShared = element
                ticker = element.ticker
                signals[ticker] = {"STO": element.sig_stoch, "RSI": element.sig_RSI, "market_open": element.market_open}
                del ticker
                del element
            del orders_active
        except Exception as inst:
            debuginfo("\tError here")
            print("\t%s" % inst)

        #
        # перебираем все акции, которыми торгуем
        #
        debug_ticker = ''
        try:
            db_session_private = connect("private")
            orders_active = get_user_init(db_session_private).filter(InitialUser.enable == 1).all()
            for element in orders_active:
                order_param = OrderParam()
                element: InitialUser = element
                order_param.ticker_figi = element.figi
                order_param.ticker = element.ticker
                debug_ticker = element.ticker
                order_param.lots_may_buy = element.buy

                try:
                    signal_stoch = signals[element.ticker]["STO"]
                    signal_rsi = signals[element.ticker]["RSI"]
                    market_open = signals[element.ticker]["market_open"]
                except Exception as inst:
                    print("\t%s" % inst)
                    signal_stoch = 'Hold'
                    signal_rsi = 'Hold'
                    market_open = 0

                if element.enable_buy == 1:
                    ticker_buy_enabled = True
                else:
                    ticker_buy_enabled = False

                if element.enable_sell == 1:
                    ticker_sell_enabled = True
                else:
                    ticker_sell_enabled = False

                """
                Проверяем какие ордера были исполнены
                """
                check_complete(element)

                if market_open == 0:
                    continue

                # изменение под v2
                order_param.last_price = get_shared_init_by_figi(db_session, element.figi).last_price
                day_params = DayParams(element.figi)

                #   СИГНАЛ НА ПОКУПКУ
                if ticker_buy_enabled and signal_stoch == "Need_Buy" and signal_rsi == "Need_Buy":
                    only_sell = get_user_settings_by_name(db_session_private, SettingsEnum.only_sell).value
                    if check_buy_time() and day_params.may_buy >= 2:
                        if order_param.last_price < day_params.max_price:
                            if not only_sell:
                                do_buy(order_param, global_var)

                #   СИГНАЛ НА ПРОДАЖУ
                if ticker_sell_enabled and signal_stoch == "Need_Sell":
                    do_sell(order_param, global_var)

                try:
                    del signal_rsi
                    del signal_stoch
                    del element
                except Exception as inst:
                    print("\t%s" % inst)
            del orders_active

            if 1 < datetime.now().hour <= 6:
                # увеличиваем паузу в неторговое время
                sleep(daemon_b_s_sleep * 30)
            else:
                sleep(daemon_b_s_sleep)

        except Exception as inst:
            debuginfo("Error here, ticker %s" % debug_ticker)
            print("\t%s" % inst)
            sleep(60)
