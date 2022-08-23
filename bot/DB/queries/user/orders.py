from sqlalchemy import func
from sqlalchemy.orm import Query

from bot.DB.User import Orders, InitialUser
from ...DB import DBSession


def get_user_orders(session: DBSession) -> Query:
    rows = session.query(Orders)
    return rows


def stocks_in_deposit(session: DBSession) -> Query:
    """
    Количество акций в портфеле
    """

    rows = session.query(InitialUser.ticker, Orders.figi,
                         func.sum(Orders.executedLots).label('total')) \
        .filter(
        InitialUser.figi == Orders.figi,
        Orders.operation == "Buy",
        Orders.status == "Done",
        Orders.sell_order == None).group_by(Orders.figi)
    return rows


def stocks_in_orders(session: DBSession) -> Query:
    """
    Количество акций в не закрытых сделках
    """

    rows = session.query(
        InitialUser.ticker, Orders.figi,
        func.sum(Orders.requestedLots).label('total')) \
        .filter(
        InitialUser.figi == Orders.figi,
        Orders.operation == "Sell",
        Orders.retry == 0) \
        .group_by(Orders.figi)
    return rows
