import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from time import sleep

import pandas as pd
from tinkoff.invest.grpc.marketdata_pb2 import CANDLE_INTERVAL_5_MIN

import bot.database.base_sqlite as base_sqlite
import scripts.globals as global_var
from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.queries.shared.initial import get_shared_init
from bot.api_v2 import authorize, get_value_from_quo
from bot.cfg.parse_params import get_params
from bot.market_operations.signals.sign_intraday import sign_intraday
from bot.settings import threads_count, send_intraday
from ta.momentum import RSIIndicator, StochasticOscillator, UltimateOscillator

global_var.init()


# осциляторы по акциям
intraday_data = {}

historic_candle = {}


def append_space(input_str: str, lenght=8):
    input_len = len(input_str)
    if input_len < lenght:
        output_str = input_str + " " * (lenght - input_len)
    else:
        output_str = input_str
    return output_str


def check_signals_sto(data, last_signal):
    if last_signal is None:
        last_signal = "Hold"

    if data[1] is None or data[0] is None:
        return "Hold"

    if data[0] <= 80 and data[1] > 80:
        return "Pre_Sell"

    if last_signal == "Pre_Sell":
        if data[0] >= 80 and data[1] < 80:
            return "Need_Sell"

    if last_signal == "Need_Sell" or last_signal == "Pre_Sell":
        if data[1] < 60:
            return "Hold"

    if data[0] >= 20 and data[1] < 20:
        return "Pre_Buy"

    if last_signal == "Pre_Buy":
        if data[0] < 20 and data[1] >= 20:
            return "Need_Buy"

    if last_signal == "Need_Buy" or last_signal == "Pre_Buy":
        if data[1] >= 30:
            return "Hold"

    return last_signal


def check_signals_rsi(data, last_signal):
    if last_signal is None:
        last_signal = "Hold"

    if last_signal == "Hold":
        if data[0] >= 60 and data[1] >= 60:
            last_signal = "Pre_Sell"
        if data[0] <= 40 and data[1] <= 40:
            last_signal = "Pre_Buy"

    if data[1] is None or data[0] is None:
        return "Hold"

    if data[0] <= 65 and data[1] > 65:
        return "Pre_Sell"

    if last_signal == "Pre_Sell":
        if data[1] >= 70:
            return "Need_Sell"

    if last_signal == "Need_Sell":
        if data[1] < 50:
            return "Hold"

    if data[0] >= 35 and data[1] < 35:
        return "Pre_Buy"

    if last_signal == "Pre_Buy":
        if data[1] < 30:  # and data[1] >= 20:
            return "Need_Buy"

    if last_signal == "Need_Buy" or last_signal == "Pre_Buy":
        if data[1] >= 50:
            return "Hold"

    return last_signal


def check_signals_uo(data, last_signal):
    if last_signal is None:
        last_signal = "Hold"

    if data[1] is None or data[0] is None:
        return "Hold"

    if data[1] > 70:
        return "Need_Sell"

    if data[0] <= 70 and data[1] > 70:
        return "Need_Sell"

    if last_signal == "Need_Sell":
        if data[1] < 65:
            return "Hold"

    if data[1] < 40:
        return "Need_Buy"

    if data[0] >= 40 and data[1] < 40:
        return "Need_Buy"

    if last_signal == "Need_Buy":
        if data[1] >= 45:
            return "Hold"

    return last_signal


def select_info(company, day_delta=None):
    from pytz import timezone
    from datetime import datetime, timedelta

    company_figi = company[0]
    company_name = company[1]

    date_from = datetime.now(timezone("Europe/Moscow")) - timedelta(days=1)
    date_to = datetime.now(timezone("Europe/Moscow"))

    if day_delta is not None:
        date_from = day_delta["date_from"] - timedelta(days=1)
        date_to = day_delta["date_to"] - timedelta(days=1)

    day_delta = {
        "date_from": date_from,
        "date_to": date_to
    }

    # date_from = date_from.isoformat()
    # date_to = date_to.isoformat()
    with authorize(token=global_var.token) as client:
        response = client.market_data.get_candles(
            figi=company_figi,
            from_=date_from,
            to=date_to,
            interval=CANDLE_INTERVAL_5_MIN
        )
        result = response.candles

    if len(result) < 20:
        # TODO сделать обнуление через 48 часов
        if historic_candle.get(company) is not None:
            result = historic_candle.get(company) + result

    if len(result) < 20:
        sleep(0.5)
        print("Мало данных по компании %s\nсобираем данные за предыдущие дни" % company_name)
        result_append = select_info(company=company, day_delta=day_delta)
        historic_candle.update({company: result_append[1]})
        result = result_append[1] + result

    return company_name, result


def calculate_signals_new(args=[]):
    sql = "figi in ({seq})".format(seq=",".join(["?"] * len(args)))

    select_figi = base_sqlite.select(
        what="figi, ticker",
        table="initial",
        base="shared",
        expression=sql,
        data=args
    )

    """    
    Уточним среднюю стоймость за 7 дней
    перебераем FIGI всех акций из базы 
    """
    port_plan = {}

    time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    print(time_now)
    start_time = time.time()
    with ThreadPoolExecutor(threads_count) as executor:
        for result in executor.map(select_info, select_figi):
            port_plan[result[0]] = result[1]
            del result
    print("Time for get candles --- %s seconds ---" % (round(time.time() - start_time, 5)))
    print("\n")

    data_up = []
    for company_name in port_plan:
        if port_plan[company_name] is not None:
            price_close = []
            price_open = []
            price_high = []
            price_low = []
            volume_price = []

            for elements in port_plan[company_name]:
                price_close.append(get_value_from_quo(elements.close))
                price_open.append(get_value_from_quo(elements.open))
                price_high.append(get_value_from_quo(elements.high))
                price_low.append(get_value_from_quo(elements.low))
                volume_price.append(elements.volume)

            df = pd.DataFrame(
                list(zip(price_open, price_close, price_low, price_high, volume_price)),
                columns=["o", "c", "l", "h", "v"]

            )

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

            try:
                last_signal = base_sqlite.select(
                    what="sig_stoch, sig_RSI, sig_UO",
                    table="initial",
                    base="shared",
                    expression="ticker='%s'" % company_name
                )
            except:
                last_signal = None

            sto_last = round(df["STO"][df["STO"].size - 1], 2)
            sto_pre_last = round(df["STO"][df["STO"].size - 2], 2)
            data = [sto_pre_last, sto_last]
            signal_sto = check_signals_sto(data, last_signal[0][0])

            rsi_last = round(df["RSI"][df["RSI"].size - 1], 2)
            rsi_pre_last = round(df["RSI"][df["RSI"].size - 2], 2)
            data = [rsi_pre_last, rsi_last]
            signal_rsi = check_signals_rsi(data, last_signal[0][1])

            uo_last = round(df["UO"][df["UO"].size - 1], 2)
            uo_pre_last = round(df["UO"][df["UO"].size - 2], 2)
            data = [uo_pre_last, uo_last]
            signal_uo = check_signals_uo(data, last_signal[0][2])

            data_up.append([
                signal_rsi,
                signal_sto,
                signal_uo,
                company_name]
            )

            print("%s" % company_name)
            signal_sto = append_space(signal_sto)
            print("\tSTOCH\t- %s\t(%s -> %s)" % (signal_sto, sto_pre_last, sto_last))

            signal_rsi = append_space(signal_rsi)
            print("\tRSI\t- %s\t(%s -> %s)" % (signal_rsi, rsi_pre_last, rsi_last))

            signal_uo = append_space(signal_uo)
            print("\tUO\t- %s\t(%s -> %s)" % (signal_uo, uo_pre_last, uo_last))

            if send_intraday:
                signals = {
                    "STOCH": {"last": sto_last, "new": sto_pre_last},
                    "RSI": {"last": rsi_last, "new": rsi_pre_last},
                    "UO": {"last": uo_last, "new": uo_pre_last}
                }
                intraday_data.update({company_name: signals})

    base_sqlite.update_data(
        table="initial",
        expression="set sig_RSI=?, sig_stoch=?, sig_UO=? where ticker=?",
        data=data_up,
        base="shared"
    )
    print("Time for calculate --- %s seconds ---" % (round(time.time() - start_time, 5)))
    print("\n")

    if send_intraday:
        try:
            sign_intraday(intraday_data)
        except:
            pass


args = get_params()
mode = None

if args.mode:
    mode = args.mode
else:
    exit()

if args.debug:
    debug_mode: str = args.debug
    if debug_mode.upper() == "ON":
        db_session_shared = connect("shared")
        sha: InitialShared = get_shared_init(db_session_shared).filter(InitialShared.ticker == "MAC").one()
        #
        # last_data = sha.last_data
        #
        # temp = datetime.strptime(last_data, '%Y-%m-%d %H:%M:%S').timestamp()

        # sha.intraday_last_send = int(time.time())
        # db_session_shared.commit_session()
        # a = global_var.telegram_token
        # send_message(sha)

        signals = {
            "STOCH": {"last": 40, "new": 0},
            "RSI": {"last": 60, "new": 0},
            "UO": {"last": 50, "new": 0}
        }

        intraday_data.update({"SGZH": signals})
        sign_intraday(intraday_data)
