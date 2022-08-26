from sqlalchemy import func

from bot.DB.DB import connect, DBSession
from bot.DB.User import Orders
from bot.DB.queries.user.balance import get_user_balance_by_currency


class BalanceInfo:
    base = "private"
    _db_session: DBSession = connect(base)

    def __init__(self, currency: str = None, base=None):
        # --------------------------------------
        # костыли для telegram
        if base is None:
            base = "private"
        BalanceInfo._db_session = connect(base)
        # --------------------------------------

        self.currency = currency
        self.free_money = 0
        self.blocked_money = 0

        self.money_in_orders = 0
        self.money_in_stock = 0
        self.all_money = 0

        self.get_money_in_stock(currency)

        self.get_user_money()
        self.calculate_total_money()

    def __repr__(self):
        return f'{self.currency} {self.all_money}'

    def get_user_money(self):
        try:
            user_balance = get_user_balance_by_currency(BalanceInfo._db_session, self.currency)

            self.free_money = round(user_balance.balance - user_balance.blocked, 2)
            self.blocked_money = round(user_balance.blocked, 2)
        except:
            self.free_money = 0
            self.blocked_money = 0

    def get_money_in_stock(self, currency):
        try:
            money_in_stock_rows = BalanceInfo._db_session.query(
                Orders.commission_currency.label('currency'),
                func.sum(Orders.lot_spent).label('total')) \
                .filter(Orders.status == "Done", Orders.operation == "Buy", Orders.sell_order == None,
                        Orders.commission_currency == currency) \
                .group_by(Orders.commission_currency).one()

            self.money_in_stock = round(money_in_stock_rows.total, 2)
        except Exception as inst:
            print("\t%s" % inst)
            self.money_in_stock: float = 0

    def get_money_in_orders(self, currency):
        try:
            money_in_orders_rows = BalanceInfo._db_session.query(
                (Orders.commission_currency).label('currency'),
                func.sum(Orders.price * Orders.requestedLots).label('total')) \
                .filter(Orders.retry == 0, Orders.operation == "Sell",
                        Orders.commission_currency == currency) \
                .group_by(Orders.commission_currency).one()

            self.money_in_orders = round(money_in_orders_rows.total, 2)
        except:
            self.money_in_orders: float = 0

    def calculate_total_money(self):
        total_money = self.free_money + self.blocked_money + self.money_in_orders + self.money_in_stock
        self.all_money = round(total_money, 2)


class UserBalance:
    """
    Полная информация по балансу пользователя
    """

    def __init__(self, base=None):
        info = []
        # --------------------------------------
        # костыли для telegram
        if base is None:
            base = "private"
        # --------------------------------------

        used_currencies = BalanceInfo(base=base)._db_session.query(
            Orders.commission_currency.label('currency'),
            func.sum(Orders.lot_spent).label('total')).group_by(Orders.commission_currency).all()

        for row in used_currencies:
            if row.currency != "-":
                info.append(row.currency)

        for c_name in info:
            user_info = BalanceInfo(currency=c_name, base=base)
            setattr(self, c_name, user_info)

    def __iter__(self) -> BalanceInfo:
        for attr, value in self.__dict__.items():
            yield value

    def get(self, currency) -> BalanceInfo:
        try:
            return getattr(self, currency)
        except:
            return BalanceInfo("Empty")

    def get_info(self) -> list:
        info = []

        for curr in self:
            if curr.currency == '-':
                continue
            text = "%s:\nСредства в акциях\t%s\nСредства в ордерах\t%s\nСвободные средства\t%s\n\nВсего:\t\t%s\n\n" \
                   % (curr.currency, curr.money_in_stock, curr.money_in_orders, curr.free_money,
                      curr.all_money)
            info.append(text)
        return info
