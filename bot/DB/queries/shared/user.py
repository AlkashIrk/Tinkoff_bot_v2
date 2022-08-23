from sqlalchemy.orm import Query

from ...DB import DBSession
from bot.DB.Shared import Users


def get_user(session: DBSession) -> Query:
    rows = session.query(Users)
    return rows


def get_user_by_name(session: DBSession, name: str) -> Users:
    try:
        value = session.query(Users).filter(Users.name == name).one()
    except Exception as inst:
        print("\t%s" % inst)
        value = None
    return value


def get_user_by_tgID(session: DBSession, tgID: str) -> Users:
    try:
        value = session.query(Users).filter(Users.telegram_id == tgID).one()
    except Exception as inst:
        print("\t%s" % inst)
        value = None
    return value
