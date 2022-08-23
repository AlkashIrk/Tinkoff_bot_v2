from sqlalchemy import func
from sqlalchemy.orm import Query

from bot.DB.Shared import InitialShared
from ...DB import DBSession


def get_shared_init(session: DBSession) -> Query:
    rows = session.query(InitialShared)
    return rows


def get_ticks_in_DB(session: DBSession) -> int:
    value = session.query(func.sum(InitialShared.tick).label('total')).one()
    return value.total


def get_shared_init_by_figi(session: DBSession, figi: str) -> InitialShared:
    value = session.query(InitialShared).filter(InitialShared.figi == figi).one()
    return value


def get_shared_init_by_ticker(session: DBSession, ticker: str) -> InitialShared:
    value = session.query(InitialShared).filter(InitialShared.ticker == ticker).one()
    return value


def set_shared_init_by_figi(session: DBSession, figi: str, att: InitialShared, value):
    session.query(InitialShared).filter(InitialShared.figi == figi).update({att: value})
    session.commit_session()


def set_shared_init_by_ticker(session: DBSession, ticker: str, att, value):
    session.query(InitialShared).filter(InitialShared.ticker == ticker).update({InitialShared.att: value})
    session.commit_session()
