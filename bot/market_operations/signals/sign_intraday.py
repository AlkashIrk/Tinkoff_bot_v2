import time
from datetime import datetime
from time import sleep

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.queries.shared.initial import get_shared_init
from bot.api_v2 import CurrencySign
from bot.model.Signals import Signal, Signals
from bot.settings import intraday_min
from bot.telegram.send_to_telegram import send_to_telegram

intraday_data = {}
chat_id = -1
telegram_token = 'your_token'


def sign_intraday(iday_data):
    # отправка интрадей сигнала в чат
    global intraday_data

    intraday_data = iday_data

    db_session_shared = connect("shared")
    signal_send: InitialShared = get_shared_init(db_session_shared).filter(InitialShared.intraday == 1).all()

    signals_on = []
    for element in signal_send:
        signals_on.append(element.ticker)

    for company_ticker in intraday_data:
        if company_ticker not in signals_on:
            continue

        share_info: InitialShared = get_shared_init(db_session_shared).filter(
            InitialShared.ticker == company_ticker).one()

        stoch_info: dict = intraday_data[company_ticker]
        last_send = share_info.intraday_last_send

        if last_send == 0 or last_send < time.time() - 60 * intraday_min:
            signal = 0

            stoch: Signal = stoch_info.STOCH
            rsi: Signal = stoch_info.RSI
            uo: Signal = stoch_info.UO
            keltner: Signal = stoch_info.Keltner
            candels: Signal = stoch_info.candels

            if stoch.previous_value > 20 and stoch.last_value <= 20 \
                    or (
                    stoch.previous_value < 20 and stoch.last_value <= 20 and stoch.last_value < stoch.previous_value):
                stoch.sell = 1
                stoch.default_message()
                signal += 1

            if rsi.previous_value > 35 and rsi.last_value <= 35 \
                    or (rsi.previous_value < 35 and rsi.last_value <= 35 and rsi.last_value < rsi.previous_value):
                rsi.sell = 1
                rsi.default_message()
                signal += 1

            if uo.previous_value > 40 and uo.last_value <= 40 \
                    or (uo.previous_value < 40 and uo.last_value <= 40 and uo.last_value < uo.previous_value):
                uo.sell = 1
                uo.default_message()
                signal += 1

            if candels.last_value < keltner.last_value:
                keltner.sell = 1
                keltner.message = "\n\t\t\t\tцена ниже канала"

            if candels.previous_value >= keltner.previous_value and candels.last_value < keltner.last_value:
                keltner.sell = 1
                keltner.message = "\n\t\t\t\tцена ушла ниже канала"

            if keltner.sell == 1 and signal >= 2:
                last_candle = share_info.last_data
                last_candle = datetime.strptime(last_candle, '%Y-%m-%d %H:%M:%S').timestamp()

                if last_candle < last_send or share_info.market_open == 0:
                    continue
                send_message(share_info)
                share_info.intraday_last_send = int(time.time())
                db_session_shared.commit_session()

    db_session_shared.commit_session()


def send_message(share_info: InitialShared):
    global intraday_data
    company_with_url = '<a href="https://www.tinkoff.ru/invest/stocks/%s/">%s (%s)</a>' \
                       % (share_info.ticker, share_info.name, share_info.ticker)

    to_print = "Сигнал на покупку"
    to_print = "%s\n\t%s" % (to_print, company_with_url)

    price = "Цена: %s%s" % (share_info.last_price, CurrencySign.value_of(share_info.currency))
    to_print = "%s\n\t%s\n" % (to_print, price)

    ticker_data: Signals = intraday_data[share_info.ticker]

    attrs = ticker_data.__dict__

    for attr in attrs:
        value = attrs[attr]
        if isinstance(value, Signal):
            value: Signal = value
            element = value._name

            if value.sell == 1:
                to_print = to_print + "\n\t\t" + element + value.message
        del attr
    del attrs

    send_to_telegram(
        message=to_print,
        chat_id=chat_id,
        telegram_token=telegram_token,
        url_param="&parse_mode=html&disable_web_page_preview=True"
    )
    sleep(3)
