# Refactored
from bot.DB.DB import connect
from bot.DB.queries.user.initial import get_user_init_by_figi
from bot.market_operations.recreate_orders.open_buy import recreate_buy_order
from bot.market_operations.recreate_orders.open_sell import recreate_sell_order


def check_last_orders(ticker_figi: str, account_id: str, ticker: str,
                      telegram_id: int, token: str, user="NULL", base=None):
    """
    Проверка отмененных ордеров
    при их наличии, пересоздание
    """
    if base is None:
        base = "private"
    db_session = connect(base)
    print("\tuser %s\n\t\tcheck_last_orders %s" % (user, ticker))

    try:
        recreate_buy_order(base=base, ticker_figi=ticker_figi)
    except:
        print("skipped")

    try:
        data = get_user_init_by_figi(db_session, ticker_figi)
        if data.enable == 1:
            recreate_sell_order(base=base, token=token, account_id=account_id, telegram_id=telegram_id,
                                ticker=ticker, ticker_figi=ticker_figi)
    except:
        pass
