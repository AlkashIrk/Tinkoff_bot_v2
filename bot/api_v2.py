import math
from enum import Enum

from tinkoff.invest import Client, Quotation

from bot.DB.DB import connect
from bot.DB.User import SettingsEnum
from bot.DB.queries.user.settings import get_user_settings_by_name


class CurrencySign(Enum):
    USD = "$"
    RUB = "₽"
    EUR = "€"

    @classmethod
    def value_of(cls, value):
        for k, v in cls.__members__.items():
            if k == value:
                return v.value
        else:
            return ""


def authorize(token: str):
    return Client(token)


def get_value_from_quo(value: Quotation) -> float:
    """
    Получение float из Quotation
    """
    try:
        nano = value.nano / (10 ** 9)
    except:
        nano = 0

    try:
        units = value.units
    except:
        units = 0

    value = units + nano
    return value


def set_price_to_quo(value: float) -> Quotation:
    """
    Получение Quotation из float
    """

    units = int(value // 1)
    nano = math.ceil(round(value - value // 1, 3) * (10 ** 9))
    return Quotation(units=units, nano=nano)


def get_status(status):
    """

    """
    if status == 0:
        return "Unknown"
    elif status == 1:
        return "Done"
    elif status == 2:
        return "Decline"
        return "REJECTED"
    elif status == 3:
        return "Decline"
    elif status == 4:
        return "New"
    elif status == 5:
        return "PARTIALLYFILL"


def get_min_max_price(token: str, figi=str):
    """

    """
    price = {}
    with authorize(token) as client:
        data = client.market_data.get_order_book(figi=figi, depth=10)
        price.update({"close_price": get_value_from_quo(data.close_price)})
        price.update({"last_price": get_value_from_quo(data.last_price)})
        price.update({"min_price": get_value_from_quo(data.limit_down)})
        price.update({"max_price": get_value_from_quo(data.limit_up)})

    return price


def calc_target_price(full_lot_price: float, min_increment: float, share_count: int) -> float:
    """
    Получение минимальной целевой суммы для продажи
    """

    db_session = connect("private")
    profit = get_user_settings_by_name(db_session, SettingsEnum.min_profit).value
    db_session.close_session()

    if profit <= 0.1:
        profit = 0.1

    if profit > 2:
        profit = 2

    points = get_count(min_increment)
    round_k = 10 ** points

    target_price = full_lot_price * (1 + profit / 100)

    new_price_round = target_price * round_k
    target_price = math.ceil(new_price_round)
    target_price = target_price / round_k

    target_share_price = target_price / share_count
    target_share_price = target_share_price * round_k

    target_share_price = math.ceil(target_share_price)
    target_share_price = target_share_price / round_k

    parts = target_share_price // min_increment

    if parts == 0:
        parts = 1

    target_share_price = round(min_increment * (parts + 1), points)

    return target_share_price


def get_count(number: float) -> int:
    """
    Получение количества знаков после запятой
    """
    s = str(number)
    if '.' in s:
        return abs(s.find('.') - len(s)) - 1
    else:
        return 0


def round_price(price: float, share_increment: float) -> float:
    """
    Округление цены, до разрядности share_increment
    """
    return round(price, get_count(share_increment))
