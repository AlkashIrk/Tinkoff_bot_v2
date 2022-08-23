from bot.DB.DB import connect
from bot.DB.queries.shared.oscillator import get_by_figi


class DayParams:
    def __init__(self, figi: str):
        db_session = connect("shared")
        self.db = get_by_figi(db_session, figi)
        self.max_price = self.db.price_max
        self.may_buy = 0
        self.calculate()

    def calculate(self):
        try:
            if float(self.db.sig_stoch) < 75:
                self.may_buy += 1
        except Exception as inst:
            print("\t%s" % inst)

        try:
            if float(self.db.sig_RSI) < 70:
                self.may_buy += 1
        except Exception as inst:
            print("\t%s" % inst)

        try:
            if float(self.db.sig_UO) < 70:
                self.may_buy += 1
        except Exception as inst:
            print("\t%s" % inst)