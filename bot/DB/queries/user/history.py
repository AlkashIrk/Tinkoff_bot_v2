from sqlalchemy.orm import Query

from bot.DB.User import History
from ...DB import DBSession


def get_user_history(session: DBSession) -> Query:
    rows = session.query(History)
    return rows
