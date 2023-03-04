import time
from datetime import datetime, timedelta

from pytz import timezone

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.User import Orders
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.user.orders import get_user_orders


def money_profit(today_open=0, today_close=0, base=None):
    """"
    Подсчет суммы закрытых сделок в плюс
    """
    if base is None:
        base = "private"

    db_session = connect(base)

    time_today = datetime.now()
    year_today = time_today.year
    month_today = time_today.month
    day_today = time_today.day
    d1 = datetime(year_today, month_today, day_today, 0, 0, 0, tzinfo=timezone("Europe/Moscow"))

    if today_open == 0:
        d1 = d1 - timedelta(days=1)
        today_open = datetime.timestamp(d1)
    if today_open == 1:
        today_open = datetime.timestamp(d1)

    if today_close == 0:
        today_close = round(time.time(), 0)

    if today_close == -1:
        d2 = datetime(year_today, month_today, day_today, 2, 0, 0, tzinfo=timezone("Europe/Moscow"))
        today_close = datetime.timestamp(d2)

    orders_done = get_user_orders(db_session).filter(
        Orders.operation == "Sell", Orders.status == "Done",
        Orders.time > today_open, Orders.time < today_close,
        Orders.money_spent != None).all()

    money_profit = {}

    db_session_shared = connect("shared")
    share_info: InitialShared = get_shared_init(db_session_shared).all()
    db_session_shared.close_session()

    # лотность акций
    share_dict = {}
    for share in share_info:
        share: InitialShared = share
        share_dict.update({share.figi: share.lot})

    for order in orders_done:
        order: Orders = order
        currency = order.commission_currency
        last_value = money_profit.get(currency)
        if last_value is None:
            last_value = 0
        new_value = round(last_value + order.executedLots * order.price * share_dict.get(order.figi) +
                          order.commission_value - order.money_spent, 2)

        money_profit.update({currency: new_value})
    return money_profit
