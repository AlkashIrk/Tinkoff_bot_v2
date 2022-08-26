from tinkoff.invest import Operation

from bot.api_v2 import get_value_from_quo, get_status, round_price
from bot.cfg.logs_work import debuginfo
from bot.database import base_sqlite as base_sqlite
from bot.model.OrderInfo import OrderInfo


def get_obj(order: Operation) -> OrderInfo:
    order_info = OrderInfo()

    # тип заявки
    try:
        order_info.type = order.type
    except:
        order_info.type = "Not valid"
        return order_info

    try:
        order_info.figi = order.figi
    except:
        order_info.figi = None

    # операция?
    try:
        order_info.operation = ""
    except:
        order_info.operation = "Not valid"

    # для транзакции комиссии необходим номер родительской заявки
    try:
        order_info.parent_id = order.parent_operation_id
    except:
        order_info.parent_id = None

    # статус заявки
    try:
        order_info.status = get_status(order.state)
    except:
        order_info.status = "Not valid"

    # запрошенное число лотов
    try:
        # пересчитываем акции в лоты
        try:
            order_info.req_lots = int(order.quantity / order_info.getLotInfo().lot)
        except:
            order_info.req_lots = order.quantity

    except:
        order_info.req_lots = None

    # исполненное число лотов
    # потраченные деньги на лот
    try:
        executed_lots = 0
        money_spent = 0
        for trades in order.trades:
            executed_lots = executed_lots + trades.quantity
            try:
                money_spent = money_spent + trades.quantity * get_value_from_quo(trades.price)
                money_spent = round(money_spent, 3)
            except:
                pass

        # пересчитываем акции в лоты
        try:
            order_info.done_lots = int(executed_lots / order_info.getLotInfo().lot)
        except:
            order_info.done_lots = executed_lots

        order_info.money_spent = money_spent
    except:
        order_info.done_lots = None
        order_info.money_spent = 0

    # цена за один лот
    try:
        order_info.commission = get_value_from_quo(order.payment)
    except:
        order_info.commission = None

    # валюта
    try:
        order_info.currency = str(order.currency).upper()
    except:
        try:
            order_info.currency = order_info.getLotInfo().currency
        except:
            order_info.currency = None

    # TODO check
    try:
        order_info.price = round_price(get_value_from_quo(order.price), order_info.getLotInfo().minPriceIncrement)
    except:
        try:
            order_info.price = round(get_value_from_quo(order.price), 2)
        except:
            order_info.price = 0

    return order_info


def edit_order_commission(o: OrderInfo):
    """
    Обновляем информацию о комиссии сделки
    """
    try:
        order_in_base = base_sqlite.select(
            what="id, orderId, figi, operation, money_spent, lot_spent",
            table="orders",
            expression="orderId='%s'" % o.parent_id,
            base="private"
        )
    except:
        return

    if not order_in_base:
        return
    else:
        order_active = order_in_base[0]
        if order_active[4] == 0:
            return

    if order_active[4] is None:
        money_spent = 0
    else:
        money_spent = order_active[4]

    order_table_id = order_active[0]
    lot_spent = round(money_spent + abs(o.commission), 2)

    if order_active[3] != 'Sell':
        data_up = (
            o.currency,
            o.commission, lot_spent,
            order_table_id,
        )
        data_up = [tuple(data_up)]

        try:
            base_sqlite.update_data(
                table="orders",
                expression="SET commission_currency=?,"
                           "commission_value=?, lot_spent=? "
                           "WHERE id=?",
                data=data_up,
                base="private"
            )
        except Exception as inst:
            print("\t%s" % inst)
            debuginfo("Error here")
    else:
        data_up = (
            o.currency,
            o.commission,
            order_table_id,
        )
        data_up = [tuple(data_up)]

        try:
            base_sqlite.update_data(
                table="orders",
                expression="SET commission_currency=?,"
                           "commission_value=? "
                           "WHERE id=?",
                data=data_up,
                base="private"
            )
        except Exception as inst:
            print("\t%s" % inst)
            debuginfo("Error here")


def edit_order_v2(order):
    order_info = get_obj(order)

    if order_info.type == 'Удержание комиссии за операцию':
        edit_order_commission(order_info)
        return

    try:
        order_in_base = base_sqlite.select(
            what="id, orderId, figi, operation",
            table="orders",
            expression="orderId='%s' and re_sell=0" % order.id,
            base="private"
        )

        if order_in_base:
            order_active = order_in_base[0]
        else:
            return

        order_info.base_id = order_active[0]
        order_info.tinkoff_order_id = order_active[1]
        order_operation = order_active[3]

        if order_operation == "Buy":
            buy_order(order_info)
        elif order_operation == "Sell":
            sell_order(order_info)

    except:
        pass

    # to_log("\t" + text, "logs/orders_%s.log" %figi, True)


def buy_order(order):
    """
    Обновление в БД сделки о покупке
    """
    data_up = (
        order.status,
        order.req_lots, order.done_lots,
        order.currency,
        order.money_spent, order.price,
        order.base_id,
    )
    data_up = [tuple(data_up)]

    try:
        base_sqlite.update_data(
            table="orders",
            expression="SET status=?,"
                       "requestedLots=?, executedLots=?,"
                       "commission_currency=?,"
                       "money_spent=?, price=? "
                       "WHERE id=?",
            data=data_up,
            base="private"
        )
    except Exception as inst:
        print("\t%s" % inst)
        print("Error update\n\tid=%s\n\ttable_id=%s" % (order.tinkoff_order_id, order.base_id))
        debuginfo("Error here")


def sell_order(order):
    """
    Обновление в БД сделки о продаже
    """
    data_up = (
        order.status,
        order.req_lots, order.done_lots,
        order.price,
        order.base_id,
    )
    data_up = [tuple(data_up)]

    try:
        base_sqlite.update_data(
            table="orders",
            expression="SET status=?,"
                       "requestedLots=?, executedLots=?,"
                       "price=? "
                       "WHERE id=?",
            data=data_up,
            base="private"
        )
    except Exception as inst:
        print("\t%s" % inst)
        print("Error update\n\tid=%s\n\ttable_id=%s" % (order.tinkoff_order_id, order.base_id))
        debuginfo("Error here")
