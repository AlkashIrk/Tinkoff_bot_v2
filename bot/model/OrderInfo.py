from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.queries.shared.initial import get_shared_init


class OrderInfo:
    def __init__(self):
        self.operation = str
        self.type = str
        self.parent_id = str
        self.base_id = int
        self.tinkoff_order_id = str
        self.req_lots = int
        self.done_lots = int
        self.currency = str
        self.commission = float
        self.price = float
        self.money_spent = float
        self.status = str
        self.figi = str
        self.ticker = str

    @property
    def ticker(self):
        return self._ticker

    @ticker.setter
    def ticker(self, value):
        self._ticker = value

    @property
    def figi(self):
        return self._figi

    @figi.setter
    def figi(self, value):
        self._figi = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def base_id(self):
        return self._base_id

    @base_id.setter
    def base_id(self, value):
        self._base_id = value

    @property
    def tinkoff_order_id(self):
        return self._tinkoff_order_id

    @tinkoff_order_id.setter
    def tinkoff_order_id(self, value):
        self._tinkoff_order_id = value

    @property
    def operation(self):
        return self._operation

    @operation.setter
    def operation(self, value):
        self._operation = value

    @property
    def req_lots(self):
        return self._req_lots

    @req_lots.setter
    def req_lots(self, value):
        self._req_lots = value

    @property
    def done_lots(self):
        return self._done_lots

    @done_lots.setter
    def done_lots(self, value):
        self._done_lots = value

    @property
    def money_spent(self):
        return self._money_spent

    @property
    def commission(self):
        return self._commission

    @property
    def currency(self):
        return self._currency

    @property
    def price(self):
        return self._price

    @currency.setter
    def currency(self, value):
        self._currency = value

    @commission.setter
    def commission(self, value):
        self._commission = value

    @price.setter
    def price(self, value):
        self._price = value

    @money_spent.setter
    def money_spent(self, value):
        self._money_spent = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def getLotInfo(self) -> InitialShared:
        db_session_shared = connect("shared")
        if self.figi != str:
            share_info: InitialShared = get_shared_init(db_session_shared).filter(
                InitialShared.figi == self.figi).one()
            db_session_shared.close_session()
            return share_info
        if self.ticker != str:
            share_info: InitialShared = get_shared_init(db_session_shared).filter(
                InitialShared.ticker == self.ticker).one()
            db_session_shared.close_session()
            return share_info

