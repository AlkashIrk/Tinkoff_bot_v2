from ...DB import DBSession
from bot.DB.User import Settings


def get_user_settings_by_name(session: DBSession, name: str) -> Settings:
    value = session.query(Settings).filter(Settings.name == name).one()
    return value


def set_user_settings_by_name(session: DBSession, name: str, value: float):
    session.query(Settings).filter(Settings.name == name).update({Settings.value: value})
    session.commit_session()
