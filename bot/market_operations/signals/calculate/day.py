import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pandas as pd
from tinkoff.invest.grpc.marketdata_pb2 import CANDLE_INTERVAL_DAY

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared, OscillatorDay
from bot.DB.queries.shared.initial import get_shared_init
from bot.api_v2 import authorize, get_value_from_quo
from bot.database import base_sqlite as base_sqlite
from bot.settings import signals_days_count
from bot.settings import threads_count
from scripts import globals as global_var
from ta.momentum import RSIIndicator, StochasticOscillator, UltimateOscillator
from ta.trend import WMAIndicator


def select_info_day(company: InitialShared):
    from pytz import timezone
    from datetime import datetime, timedelta

    company_figi = company.figi
    company_name = company.ticker

    date_from = datetime.now(timezone("Europe/Moscow")) - timedelta(days=signals_days_count)
    date_to = datetime.now(timezone("Europe/Moscow"))

    result = None
    with authorize(token=global_var.token) as client:
        response = client.market_data.get_candles(
            figi=company_figi,
            from_=date_from,
            to=date_to,
            interval=CANDLE_INTERVAL_DAY
        )

        result = response.candles

    return company_name, result, company


def calculate_signals_day(shares=None, session=None):
    # TODO check work!

    if session is None:
        db_session_shared = connect("shared")
    else:
        db_session_shared = session

    if shares is None:
        shares: InitialShared = get_shared_init(db_session_shared).all()

    # количество потоков
    threads = threads_count

    if len(shares) < threads:
        threads = len(shares)

    """
    Уточним среднюю стоймость за 7 дней
    перебераем FIGI всех акций из базы 
    """
    port_plan = {}

    time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    print(time_now)
    start_time = time.time()
    with ThreadPoolExecutor(threads) as executor:
        for result in executor.map(select_info_day, shares):
            ticker = result[0]
            candle = result[1]
            share_obj = result[2]

            port_plan[ticker] = {"candle": candle, "share": share_obj}
            del result
    print("Time for get candles --- %s seconds ---" % (round(time.time() - start_time, 5)))
    print("\n")

    data_up = []
    for company_name in port_plan:
        share = db_session_shared.query(OscillatorDay).filter(OscillatorDay.ticker == company_name).all()

        if len(share) == 0:
            new_share = port_plan.get(company_name).get("share")
            # new_share = db_session_shared.query(InitialShared).filter(InitialShared.ticker == company_name).one()

            data = []
            row = OscillatorDay(
                figi=new_share.figi,
                ticker=new_share.ticker
            )

            data.append(row)
            db_session_shared.add_all(data)
            db_session_shared.commit_session()

        if port_plan[company_name] is not None:
            price_close = []
            price_open = []
            price_high = []
            price_low = []
            volume_price = []

            candles = port_plan.get(company_name).get("candle")

            for candle_history in candles:
                price_close.append(get_value_from_quo(candle_history.close))
                price_open.append(get_value_from_quo(candle_history.open))
                price_high.append(get_value_from_quo(candle_history.high))
                price_low.append(get_value_from_quo(candle_history.low))
                volume_price.append(candle_history.volume)

            df = pd.DataFrame(
                list(zip(price_open, price_close, price_low, price_high, volume_price)),
                columns=["o", "c", "l", "h", "v"]
            )
            if df.shape[0] == 0:
                continue

            inficator_rsi = RSIIndicator(
                close=df["c"],
                window=5
            )
            df["RSI"] = inficator_rsi.rsi()

            inficator_sto = StochasticOscillator(
                close=df["c"],
                low=df["l"],
                high=df["h"]
            )
            df["STO"] = inficator_sto.stoch_signal()

            indicator_uo = UltimateOscillator(
                high=df["h"],
                low=df["l"],
                close=df["c"],
            )
            df["UO"] = indicator_uo.ultimate_oscillator()

            indicator_ma = WMAIndicator(
                close=df["c"],
                window=14
            )
            df["MA"] = indicator_ma.wma()

            sto_last = round(df["STO"][df["STO"].size - 1], 2)
            rsi_last = round(df["RSI"][df["RSI"].size - 1], 2)
            uo_last = round(df["UO"][df["UO"].size - 1], 2)
            ma_last = round(df["MA"][df["MA"].size - 1], 2)
            max_price = round(ma_last * 1.05, 2)

            print("%s" % company_name)
            print("\tMA\t- %s \t (max %s)" % (ma_last, max_price))

            print("\tSTOCH\t- %s" % sto_last)
            print("\tRSI\t- %s" % rsi_last)
            print("\tUO\t- %s" % uo_last)

            data_up.append([
                rsi_last, sto_last, uo_last,
                ma_last, max_price,
                company_name]
            )

    base_sqlite.update_data(
        table="oscillator_day",
        expression="set sig_RSI=?, sig_stoch=?, sig_UO=?,  MA=?, price_max=? where ticker=?",
        data=data_up,
        base="shared"
    )

    print("Time for calculate --- %s seconds ---" % (round(time.time() - start_time, 5)))
    print("\n")
