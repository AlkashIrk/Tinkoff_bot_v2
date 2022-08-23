# Refactored
import asyncio
import os
import sys
import time
from datetime import datetime
from time import sleep

from tinkoff.invest import SubscriptionInterval, CandleInstrument, AsyncClient, InfoInstrument, MarketDataResponse, \
    TradingStatus, SecurityTradingStatus
from tinkoff.invest.market_data_stream.async_market_data_stream_manager import AsyncMarketDataStreamManager

from bot.DB.DB import connect
from bot.DB.Shared import SharedSettingsEnum, Users, InitialShared
from bot.DB.queries.shared.initial import get_shared_init, get_shared_init_by_figi
from bot.DB.queries.shared.status import set_shared_settings_by_name
from bot.DB.queries.shared.user import get_user
from bot.api_v2 import get_value_from_quo
from bot.cfg.logs_work import debuginfo
from bot.database import base_sqlite
from bot.database.service_for_base import optimize_base
from bot.market_operations.recreate_orders.recreate_on_open import check_last_orders

# свеча в 1 минуту - для триггера сигналов
CANDLES_INTERVAL = SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE

tickers_view = {}


def daemon_candles(user_token):
    db_session_shared = connect("shared")
    base_sqlite.check_column(base="shared", table="initial",
                             column="tick", column_type="integer", default_value=0)

    # последняя активность
    base_sqlite.check_column(base="shared", table="initial", column="last_data", column_type="text", default_value=0)

    # последняя цена
    base_sqlite.check_column(base="shared", table="initial", column="last_price", column_type="integer",
                             default_value=0)

    base_sqlite.check_journal_pragma("shared")

    print('\33]0;Candles\a', end='')
    sys.stdout.flush()
    pid = os.getpid()

    set_shared_settings_by_name(db_session_shared, SharedSettingsEnum.pid, pid)
    optimize_base()

    while True:
        os.system("cls")
        now = datetime.now()
        date_time = now.strftime("%d.%m.%Y %H:%M:%S")
        os.system("title CANDELS start: %s" % date_time)
        try:
            asyncio.run(subscribe(user_token))
        except Exception as inst:
            debuginfo("\tError here")
            print("\t%s" % inst)
        sleep(15)


# отслеживаем свечи, записываем их в базу
async def subscribe(user_token):
    global tickers_view
    while True:
        db_session = connect("shared")
        orders_active = get_shared_init(db_session).all()

        candle_subs = []
        info_subs = []
        for stock_settings in orders_active:
            stock_settings: InitialShared = stock_settings
            tickers_view[stock_settings.ticker] = {"value": -1, "last_set": 0}
            candle_subs.append(CandleInstrument(figi=stock_settings.figi, interval=CANDLES_INTERVAL))
            info_subs.append(InfoInstrument(figi=stock_settings.figi))
        del orders_active

        get_shared_init(db_session).update({InitialShared.market_open: 0})
        db_session.commit_session()

        for candle in candle_subs:
            ticker_figi = candle.figi
            tickers_view[ticker_figi] = {"value": -1, "last_set": 0}
            del ticker_figi
            del candle

        async with AsyncClient(user_token) as client:
            market_data_stream: AsyncMarketDataStreamManager = (
                client.create_market_data_stream()
            )
            market_data_stream.stop()
            sleep(1)
            market_data_stream.candles.subscribe(candle_subs)
            del candle_subs

            sleep(2)
            market_data_stream.info.subscribe(info_subs)

            async for marketdata in market_data_stream:
                marketdata: MarketDataResponse = marketdata
                # if marketdata.subscribe_candles_response:
                #     print(marketdata)
                if marketdata.candle:
                    candle_event(marketdata.candle)
                if marketdata.trading_status:
                    info_event(marketdata.trading_status)
        sleep(30)


def candle_event(event):
    from dateutil import tz
    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz("Europe/Moscow")

    ticker_figi = event.figi
    if event.interval == CANDLES_INTERVAL:
        last_price = get_value_from_quo(event.close)
        last_activity = event.last_trade_ts
        last_activity = last_activity.astimezone(to_zone).strftime("%Y-%m-%d %H:%M:%S")
        try:
            base_sqlite.command_adw(
                what="UPDATE initial set tick=tick+1, last_data='%s', last_price='%s' where figi='%s'"
                     % (last_activity, last_price, ticker_figi),
                base="shared"
            )
        except Exception as inst:
            debuginfo("\tError here")
            print("\t%s" % inst)

        # вызываем триггер для перевыставления акций
        trigger_start(ticker_figi)
        return

    try:
        figi = event.figi
        candle_open = get_value_from_quo(event.open)
        candle_close = get_value_from_quo(event.close)
        candle_low = get_value_from_quo(event.low)
        candle_high = get_value_from_quo(event.high)

        candle_volume = event.volume
        candle_time = event.time

        print("Figi: %s\t\t(%s)\n\t\topen:\t%s\t\tclose:\t%s\t\t\tlow:\t%s\t\t\thigh:\t%s\t\t\tvol:\t%s" % (
            figi, candle_time, candle_open, candle_close, candle_low, candle_high, candle_volume))

    except Exception as inst:
        debuginfo("Error here")
        print("\t%s" % inst)


def info_event(event: TradingStatus):
    db_session = connect("shared")
    if event.trading_status == SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING:
        a = 0
    else:
        get_shared_init(db_session).filter(InitialShared.figi == event.figi).update({InitialShared.market_open: 0})
        db_session.commit_session()




def trigger_start(ticker_figi):
    """
    при старте торгов начинают идти свечи
    при открытии торгов необходимо перевыставить отмененные заявки
    """

    global tickers_view
    db_session = connect("shared")

    # tickers_view[] - смотрим ли мы за данной свечей
    # 0 - нет
    # 1 - да
    timestamp = round(time.time())

    if tickers_view[ticker_figi]["value"] <= 1:
        tickers_view[ticker_figi]["value"] += 1
        tickers_view[ticker_figi]["last_set"] = timestamp
        time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print(time_now)
        print("\tfigi %s - set to %s" % (ticker_figi, tickers_view[ticker_figi]["value"]))

    try:
        select_ticker = get_shared_init_by_figi(db_session, ticker_figi)
        ticker = select_ticker.ticker
        market_open = select_ticker.market_open
    except Exception as inst:
        debuginfo("Error here")
        print("\t%s" % inst)
        ticker = ticker_figi
        market_open = 0

    # если есть свечи по акции - проверяем невыполненные лоты пользователей
    if market_open == 0 \
            and tickers_view[ticker_figi]["value"] >= 1:

        time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print(time_now)
        print("\t%s - market_open set to %s" % (ticker, 1))
        check_last_orders_users(ticker_figi, ticker)
        try:
            get_shared_init(db_session).filter(InitialShared.ticker == ticker).update({InitialShared.market_open: 1})
            db_session.commit_session()
        except Exception as inst:
            debuginfo("Error here")
            print("\t%s" % inst)


def check_last_orders_users(ticker_figi: str, ticker: str):
    """
    проверка отмененных ордеров
    при их наличии, пересоздание
    """
    try:
        db_session = connect("shared")
        select_users = get_user(db_session).filter(Users.enable == 1).all()
    except Exception as inst:
        debuginfo("Error here")
        print("\t%s" % inst)
        select_users = []

    for user_data in select_users:
        user_data: Users = user_data
        check_last_orders(
            ticker_figi=ticker_figi,
            ticker=ticker,
            base=user_data.base,
            user=user_data.name,
            token=user_data.token,
            telegram_id=int(user_data.telegram_id),
            account_id=user_data.account_id
        )
