# Refactored
from bot.DB.DB import connect
from bot.DB.User import Orders
from bot.DB.queries.user.initial import get_user_init_by_figi
from bot.DB.queries.user.orders import get_user_orders
from bot.cfg.logs_work import debuginfo
from bot.database import base_sqlite


def recreate_buy_order(base, ticker_figi):
    """
    Если есть не исполненные ордера на покупку
    необходимо увеличить квоту на покупку
    """
    db_session = connect(base)
    try:
        need_buy = get_user_init_by_figi(db_session, ticker_figi).buy
    except Exception as inst:
        print("\t%s" % inst)
        need_buy = 0
        debuginfo("Error here")

    # получаем список неисполненных ордеров
    try:
        orders_declined = get_user_orders(db_session).filter(
            Orders.status == "Decline", Orders.operation == "Buy",
            Orders.retry == 0, Orders.figi == ticker_figi).all()
    except Exception as inst:
        orders_declined = []
        debuginfo("Error here")

    # если в списке есть ордера - меняем квоту на покупку
    if orders_declined:
        for order in orders_declined:
            order: Orders = order
            need_buy += order.requestedLots
            data_up = (
                order.id,
            )
            data_up = [tuple(data_up)]

            base_sqlite.update_data(
                table="orders",
                expression="set retry=1 WHERE id=?",
                data=data_up,
                base=base)

        data_up = (ticker_figi,)
        data_up = [tuple(data_up)]
        base_sqlite.update_data(table="initial",
                                expression="set buy=%s WHERE figi=?" % need_buy,
                                data=data_up,
                                base=base
                                )
