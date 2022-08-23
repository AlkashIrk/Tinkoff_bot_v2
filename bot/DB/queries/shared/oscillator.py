from ...DB import DBSession
from bot.DB.Shared import OscillatorDay


def get_by_figi(session: DBSession, figi: str) -> OscillatorDay:
    try:
        value = session.query(OscillatorDay).filter(OscillatorDay.figi == figi).one()
    except Exception as inst:
        print("\t%s" % inst)
        value = None
    return value
