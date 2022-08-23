# Refactored
from bot.database import base_sqlite
from bot.api_v2 import authorize
from bot.cfg.logs_work import to_log, debuginfo
from bot.market_operations.market_operations import create_request
from bot.telegram.send_to_telegram import send_to_telegram
from bot.market_operations.special_func import split_by_n


def recreate_sell_order(base, ticker_figi, token, account_id, ticker, telegram_id):
    """
    Если есть не исполненные ордера на продажу
    необходимо их выставить снова
    """
    try:
        orders_declined = base_sqlite.select(
            what="orderId, target, requestedLots, sell_order, money_spent",
            table="orders",
            expression="(status='Decline' or status='Rejected')"
                       " and operation='Sell' and retry<>1 and figi='%s'"
                       % ticker_figi,
            base=base
        )
    except:
        orders_declined = []
        debuginfo("Error here")

    if len(orders_declined) >= 1:
        money_spent = 0
        order_lots, order_price = get_average_order(orders_declined)

        try:
            first_mess_id = base_sqlite.select(
                what="telegram_mess_id",
                table="orders",
                expression="operation='Sell' and sell_order='%s' limit 1"
                           % orders_declined[0][3],
                base=base
            )[0][0]
        except:
            first_mess_id = None
        try:
            with authorize(token) as client:
                order_id_new = create_request(
                    client=client,
                    account_id=account_id,
                    figi=ticker_figi,
                    lots=order_lots,
                    operation="Sell",
                    order_price=order_price,
                    order_price_target=order_price,
                    base=base
                )

            text_print = "Recreate order: \n\t%s\t\t(id=%s)\n\tSell price: %.2f$\n\tCount: %s" \
                         % (ticker, split_by_n(order_id_new, 4), order_price, order_lots)
            to_log("\t" + text_print, "logs/%s_orders.log" % ticker, True)

            """
            Отправим оповещение и обновим значение в таблице
            """
            if first_mess_id is not None:
                mess_id = send_to_telegram(text_print,
                                           chat_id=telegram_id,
                                           reply_to=first_mess_id)
            else:
                mess_id = send_to_telegram(text_print, chat_id=telegram_id)

            if mess_id is not None:
                try:
                    base_sqlite.command_adw(
                        what="UPDATE orders "
                             "set telegram_mess_id='%s' "
                             "where orderId='%s'"
                             % (mess_id, order_id_new),
                        base=base
                    )
                except:
                    pass

            for order in orders_declined:
                order_id = order[0]
                order_price = order[1]
                order_lots = order[2]
                sell_order_id_old = order[3]
                money_spent += order[4]
                data_up = (
                    order_id,
                )
                data_up = [tuple(data_up)]

                """
                Обновим цепочку продажи ордеров
                """
                try:
                    base_sqlite.command_adw(
                        what="UPDATE orders "
                             "set sell_order='%s' "
                             "where sell_order='%s'"
                             % (order_id_new, sell_order_id_old),
                        base=base
                    )
                except:
                    pass

                base_sqlite.update_data(
                    table="orders",
                    expression="set retry=1 WHERE orderId=?",
                    data=data_up,
                    base=base
                )

                text_print = "Recreate order: \n\t\t\tSell price: %.2f$\n\t\t\tCount: %s" \
                             % (order_price, order_lots)
                to_log("\t\t" + text_print, "logs/%s_orders.log" % ticker)

                # send_to_telegram(text_print)

            # обновим в базе стоймость потраченных средств
            try:
                base_sqlite.command_adw(
                    what="UPDATE orders "
                         "set money_spent='%s' "
                         "where orderId='%s'"
                         % (money_spent, order_id_new),
                    base=base
                )
            except:
                pass

        except Exception as inst:
            print("\tCant recreate orders for %s" % ticker)
            debuginfo("Error here")
            print("\t%s" % inst)


def get_average_order(order_list: list):
    """
    Средняя цена ордера увеличенная на 1 цент

    Parameters:
    order_list (list): Список сделок

    Returns:
    int:Количество лотов
    float:Средняя цена лота
    """
    cost_average: float
    lots_cost = 0
    lots_count = 0
    for order_info in order_list:
        lots_count = lots_count + order_info[2]
        lots_cost = lots_cost + order_info[1] * order_info[2]

    ## TODO 0.01 change to minIncrement
    if len(order_list) == 1:
        cost_average = lots_cost / lots_count
    else:
        cost_average = lots_cost / lots_count + 0.01
    cost_average = round(cost_average, 2)

    return lots_count, cost_average
