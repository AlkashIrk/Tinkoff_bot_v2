from enum import Enum


class InstrumentSignals(str, Enum):
    RSI = 'RSI'
    STOCH = 'STOCH'
    UO = 'UO'
    Keltner = 'Keltner'
    candels = 'candels'


class Signal:
    def __init__(self, name: str, last_value: float, previous_value: float):
        self._name = name
        self.last_value = last_value
        self.previous_value = previous_value
        self.sell = 0
        self.buy = 0
        self.message = ""

    def __repr__(self):
        if self.previous_value == self.last_value == -1:
            return f'{self._name} empty'
        else:
            return f'{self._name} {self.previous_value} -> {self.last_value}'

    def default_message(self):
        self.message = "\n\t\t\t\t%.2f -> %.2f" % (self.previous_value, self.last_value)


class Signals:
    def __init__(self, instriment_name):
        self.instriment_name = instriment_name
        self._test()

    def append(self, signal: Signal):
        setattr(self, signal._name, signal)

    def _test(self):
        for sign in InstrumentSignals:
            sign_def = Signal(name=sign, last_value=-1, previous_value=-1)
            setattr(self, sign_def._name, sign_def)
