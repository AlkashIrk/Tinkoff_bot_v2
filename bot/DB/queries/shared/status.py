from bot.DB.Shared import Status
from ...DB import DBSession


def get_shared_settings_by_name(session: DBSession, name: str) -> Status:
    value = session.query(Status).filter(Status.name == name).one()
    return value


def set_shared_settings_by_name(session: DBSession, name: str, value: float):
    operation_complete = False
    while not operation_complete:
        row = get_shared_settings_by_name(session=session, name=name)
        row.value = value
        operation_complete = session.commit_session()
