from sqlalchemy import desc

from bot.DB.DB import connect
from bot.DB.User import Orders
from bot.DB.queries.user.orders import get_user_orders
from bot.database import base_sqlite as base_sqlite


def create_in_base_resell_order(sell_order_id: int):
    """
    Создание записей в БД для последующей допродажи
    """
    db_session = connect("private")
    try:
        # находим запись по которой не было сделано полной продажи
        select_part_sell_info = get_user_orders(db_session).filter(
            Orders.status == "Done", Orders.operation == "Sell",
            Orders.re_sell == 0, Orders.orderID == sell_order_id,
            Orders.executedLots != Orders.requestedLots).all()
        # select_part_sell_info = base_sqlite.select_adw(
        #     what="id, orderId, executedLots, telegram_complete_mess_id",
        #     table="orders",
        #     expression="where operation='Sell' and status='Done' and "
        #                "executedLots<>requestedLots and re_sell=0 and "
        #                "orderId=%s" % sell_order_id,
        #     base="private"
        # )

        for part_sell in select_part_sell_info:
            part_sell: Orders = part_sell
            table_sell_id = part_sell.id
            executed_lots = part_sell.executedLots
            order_telegram_id = part_sell.telegram_mess_id

            # находим записи покупок, связанных с записью продажи
            select_buy = get_user_orders(db_session).filter(
                Orders.status == "Done", Orders.operation == "Buy",
                Orders.sell_order == part_sell.orderID).order_by(desc(Orders.price)).all()

            # select_buy = base_sqlite.select_adw(
            #     what="id, executedLots",
            #     table="orders",
            #     expression="where operation='Buy' and sell_order=%s and "
            #                "status='Done' order by price desc" % part_sell.orderID,
            #     base="private"
            # )

            for buy_order in select_buy:
                buy_order: Orders = buy_order
                order_id = buy_order.id
                order_lot = buy_order.executedLots
                if order_lot <= executed_lots:
                    executed_lots = executed_lots - order_lot
                else:
                    order_lot = order_lot - executed_lots
                    executed_lots = 0
                    # создаем копию строки
                    create_copy_buy_order(
                        buy_order_id=order_id,
                        lots=order_lot,
                        telegram_id=order_telegram_id
                    )
            try:
                part_sell.re_sell = 1
                db_session.commit_session()
                # base_sqlite.command_adw(
                #     what="UPDATE orders set re_sell=1 where id=%s" % table_sell_id,
                #     base="private"
                # )
            except Exception as inst:
                print("\t%s" % inst)

    except Exception as inst:
        print("\t%s" % inst)


def create_copy_buy_order(buy_order_id: int, lots: int, telegram_id=None):
    """
    Создание копии лота покупки для последующей допродажи
    """
    try:
        order = base_sqlite.select_adw(
            what="figi, orderId, "
                 "price, target, "
                 "executedLots, commission_value, telegram_mess_id, commission_currency",
            table="orders",
            expression="where id=%s" % buy_order_id,
            base="private"
        )[0]

        figi = order[0]
        order_id = order[1]
        order_price = round(order[2], 2)
        order_price_target = round(order[3], 2)
        executed_lots = order[4]
        commission_value = round(order[5], 2)

        if telegram_id is None:
            telegram_id = order[6]

        currency = order[7]

        money_spent = order_price * executed_lots
        money_spent = round(money_spent / executed_lots * lots, 2)
        lot_spent = round(money_spent + abs(commission_value), 2)

        data = [
            figi, order_id,
            "Buy", order_price, order_price_target,
            "Done", lots, lots,
            money_spent, lot_spent,
            telegram_id, 1,
            0, currency
        ]

        sql = """insert into orders(
        figi, orderId, 
        operation, price, target,
        status, requestedLots, executedLots,
        money_spent, lot_spent,
        telegram_mess_id, re_sell,
        commission_value, commission_currency
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """

        base_sqlite.command_adw(
            what=sql,
            data=data,
            base="private"
        )

    except Exception as inst:
        print("\t%s" % inst)
