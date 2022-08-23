from bot.DB.DB import connect
from bot.DB.User import SettingsEnum
from bot.DB.queries.user.balance import get_user_balance_by_currency
from bot.DB.queries.user.settings import get_user_settings_by_name


def increase_min_balance(value: float, currency: str):
    """
    Увеличиваем минимальный баланс для валюты
    """
    if value < 0:
        return
    db_session = connect("private")
    if get_user_settings_by_name(db_session, SettingsEnum.balance_autoappend).value == 1:
        balance_info = get_user_balance_by_currency(db_session, currency)
        balance_value = balance_info.min_value
        new_balance = round(balance_value + value, 2)
        balance_info.min_value = new_balance
        db_session.commit_session()
