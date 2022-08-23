from bot.DB.DB import connect
from bot.DB.Shared import InitialShared, Users
from bot.DB.User import SettingsEnum, History
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.shared.user import get_user_by_name
from bot.DB.queries.user.history import get_user_history
from bot.DB.queries.user.settings import get_user_settings_by_name, set_user_settings_by_name
from bot.api_v2 import authorize, CurrencySign
from bot.database import base_sqlite
from bot.market_operations.special_func import split_by_n


def toggle_buy(operation="GET", value=None, user_id=None):
    base_name = get_base_by_user(user_id)
    if base_name is None:
        return

    db_session = connect(base_name)
    if operation == "GET":
        select_settings = get_user_settings_by_name(db_session, SettingsEnum.only_sell).value

        if select_settings == 0:
            return False
        if select_settings == 1:
            return True
    if operation == "SET":
        if value == "OFF":
            set_user_settings_by_name(db_session, SettingsEnum.only_sell, 1)
        if value == "ON":
            set_user_settings_by_name(db_session, SettingsEnum.only_sell, 0)


def get_chat_by_user(user_id):
    db_session = connect("shared")
    select_users = get_user_by_name(db_session, user_id)

    if user_id is None or select_users is None:
        return None
    return select_users.telegram_id


def get_base_by_user(user_id):
    db_session = connect("shared")
    select_users = get_user_by_name(db_session, user_id)

    if user_id is None or select_users is None:
        return None
    return select_users.base


def get_token_by_user(user_id):
    db_session = connect("shared")
    select_users = get_user_by_name(db_session, user_id)

    if user_id is None or select_users is None:
        return None
    return select_users.token


def get_account_id_by_user(user_id):
    db_session = connect("shared")
    select_users = get_user_by_name(db_session, user_id)

    if user_id is None or select_users is None:
        return None
    return select_users.account_id


def get_balance_info(base=None) -> History:
    if base is None:
        base = "private"
    db_session = connect(base)

    return get_user_history(db_session).order_by(History.id.desc()).first()


def force_sell(ticker: str, user_id: Users):
    from bot.cfg.logs_work import to_log
    from bot.market_operations.market_operations import create_request, debuginfo
    from bot.telegram.send_to_telegram import send_to_telegram

    if user_id is None:
        return

    user_token = user_id.token
    chat_id = user_id.telegram_id
    base = user_id.base

    ticker = ticker.upper()
    try:
        orders_active = base_sqlite.select(
            what="figi, ticker,  buy",
            table="initial",
            expression="ticker='%s'" % ticker,
            base=base
        )

        ticker_figi = orders_active[0][0]

        db_session = connect("shared")
        row_data: InitialShared = get_shared_init(db_session).filter(InitialShared.figi == ticker_figi).one()
        candle_close = round(row_data.last_price, 2)
        text_print = "Принудительная продажа %s по %.2f%s\n" \
                     % (ticker, candle_close, CurrencySign.value_of(row_data.currency))
        to_log("\t" + text_print, "logs/all_orders.log", True)

        try:
            orders_active = base_sqlite.select(
                what="orderId, target, executedLots, money_spent, telegram_mess_id, price, commission_value, id",
                table="orders",
                expression="figi='%s' and operation='Buy' "
                           "and status='Done' and sell_order is NULL and target<='%s'"
                           % (ticker_figi, candle_close),
                base=base
            )

        except:
            orders_active = []
            debuginfo("Error here")

        lots_to_sell = 0
        money_spent = 0
        min_target = 0
        data_up_all = []
        orders_text = ""
        for order in orders_active:
            order_id = order[0]
            target = order[1]
            if target > min_target:
                min_target = round(target, 2)
            order_buy_price = order[5]
            order_lot_count = order[2]
            commission_value = abs(order[6])
            orders_text += "   id=%s (%s по %.2f$)\n" \
                           % (split_by_n(order_id, 4), order_lot_count, order_buy_price)
            lots_to_sell = lots_to_sell + order_lot_count
            if order[3] is None:
                money_spent_in_order = round(order_lot_count * order_buy_price + commission_value, 2)
                data_up = []
                data_up.append(
                    [money_spent_in_order, order[7]]
                )

                base_sqlite.update_data(
                    table="orders",
                    expression="SET money_spent=? where id=?",
                    data=data_up,
                    base=base
                )
            money_spent = money_spent + order[3]
            mess_id = order[4]

            data_up = (
                order_id,
            )
            data_up_all.append(data_up, )
        text_print += orders_text

        # TODO min_target  округляется выше до 2 знаков
        if lots_to_sell != 0:
            mess_id = send_to_telegram(
                text_print,
                reply_to=mess_id,
                chat_id=chat_id
            )
            with authorize(user_token) as client:
                order_id = create_request(
                    client=client,
                    account_id=user_id.account_id,
                    figi=ticker_figi,
                    lots=lots_to_sell,
                    operation="Sell",
                    order_price=min_target,
                    order_price_target=candle_close,
                    base=base
                )
            if order_id != -1:
                text_print = "Ордер: \n\t%s\t\t(id=%s)\n\t%s min price: %.2f$\n\tcount: %s\n" \
                             % (ticker, split_by_n(order_id, 4), "Sell", min_target, lots_to_sell)
                to_log("\t" + text_print, "logs/%s_orders.log" % ticker, True)
                to_log("\t" + text_print, "logs/all_orders.log",
                       time_to_log=True, print_to_console=False)

                mess_id = send_to_telegram(
                    text_print,
                    reply_to=mess_id,
                    chat_id=chat_id
                )
                if mess_id is not None:
                    try:
                        base_sqlite.command_adw(
                            what="UPDATE orders "
                                 "set telegram_mess_id='%s', "
                                 "money_spent='%s'"
                                 "where orderId='%s'"
                                 % (mess_id, money_spent, order_id),
                            base=base
                        )
                    except:
                        pass

                base_sqlite.update_data(
                    table="orders",
                    expression="set sell_order='%s'"
                               "WHERE orderId=?" % order_id,
                    data=data_up_all,
                    base=base
                )
        else:
            text_print = "Нет доступных акций %s для продажи" % ticker
            send_to_telegram(
                text_print,
                chat_id=chat_id
            )
    except Exception as inst:
        debuginfo("Error here")
        print("\t%s" % inst)
