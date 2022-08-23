import time
from datetime import datetime, timedelta

from pytz import timezone
from sqlalchemy import func

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.User import Orders
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.user.balance import get_user_balance_by_currency
from bot.DB.queries.user.orders import get_user_orders


class UserStatInfo:
    def __init__(self):
        self.operation = str
        self.type = str
        self.parent_id = str
        self.base_id = int
        self.tinkoff_order_id = str
        self.req_lots = int
        self.done_lots = int
        self.currency = str
        self.commission = float
        self.price = float
        self.money_spent = float
        self.status = str
        self.figi = str
        self.ticker = str



def money_profit(today_open=0, today_close=0, base=None):
    """"
    Подсчет суммы
    """
    if base is None:
        base = "private"

    db_session = connect(base)

    if today_open == 0:
        time_today = datetime.now()
        year_today = time_today.year
        month_yoday = time_today.month
        day_today = time_today.day
        d1 = datetime(year_today, month_yoday, day_today, 0, 0, 0, tzinfo=timezone("Europe/Moscow"))
        d1 = d1 - timedelta(days=1)
        today_open = datetime.timestamp(d1)
    if today_open == 1:
        time_today = datetime.now()
        year_today = time_today.year
        month_yoday = time_today.month
        day_today = time_today.day
        d1 = datetime(year_today, month_yoday, day_today, 0, 0, 0, tzinfo=timezone("Europe/Moscow"))
        today_open = datetime.timestamp(d1)

    if today_close == 0:
        today_close = round(time.time(), 0)

    if today_close == -1:
        d2 = datetime(year_today, month_yoday, day_today, 2, 0, 0, tzinfo=timezone("Europe/Moscow"))
        today_close = datetime.timestamp(d2)

    orders_done = get_user_orders(db_session).filter(
        Orders.operation == "Sell", Orders.status == "Done",
        Orders.time > today_open, Orders.time < today_close,
        Orders.money_spent != None).all()

    money_profit = {}

    db_session_shared = connect("shared")
    share_info: InitialShared = get_shared_init(db_session_shared).all()
    db_session_shared.close_session()

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



def user_stat_info():
    db_session = connect("private")

    # подсчет средств в акциях
    money_in_stock_rows = db_session.query(
        (Orders.commission_currency).label('currency'),
        func.sum(Orders.lot_spent).label('total')) \
        .filter(Orders.status == "Done", Orders.operation == "Buy", Orders.sell_order == None) \
        .group_by(Orders.commission_currency).all()

    money_in_stock = {}
    for row in money_in_stock_rows:
        money_in_stock.update({row.currency: round(row.total, 2)})
    del money_in_stock_rows


    # TODO валюта - для отмененных
    # подсчет средств в сделках
    money_in_orders_rows = db_session.query(
        (Orders.commission_currency).label('currency'),
        func.sum(Orders.price * Orders.requestedLots).label('total')) \
        .filter(Orders.retry == 0, Orders.operation == "Sell") \
        .group_by(Orders.commission_currency).all()

    money_in_orders = {}
    for row in money_in_orders_rows:
        money_in_orders.update({row.currency: round(row.total, 2)})
    del money_in_orders_rows

    # составляем список используемых валют
    all_currencies = list(money_in_orders.keys()) + list(money_in_stock.keys())
    all_currencies = list(set(all_currencies))

    info = {}
    for curr in all_currencies:
        if curr == '-':
            continue
        try:
            balance = get_user_balance_by_currency(db_session, curr)
            money_in = money_in_stock.get(curr)

            if money_in is None:
                money_in = 0

            money_in_o = money_in_orders.get(curr)

            if money_in_o is None:
                money_in_o = 0

            info.update(
                {
                    curr:
                        {
                            "free_money": round(balance.balance, 2),
                            "blocked_money": round(balance.blocked, 2),
                            "all_money": round(balance.balance + balance.blocked + money_in, 2),
                            "money_in_orders": round(money_in_o, 2),
                            "money_in_stock": round(money_in, 2)
                        }
                }
            )
        except:
            pass

    return info