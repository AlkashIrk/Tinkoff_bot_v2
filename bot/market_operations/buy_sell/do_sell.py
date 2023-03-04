# Refactored
from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.queries.shared.initial import get_shared_init
from bot.api_v2 import authorize, CurrencySign
from bot.cfg.logs_work import to_log, debuginfo
from bot.database import base_sqlite
from bot.market_operations.market_operations import create_request
from bot.market_operations.special_func import split_by_n
from bot.model.OrderParam import OrderParam
from bot.telegram.send_to_telegram import send_to_telegram


def do_sell(o: OrderParam, user_vars):
    # получаем валюту акции
    db_session_shared = connect("shared")

    share_info: InitialShared = get_shared_init(db_session_shared).filter(InitialShared.figi == o.ticker_figi).one()
    currency_order = share_info.currency
    currency_sign = CurrencySign.value_of(currency_order)
    db_session_shared.close_session()

    text_print = "Можно продать %s по %.2f%s\n" % (o.ticker, o.last_price, currency_sign)
    # to_log("\t" + text_print, "logs/all_orders.log", True)

    # делаем выборку акций из БД
    try:
        orders_to_sell = base_sqlite.select(
            what="orderId, target, executedLots, lot_spent, telegram_mess_id, price, id",
            table="orders",
            expression="figi='%s' and operation='Buy' "
                       "and status='Done' and sell_order is NULL and target<='%s'"
                       % (o.ticker_figi, o.last_price),
            base="private")
    except Exception as inst:
        debuginfo("Error here")
        print("\t%s" % inst)
        orders_to_sell = []

    lots_to_sell = 0
    money_spent = 0
    min_target = 0
    data_up_all = []
    orders_text = ""

    # подсчитываем лоты
    # затраты на покупку
    # формируем сообщение
    for order in orders_to_sell:
        order_id = order[0]
        target = order[1]
        # определяем минимальный target-price
        if target > min_target:
            min_target = round(target, 2)
        order_lot_count = order[2]
        order_money_spent = order[3]
        mess_id = order[4]
        order_buy_price = order[5]
        order_base_id = order[6]

        orders_text += "   id=%s (%s по %.2f%s)\n" \
                       % (split_by_n(order_id, 4), order_lot_count, order_buy_price, currency_sign)

        lots_to_sell = lots_to_sell + order_lot_count
        money_spent = money_spent + order_money_spent

        data_up = (
            order_base_id,
        )
        data_up_all.append(data_up, )
        del order
    del orders_to_sell

    # поправка на лотность
    text_print += orders_text
    # TODO проверка лотности!!!
    #lots_to_sell = int(lots_to_sell / share_info.lot)

    if lots_to_sell != 0:
        text_print1 = "Можно продать %s по %.2f%s\n" % (o.ticker, o.last_price, currency_sign)
        print(text_print1)

        # отправляем сообщение в телеграм со ссылкой на последнюю покупку
        mess_id = send_to_telegram(text_print, reply_to=mess_id)

        with authorize(user_vars.token) as client:
            order_id = create_request(
                client=client,
                account_id=user_vars.account_id,
                figi=o.ticker_figi,
                lots=lots_to_sell,
                operation="Sell",
                order_price=min_target,
                order_price_target=o.last_price
            )

        # если получили номер заявки - отправляем в телеграм
        if order_id is not None and order_id != -1:
            text_print = "Ордер: \n\t%s\t\t(id=%s)\n\t%s min price: %.2f%s\n\tcount: %s\n" \
                         % (o.ticker, split_by_n(order_id, 4), "Sell", min_target, currency_sign, lots_to_sell)
            to_log("\t" + text_print, "logs/%s_orders.log" % o.ticker, True)
            to_log("\t" + text_print, "logs/all_orders.log",
                   time_to_log=True, print_to_console=False)

            mess_id = send_to_telegram(text_print, reply_to=mess_id)
            if mess_id is not None:
                try:
                    base_sqlite.command_adw(
                        what="UPDATE orders "
                             "set telegram_mess_id='%s', "
                             "money_spent='%s'"
                             "where orderId='%s'"
                             % (mess_id, money_spent, order_id),
                        base="private")
                except:
                    pass

            # на всех сделках Buy проставляем id сделки продажи
            base_sqlite.update_data(
                table="orders",
                expression="set sell_order='%s'"
                           "WHERE id=?" % order_id,
                data=data_up_all,
                base="private"
            )
    del data_up_all
