from ...DB import DBSession
from bot.DB.User import Balance


def get_user_balance_by_currency(session: DBSession, currency: str) -> Balance:
    value = session.query(Balance).filter(Balance.name == currency).one()
    return value


def set_user_balance_by_currency(session: DBSession, currency: str, value: float):
    session.query(Balance).filter(Balance.name == currency).update({Balance.value: value})
    session.commit_session()
