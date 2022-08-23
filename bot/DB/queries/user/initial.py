from typing import Tuple

from sqlalchemy.orm import Query

from bot.DB.User import InitialUser
from ..shared.initial import get_shared_init
from ...DB import DBSession, connect
from ...Shared import InitialShared


def get_user_init(session: DBSession) -> Query:
    rows = session.query(InitialUser)
    return rows


def get_user_init_by_figi(session: DBSession, figi: str) -> InitialUser:
    value = session.query(InitialUser).filter(InitialUser.figi == figi).one()
    return value


def set_user_init_by_figi(session: DBSession, figi: str, value: float):
    session.query(InitialUser).filter(InitialUser.figi == figi).update({InitialUser.value: value})
    session.commit_session()


def get_curr_list(session: DBSession) -> Tuple[dict, dict]:
    """
    Список акций по валютам
    """
    db_session_shared = connect("shared")
    shares = get_shared_init(db_session_shared).all()

    stock_info = {}
    for share in shares:
        share: InitialShared = share
        stock_info.update({share.ticker: share.currency})
        del share

    del shares
    db_session_shared.close_session()

    stock_user = get_user_init(session).all()

    stock_user_info = {}
    stock_curr = {}

    # перебор акций пользователя
    # переделать на ООП
    for share in stock_user:
        share: InitialUser = share

        # если акции нет в общей БД - пропускаем
        try:
            value = stock_info.get(share.ticker)
        except:
            continue

        if value is not None:
            last = stock_user_info.get(value)
            if last is None:
                last = {"enable": 0, "total": 0, "list": []}

            info_list = last.get("list")
            info_list.append(share.ticker)
            enable_value = last.get("enable")

            if share.enable_buy == 1:
                enable_value = enable_value + 1

            total_value = last.get("total")
            total_value = total_value + 1

            last.update({"enable": enable_value, "total": total_value, "list": info_list})

            stock_user_info.update({value: last})
            stock_curr.update({share.ticker: value})

        del share

    return stock_user_info, stock_curr
