import os

from tinkoff.invest import InstrumentShort

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared, Users
from bot.api_v2 import authorize
from bot.daemons.daemon_service import update_stock_info
from bot.market_operations.signals.calculate.day import calculate_signals_day


def add_share(search_query):
    """
    Добавление акции в общую базу
    """

    db_session_shared = connect("shared")

    try:
        user = db_session_shared.query(Users).first()
        user: Users = user
    except:
        return

    with authorize(user.token) as client:
        results = client.instruments.find_instrument(query=search_query)

    for result in results.instruments:
        result: InstrumentShort = result

        if result.instrument_type == 'share':
            share_info = "%s\nticker = %s\nfigi = %s" % (result.name, result.ticker, result.figi)
            share_info = "%s\n%s %s" % ("Добавить:", share_info, "\nY/N?")

            data = input(share_info)

            if "Y" not in data.upper():
                os.system("cls")
                continue

            info = db_session_shared.query(InitialShared).filter(InitialShared.figi == result.figi).all()

            if len(info) == 0:
                data = []
                row = InitialShared(
                    figi=result.figi,
                    ticker=result.ticker,
                    name=result.name,
                    intraday=1)

                data.append(row)
                db_session_shared.add_all(data)
                db_session_shared.commit_session()

                share = db_session_shared.query(InitialShared).filter(InitialShared.figi == result.figi).all()
                update_stock_info(shares=share, session=db_session_shared)
                calculate_signals_day(shares=share)

            if "Y" in data.upper():
                break
