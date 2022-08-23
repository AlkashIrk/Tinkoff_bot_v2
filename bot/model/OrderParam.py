class OrderParam:
    def __init__(self):
        self._ticker = str
        self._ticker_figi = str
        self._last_price = float
        self._lots_may_buy = int

    @property
    def ticker(self):
        return self._ticker

    @property
    def ticker_figi(self):
        return self._ticker_figi

    @property
    def last_price(self):
        return self._last_price

    @property
    def lots_may_buy(self):
        return self._lots_may_buy

    @ticker.setter
    def ticker(self, value):
        self._ticker = value

    @ticker_figi.setter
    def ticker_figi(self, value):
        self._ticker_figi = value

    @last_price.setter
    def last_price(self, value):
        self._last_price = value

    @lots_may_buy.setter
    def lots_may_buy(self, value):
        self._lots_may_buy = value
