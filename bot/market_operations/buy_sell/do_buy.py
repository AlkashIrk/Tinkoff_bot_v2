# Refactored
import time

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.user.balance import get_user_balance_by_currency
from bot.DB.queries.user.initial import get_user_init_by_figi
from bot.api_v2 import authorize, calc_target_price, CurrencySign, round_price
from bot.cfg.logs_work import to_log, debuginfo
from bot.database import base_sqlite
from bot.market_operations.market_operations import up_port, create_request
from bot.market_operations.special_func import split_by_n
from bot.model.OrderParam import OrderParam
from bot.settings import def_order_lot_price, def_minimum_balance, time_pause_buy
from bot.telegram.send_to_telegram import send_to_telegram


def do_buy(o: OrderParam, user_vars):
    """
    1. время входит в диапазон покупок
    2. покупки разрешены
    3. цена закрытия меньше максимальной
    4. нет перекупленности акции 2 сигнала из трех ниже
        STO < 75
        RSI < 70
        UO < 70
    """
    db_session = connect("private")
    db_session_shared = connect("shared")

    # получаем валюту акции
    share_info: InitialShared = get_shared_init(db_session_shared).filter(InitialShared.figi == o.ticker_figi).one()
    currency_order = share_info.currency
    currency_sign = CurrencySign.value_of(currency_order)
    db_session_shared.close_session()

    with authorize(user_vars.token) as client:
        up_port(client=client, user=user_vars.user_login)

    # получаем баланс пользователя из БД
    balance_info = get_user_balance_by_currency(db_session, currency_order)

    if balance_info.blocked is not None:
        balance = balance_info.balance - balance_info.blocked
    else:
        balance = balance_info.balance

    balance = round(balance, 2)

    # определяем минимальный баланс для покупки
    try:
        # min_balance = get_user_settings_by_name(db_session, SettingsEnum.min_balance).value
        min_balance = balance_info.min_value
    except Exception as inst:
        debuginfo("Error here")
        print("\t%s" % inst)
        min_balance = def_minimum_balance

    # покупка возможна, только при балансе большем чем минимальный!
    if balance >= min_balance:
        time_now = round(time.time())

        text_print = "Можно закупить %s по %.2f%s\n" % (
            o.ticker, o.last_price, currency_sign)
        to_log("\t" + text_print, "logs/all_orders.log", True)

        # определяем средний размер лота
        try:
            lot_price = balance_info.lot_price
            if lot_price <= 0:
                return
        except Exception as inst:
            debuginfo("Error here")
            print("\t%s" % inst)
            lot_price = def_order_lot_price

        # стоимость 1 лота
        share_lot_price = round(o.last_price * share_info.lot, 2)

        # определяем количество возможного лота для покупки, исходя из стоимости одного лота
        lots_to_buy = lot_price // share_lot_price
        lots_to_buy = int(lots_to_buy)

        # если можно купить больше, чем разрешено по лимитам - обрезаем лотность
        if lots_to_buy > o.lots_may_buy:
            lots_to_buy = o.lots_may_buy

        # если получилась 1 акция - проверяем можем ли мы купить 2 акции.
        if lots_to_buy == 1 and share_info.lot == 1:
            check_new_balance = balance - (lots_to_buy + 1) * share_lot_price
            if check_new_balance > 0:
                lots_to_buy = 2

        #  минимальный лот в 2 акций
        if lots_to_buy <= 2 and share_info.lot == 1:
            o.lots_may_buy = 0
            last_buy_time = time_now
        else:
            last_buy_time = get_user_init_by_figi(db_session, o.ticker_figi).last_buy_time

        # если количество акций для покупки больше 0 и по ближайшему времени не было покупок этой акции
        if o.lots_may_buy > 0 and last_buy_time < time_now - time_pause_buy:
            mess_id = send_to_telegram(text_print)

            # обновляем лимит акций для покупки
            need_buy = o.lots_may_buy - lots_to_buy
            data_up = (
                need_buy,
                time_now,
                o.ticker_figi,
            )
            data_up = [tuple(data_up)]
            base_sqlite.update_data(
                table="initial",
                expression="set buy=?, last_buy_time=? "
                           "WHERE figi=?",
                data=data_up,
                base="private"
            )

            # обновляем баланс
            balance_info.balance = balance - (lots_to_buy * share_lot_price)
            db_session.commit_session()

            # определяем минимальный профит с акции
            try:
                target_price = calc_target_price(lots_to_buy * share_lot_price, share_info.minPriceIncrement,
                                                 lots_to_buy * share_info.lot)
            except Exception as inst:
                debuginfo("Error here")
                print("\t%s" % inst)
                return

            # формируем запрос на покупку
            buy_price = o.last_price + share_info.minPriceIncrement
            buy_price = round_price(buy_price, share_info.minPriceIncrement)
            with authorize(user_vars.token) as client:
                order_id = create_request(client=client,
                                          account_id=user_vars.account_id,
                                          figi=o.ticker_figi, lots=lots_to_buy,
                                          operation="Buy",
                                          order_price=buy_price,
                                          order_price_target=target_price)

            # если получили номер заявки - отправляем в телеграм
            if order_id != -1:
                text_print = "Ордер: \n\t%s\t\t(id=%s)\n\t%s price: %.2f%s\n\tcount: %s (x%s)\n" \
                             % (o.ticker, split_by_n(order_id, 4), "Buy", buy_price,
                                currency_sign, lots_to_buy, int(share_info.lot))

                to_log("\t" + text_print, "logs/%s_orders.log" % o.ticker, True)
                to_log("\t" + text_print, "logs/all_orders.log",
                       time_to_log=True, print_to_console=False)

                mess_id = send_to_telegram(text_print, reply_to=mess_id)
                # если получили id сообщения - обновляем БД
                if mess_id is not None:
                    try:
                        base_sqlite.command_adw(
                            what="UPDATE orders "
                                 "set telegram_mess_id='%s' "
                                 "where orderId='%s'"
                                 % (mess_id, order_id),
                            base="private")
                    except Exception as inst:
                        debuginfo("Error here")
                        print("\t%s" % inst)
