from enum import Enum

from sqlalchemy import Column, Integer, String, REAL

from bot.DB.DB import Base_user


class SettingsEnum(str, Enum):
    min_balance = 'min_balance'
    lot_price = 'lot_price'
    min_profit = 'min_profit'
    rebalance_stock_koeff = 'rebalance_stock_koeff'
    last_update_portfolio = 'last_update_portfolio'
    last_optimise_base = 'last_optimise_base'
    last_backup = 'last_backup'
    only_sell = 'only_sell'
    decline_long_buy = 'decline_long_buy'
    balance_autoappend = 'balance_autoappend'


class Settings(Base_user):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(REAL)


class Balance(Base_user):
    __tablename__ = "balance"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    balance = Column(REAL)
    blocked = Column(REAL)
    min_value = Column(REAL)
    lot_price = Column(REAL)


class Orders(Base_user):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(REAL)
    figi = Column(String)
    orderID = Column(String)
    operation = Column(String)
    price = Column(REAL)
    target = Column(REAL)
    status = Column(String)
    requestedLots = Column(Integer)
    executedLots = Column(Integer)
    commission_currency = Column(String)
    commission_value = Column(REAL)
    money_spent = Column(REAL)
    lot_spent = Column(REAL, default=0)
    sell_order = Column(String)
    retry = Column(Integer, default=0)
    re_sell = Column(Integer, default=0)
    telegram_mess_id = Column(Integer)
    telegram_complete_mess_id = Column(Integer)

    def __repr__(self):
        return f'{self.figi} {self.orderID}'


class Stock(Orders):
    def __init__(self):
        self.figi = str
        self.total = int


class History(Base_user):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String)
    money_in_stock = Column(REAL, default=0)
    money_in_orders = Column(REAL, default=0)
    free_money = Column(REAL)
    profit_money = Column(REAL, default=0)
    profit_percent = Column(REAL, default=0)
    send_to_telegram = Column(Integer, default=0)
    currency = Column(String)
    PayIn = Column(REAL, default=0)


class InitialUser(Base_user):
    __tablename__ = "initial"
    id = Column(Integer, primary_key=True)
    figi = Column(String)
    ticker = Column(String)
    buy = Column(Integer)
    stock_in_portfel = Column(Integer)
    max_stock = Column(Integer)
    autobalance = Column(Integer)
    last_buy_time = Column(REAL)
    enable = Column(Integer)
    enable_buy = Column(Integer)
    enable_sell = Column(Integer)
