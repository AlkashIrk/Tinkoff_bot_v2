from enum import Enum

from sqlalchemy import Column, Integer, String, REAL

from bot.DB.DB import Base_shared


class SharedSettingsEnum(str, Enum):
    pid = 'pid'
    last_check = 'last_check'
    last_value = 'last_value'
    last_restart = 'last_restart'
    last_optimise = 'last_optimise'
    last_rebalance = 'last_rebalance'


class Users(Base_shared):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    account_id = Column(String)
    token = Column(String)
    telegram_id = Column(String)
    base = Column(String)
    enable = Column(Integer)


class Status(Base_shared):
    __tablename__ = "status"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(REAL)


class OscillatorDay(Base_shared):
    __tablename__ = "oscillator_day"
    id = Column(Integer, primary_key=True)
    figi = Column(String)
    ticker = Column(String)
    sig_stoch = Column(REAL, default=0)
    sig_RSI = Column(REAL, default=0)
    sig_UO = Column(REAL, default=0)
    MA = Column(REAL, default=0)
    price_max = Column(REAL, default=0)


class InitialShared(Base_shared):
    __tablename__ = "initial"
    id = Column(Integer, primary_key=True)
    figi = Column(String)
    ticker = Column(String)
    market_open = Column(Integer, default=0)
    sig_stoch = Column(String, default='Hold')
    sig_RSI = Column(String, default='Hold')
    sig_UO = Column(String, default='Hold')
    tick = Column(Integer, default=0)
    last_data = Column(String, default=0)
    last_price = Column(REAL, default=0)
    intraday = Column(Integer, default=0)
    intraday_last_send = Column(Integer, default=0)
    lot = Column(Integer, default=0)
    minPriceIncrement = Column(REAL, default=0)
    currency = Column(String)
    name = Column(String)
