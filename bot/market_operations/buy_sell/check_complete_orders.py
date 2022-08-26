from datetime import datetime

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.User import InitialUser, Orders
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.user.initial import get_user_init_by_figi
from bot.DB.queries.user.orders import get_user_orders
from bot.api_v2 import CurrencySign
from bot.cfg.logs_work import debuginfo, to_log
from bot.database.service.re_sell import create_in_base_resell_order
from bot.database.service.user_increase_balance import increase_min_balance
from bot.market_operations.special_func import split_by_n
from bot.telegram.send_to_telegram import send_to_telegram


def check_complete(o: InitialUser):
    base = "private"
    db_session = connect(base)

    try:
        stock_param = get_user_init_by_figi(db_session, o.figi)
        orders_done = get_user_orders(db_session).filter(
            Orders.status == "Done", Orders.retry == 0, Orders.figi == o.figi).all()
    except:
        debuginfo("Error here")
        return

    # Если у нас были исполненные ордера
    for order in orders_done:
        order: Orders = order
        # сообщения в телеграм
        currency_sign = CurrencySign.value_of(order.commission_currency)
        if order.operation == "Sell":
            # TODO переделать на 1 запрос
            # получаем валюту акции
            db_session_shared = connect("shared")
            share_info: InitialShared = get_shared_init(db_session_shared).filter(
                InitialShared.figi == order.figi).one()
            currency_order = share_info.currency
            db_session_shared.close_session()

            """
            информация о выполненных сделках по API при высокой нагрузке приходит с задержкой:
            
            иногда возвращается 0 число исполненных лотов
            иногда 0 цена
            
            необходимо подождать от 5 до 30 минут
            """
            if order.status == "Done" and (order.executedLots == 0 or order.price == 0):
                text_to_log = "id=%s status=%s price=%s lots=%s" \
                              % (order.orderID, order.status, order.price, order.executedLots)
                to_log(text_to_log="\t" + text_to_log,
                       file_name="logs/debug_%s.log" % order.figi,
                       time_to_log=True)
                continue

            # частичное исполнение
            if order.requestedLots != order.executedLots:
                money_get = order.target * order.executedLots
                # TODO correct
                money_get = money_get - order.money_spent / order.requestedLots * order.executedLots
                money_get += order.commission_value

                money_get = round(money_get, 2)
                money_spent = order.money_spent / order.requestedLots * order.executedLots
                money_spent = round(money_spent, 2)

                try:
                    order.money_spent = money_spent
                    order.lot_spent = money_spent + abs(order.commission_value)
                except Exception as inst:
                    debuginfo("\tError here\n\t"
                              "order_base_id=%s\n\t"
                              "order_id=%s" % (order.id, order.orderID))
                    print("\t%s" % inst)

                text_print = "Исполнен частично %s из %s\n%.2f%s\n   id=%s" \
                             % (order.executedLots, order.requestedLots,
                                money_get, currency_sign, split_by_n(order.orderID, 4))

                time_now = datetime.now().strftime("%d-%m-%Y__%H_%M_%S")
                with open("logs/operations/log_mark_%s.log" % time_now, "a+", encoding="utf-8") as full_log:
                    print(text_print, file=full_log)

            # полное исполнение
            else:
                money_get = order.price * order.executedLots * share_info.lot
                money_get = money_get - order.money_spent + order.commission_value
                money_get = round(money_get, 2)
                text_print = "Исполнен %.2f%s\n   id=%s" % (money_get, currency_sign, split_by_n(order.orderID, 4))

            # увеличить размер баланса
            increase_min_balance(money_get, currency_order)

            if order.telegram_mess_id is not None:
                mess_id = send_to_telegram(text_print, reply_to=order.telegram_mess_id)
            else:
                mess_id = send_to_telegram(text_print)

            if mess_id is not None:
                try:
                    order.telegram_complete_mess_id = mess_id
                except Exception as inst:
                    debuginfo("Error here")
                    print("\t%s" % inst)
            del text_print

        #   ИЗМЕНЯЕМ КВОТУ В БАЗЕ
        if order.operation == "Buy":
            # увеличиваем квоту на количество неполного исполнения ордера
            # хотел закупить 10             order[2]
            # а закупил только 7            order[3]
            # увеличиваем квоту на 3        order[2] - order[3]
            stock_param.buy += order.requestedLots - order.executedLots

            try:
                order.money_spent = order.price * order.executedLots
                order.lot_spent = order.money_spent + abs(order.commission_value)
            except Exception as inst:
                debuginfo("\tError here\n\t"
                          "order_base_id=%s\n\t"
                          "order_id=%s" % (order.id, order.orderID))
                print("\t%s" % inst)

        #   ИЗМЕНЯЕМ КВОТУ В БАЗЕ
        #   при наличии не допроданных акций пересоздаем ордер
        if order.operation == "Sell":
            stock_param.buy += order.executedLots
            # ордер для допродажи
            if order.requestedLots != order.executedLots and order.executedLots != 0:
                create_in_base_resell_order(sell_order_id=order.orderID)

        order.retry = 1
        del order
    del orders_done
    db_session.commit_session()
