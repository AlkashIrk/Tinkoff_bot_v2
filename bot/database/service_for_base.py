import time
from datetime import timedelta

from sqlalchemy import func

import scripts.globals as global_var
from bot.DB.DB import connect
from bot.DB.Shared import InitialShared, OscillatorDay
from bot.DB.User import Orders, SettingsEnum, InitialUser, History
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.user.initial import get_user_init, get_curr_list
from bot.DB.queries.user.orders import get_user_orders, stocks_in_deposit, stocks_in_orders
from bot.DB.queries.user.settings import get_user_settings_by_name
from bot.api_v2 import authorize, CurrencySign
from bot.database import base_sqlite
from bot.database.stat_info import money_profit
from bot.market_operations.special_func import *
from bot.model.BalanceInfo import BalanceInfo, UserBalance

global_var.init()
sandbox_token = global_var.sandbox_token


def rebalance(base=None):
    """
    Ребалинсировка акций!!!
    нужно продумать механизм
    """

    if base is None:
        base = "private"

    db_session = connect(base)
    db_session_shared = connect("shared")

    c_info = db_session_shared.query(InitialShared.ticker, InitialShared.lot, OscillatorDay.MA).filter(
        OscillatorDay.ticker == InitialShared.ticker).all()

    share_info = {}
    for row in c_info:
        share_info.update({row.ticker: row})

    try:
        money_koeff = get_user_settings_by_name(db_session, SettingsEnum.rebalance_stock_koeff).value
    except:
        money_koeff = 1.5

    if money_koeff > 2:
        money_koeff = 1.5

    if money_koeff < 0.1:
        money_koeff = 1.5

    # подсчет количества акций в портфеле

    # акции в сделках
    stocks_count = {}
    stocks_in_sell = stocks_in_orders(db_session).all()
    for order in stocks_in_sell:
        stocks_count[order.ticker] = order.total
        del order

    # итоговый подсчет количества акций в портфеле
    stocks_buy = stocks_in_deposit(db_session).all()
    for stocks in stocks_buy:
        try:
            stocks_in = stocks_count[stocks.ticker]
        except:
            stocks_in = 0

        stocks_count[stocks.ticker] = stocks.total + stocks_in
        del stocks
    del stocks_buy
    del stocks_in_sell

    info_a, info_c = get_curr_list(db_session)
    currencies = list(info_a.keys())

    info = {}
    for c in currencies:
        info.update({c: BalanceInfo(c)})

    """
    Уточним среднюю стоймость за 7 дней
    перебераем FIGI всех акций из базы 
    """
    shares_autobalance = get_user_init(db_session).filter(InitialUser.autobalance == 1,
                                                          InitialUser.enable_buy == 1).all()

    output_text = []
    for company in shares_autobalance:
        company: InitialUser = company

        try:
            full_money = info.get(info_c.get(company.ticker))
            if full_money is None:
                print("full_money is None")
                print("Error rebalance")
                continue
        except Exception as inst:
            print("\t%s" % inst)
            print("Error rebalance")
            continue

        try:
            # средняя цена акции
            aver_price = share_info.get(company.ticker).MA

            # виртуальный объем средств
            portfolio_virt_money = full_money.all_money * money_koeff
            # число акций торгуемых этой валютой
            shares_count = info_a.get(info_c.get(company.ticker)).get("enable")

            # максимальное число акций который можно купить учитывая все коэффициенты
            max_shares = (portfolio_virt_money / shares_count) // aver_price

            # максимальное число лотов к покупке
            max_lots = int(round(max_shares // share_info.get(company.ticker).lot, 0))

            company.max_stock = max_lots

            try:
                stock_in_port = stocks_count.get(company.ticker)
                if stock_in_port is None:
                    stock_in_port = 0
            except:
                stock_in_port = 0

            try:
                delta = company.max_stock - stock_in_port
            except:
                delta = 0

            text = "Акция %s\n\tплан %s\n\tпортфель %s\n\tможно докупить %s\n\tпредыдущее значение %s" \
                   % (company.ticker, company.max_stock, stock_in_port, delta, company.buy)
            output_text.append(text)
            print(text)
            print("\tAverage price for %s - %s" % (company.ticker, aver_price))

            company.buy = delta
            company.stock_in_portfel = stock_in_port
            db_session.commit_session()




        except Exception as inst:
            print("\t%s" % inst)
            print("\tError %s" % (company.ticker))
            pass
        # del response
    print("\n")

    try:
        del full_money
        del money_koeff
        del shares_autobalance
    except:
        pass

    return output_text


def optimize_base():
    time_now = round(time.time())
    try:
        last_optimise_time = base_sqlite.select_adw(
            what="value",
            table="status",
            expression="where name='last_optimise'",
            base="shared"
        )[0][0]
    except Exception as inst:
        print("\t%s" % inst)
        last_optimise_time = 0

    # print("Last optimise %s" % last_optimise_time)
    if time_now - last_optimise_time > 60 * 60 * 12:
        last_optimise_time = time_now
        try:
            base_sqlite.command_adw(
                what="UPDATE status set value=%s where name='last_optimise'" % last_optimise_time,
                base="shared"
            )
        except Exception as inst:
            print("\t%s" % inst)

        orders_active = base_sqlite.select_adw(
            what="figi, ticker",
            table="initial",
            expression="",
            base="shared")

        for figi in orders_active:
            table_from_base = figi[0]
            base_sqlite.command_adw(
                what="delete from %s where id NOT IN "
                     "(select max(id) as id from %s group by time)"
                     % (table_from_base, table_from_base),
                base="shared"
            )

        base_sqlite.command_adw(
            what="VACUUM",
            base="shared"
        )


def calculate_profit(update_base=True):
    """
    Подсчет прибыльности по итогам дня
    """

    # обновляем данные по частично выполненным заявкам
    # заявки на покупку
    db_session = connect("private")
    try:
        buy_orders = get_user_orders(db_session).filter(Orders.status == "Done", Orders.operation == "Buy",
                                                        Orders.money_spent == None).all()
        for element in buy_orders:
            element: Orders = element
            try:
                element.money_spent = round(element.executedLots * element.price, 2)
            except:
                pass

        buy_orders = get_user_orders(db_session).filter(Orders.status == "Done", Orders.operation == "Buy",
                                                        Orders.lot_spent == 0).all()
        for element in buy_orders:
            element: Orders = element
            try:
                element.lot_spent = round(element.money_spent + abs(element.commission_value), 2)
            except:
                pass
        db_session.commit_session()
    except:
        pass

    # заявки на продажу
    # expression="requested_lots <> executed_lots and status="Done" and operation="Sell"",
    try:
        sell_orders = get_user_orders(db_session).filter(Orders.status == "Done", Orders.operation == "Sell").all()
        for element in sell_orders:
            element: Orders = element

            if element.money_spent is None:
                money_spent = db_session.query(func.sum(Orders.lot_spent).label('total')).filter(
                    Orders.sell_order == element.orderID).one()
                element.money_spent = money_spent.total

            try:
                element.lot_spent = round(element.money_spent * element.executedLots / element.requestedLots
                                          + abs(element.commission_value), 2)
            except:
                pass
        db_session.commit_session()
    except:
        pass

    info = UserBalance()
    info_message = info.get_info()
    for text in info_message:
        print(text)

    """
    Импортируем данные в таблицу
    """
    if update_base:
        # получаем текущую дату
        if datetime.now().hour <= 5:
            date_select = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
        else:
            date_select = (datetime.now()).strftime("%d.%m.%Y")

        profit_money = money_profit(0, 0)
        data = []
        for currency in profit_money:
            value = profit_money.get(currency)

            data_app = info.get(currency)

            profit_percent = round(
                100 * value /
                (data_app.money_in_stock + data_app.money_in_orders + data_app.free_money), 2)

            row = History(date=date_select,
                          money_in_stock=data_app.money_in_stock,
                          money_in_orders=data_app.money_in_orders,
                          free_money=data_app.free_money,
                          profit_money=value,
                          profit_percent=profit_percent,
                          currency=currency
                          )
            data.append(row)

        db_session.add_all(data)
        db_session.commit_session()


def sort_by_target(elem):
    return elem[1]


def stock_info(ticker: str = None, action: str = "message", base_name=None):
    if base_name is None:
        base_name = "private"

    if ticker is None:
        left_join = "left join initial on initial.figi = orders.figi"
        sql = "where orders.status='Done' and sell_order is NULL and orders.operation='Buy' order by ticker"

        stocks_in_portf = base_sqlite.select_adw(
            what="initial.ticker, price, target, executedLots, money_spent",
            table="orders",
            expression="%s %s" % (left_join, sql),
            base=base_name
        )

        del sql
        del left_join
    else:
        left_join = "left join initial on initial.figi = orders.figi"
        sql = "where initial.ticker='%s' and orders.status='Done' " \
              "and sell_order is NULL and orders.operation='Buy' order by ticker" % ticker

        stocks_in_portf = base_sqlite.select_adw(
            what="initial.ticker, price, target, executedLots, money_spent",
            table="orders",
            expression="%s %s" % (left_join, sql),
            base=base_name
        )

        del sql
        del left_join

    stock_sort = {}
    for stock_position in stocks_in_portf:
        stock_ticker = stock_position[0]
        if stock_ticker is None:
            continue
        price_buy = round(stock_position[1], 2)
        price_target_sell = round(stock_position[2], 2)
        lot_count = int(stock_position[3])
        try:
            money_spent = round(stock_position[4], 2)
        except:
            money_spent = price_buy * lot_count

        try:
            data = stock_sort[stock_ticker]
        except:
            data = []

        info = [price_buy, price_target_sell, lot_count, money_spent]
        data.append(info)
        del info

        stock_sort[stock_ticker] = data

        del money_spent
        del lot_count
        del price_target_sell
        del price_buy
        del stock_ticker
        del stock_position
        del data
    del stocks_in_portf

    for elem in stock_sort:
        stock_sort[elem].sort(key=sort_by_target)

    if action == "dict":
        return stock_sort

    message_list = []
    if action == "message":
        for elem in stock_sort:
            # получаем валюту акции
            db_session_shared = connect("shared")
            share_info: InitialShared = get_shared_init(db_session_shared).filter(
                InitialShared.ticker == elem).one()
            currency_order = share_info.currency
            currency_sign = CurrencySign.value_of(currency_order)
            db_session_shared.close_session()

            last_price = share_info.last_price
            text = '<a href="https://www.tinkoff.ru/invest/stocks/%s/">Акция %s (%.2f%s)</a>:\n' \
                   % (elem, elem, last_price, currency_sign)

            text = "[Акция %s (%.2f%s)](https://www.tinkoff.ru/invest/stocks/%s/): " \
                   % (elem, last_price, currency_sign, elem)
            total_lots = 0
            total_spent = 0
            text += "``` \n"
            for order in stock_sort[elem]:
                total_lots += order[2]
                total_spent += order[3]

                lot_in_order = "{:>3}".format(order[2])

                text += " %s шт. за %.2f цель %.2f\n" % (lot_in_order, order[0], order[1])

            total_spent = round(total_spent, 2)
            text += "\nИтого: %s%s (%s шт.)" % (total_spent, currency_sign, total_lots)
            text += " ```"
            message_list.append(text)
    return message_list


def stock_in_order_info(ticker: str = None, action: str = "message", base_name=None):
    if base_name is None:
        base_name = "private"

    if ticker is None:
        left_join = "left join initial on initial.figi = orders.figi"
        sql = "where orders.status='New' order by ticker"

        stocks_in_portf = base_sqlite.select_adw(
            what="initial.ticker, price, requestedLots, money_spent, orderId, orders.operation",
            table="orders",
            expression="%s %s" % (left_join, sql),
            base=base_name
        )

        del sql
        del left_join
    else:
        left_join = "left join initial on initial.figi = orders.figi"
        sql = "where initial.ticker='%s' and orders.status='New' " \
              "order by ticker" % ticker

        stocks_in_portf = base_sqlite.select_adw(
            what="initial.ticker, price, requestedLots, money_spent, orderId, orders.operation",
            table="orders",
            expression="%s %s" % (left_join, sql),
            base=base_name
        )

        del sql
        del left_join

    stock_sort = {}
    for stock_position in stocks_in_portf:
        stock_ticker = stock_position[0]
        price_buy = round(stock_position[1], 2)
        lot_count = int(stock_position[2])
        operation = stock_position[5]

        if operation == "Sell":
            money_spent = round(stock_position[3], 2)
        else:
            money_spent = round(price_buy * lot_count, 2)
        order_id = stock_position[4]

        try:
            data = stock_sort[stock_ticker]
        except:
            data = []

        info = {
            "id": order_id,
            "lots": lot_count,
            "price": price_buy,
            "money_spent": money_spent,
            "operation": operation
        }
        data.append(info)
        del info

        stock_sort[stock_ticker] = data

        del money_spent
        del lot_count
        del order_id
        del price_buy
        del stock_ticker
        del stock_position
        del data
        del operation
    del stocks_in_portf

    if action == "dict":
        return stock_sort
    # last_candle_price = last_candle_info(action="only_last_price")
    message_list = []
    if action == "message":
        for elem in stock_sort:
            # получаем валюту акции
            db_session_shared = connect("shared")
            share_info: InitialShared = get_shared_init(db_session_shared).filter(
                InitialShared.figi == elem).one()
            currency_order = share_info.currency
            currency_sign = CurrencySign.value_of(currency_order)
            db_session_shared.close_session()

            text = "[Акция %s](https://www.tinkoff.ru/invest/stocks/%s/): " \
                   % (elem, elem)
            total_lots = 0
            total_spent = 0
            text += "``` \n"
            for order in stock_sort[elem]:
                total_lots += order[2]
                total_spent += order[3]

                lot_in_order = "{:>3}".format(order[2])

                text += " %s шт. за %.2f цель %.2f\n" % (lot_in_order, order[0], order[1])

            total_spent = round(total_spent, 2)
            text += "\nИтого: %s%s (%s шт.)" % (total_spent, total_lots, currency_sign)
            text += " ```"
            message_list.append(text)
    return message_list


def last_candle_info(ticker: str = None, action: str = "dict", base=None):
    if base is None:
        base = "private"

    stocks_list = []
    if ticker is None:
        db_session = connect(base)

        try:
            stocks_list = db_session.query(Orders.figi, InitialUser.ticker). \
                join(InitialUser, InitialUser.figi == Orders.figi). \
                filter(Orders.sell_order == None, Orders.operation == "Buy", Orders.status == "Done"). \
                group_by(Orders.figi).order_by(InitialUser.ticker).all()
        except Exception as ex:
            print(ex)
        db_session.close_session()
    del ticker

    # TODO сделать через 1 запрос к БД
    stock_last_price = {}
    db_session_shared = connect("shared")

    for company in stocks_list:
        company_figi = company.figi
        company_name = company.ticker

        try:
            row_data: InitialShared = get_shared_init(db_session_shared).filter(
                InitialShared.figi == company_figi).one()
            try:
                stock_last_price[company_name] = row_data
            except:
                pass
        except Exception as inst:
            print("\t%s" % inst)

        del company_figi
        del company_name
        del company
    db_session_shared.close_session()

    if action == "only_last_price":
        return stock_last_price

    stock_in = stock_info(action="dict", base_name=base)

    lots_to_sell = {}
    for company in stock_in:
        # если акция не добавлена в список купли \ продажи, то идем по списку дальше
        if company is None:
            continue
        lots = 0
        money_spent = 0
        share_info: InitialShared = stock_last_price[company]

        for order in stock_in[company]:
            if order[1] <= share_info.last_price:
                lots += order[2]
                money_spent += order[3]
            del order

        profit = lots * share_info.last_price * share_info.lot - money_spent

        if profit > 0:
            commission = (lots * share_info.last_price) * (0.025 / 100)
            profit = round(profit - commission, 2)
        else:
            profit = round(profit, 2)

        lots_to_sell[company] = {"lots": lots, "profit": profit, "object": share_info}
        del company
        del lots
    return lots_to_sell


def try_decline_order(sell_order, base=None, user_id=None):
    user_id: InitialUser = user_id

    if base is None:
        base = "private"

    if user_id is None:
        return

    operation = None
    try:
        sql = "where orderId='%s'" % sell_order
        select_from_orders = base_sqlite.select_adw(
            what="operation, telegram_mess_id",
            table="orders",
            expression="%s" % sql,
            base=base
        )[0]
        operation = select_from_orders[0]
        mess_id = select_from_orders[1]
    except:
        pass

    if operation == "Buy":
        from bot.market_operations.market_operations import decline_order

        with authorize(user_id.token) as client:
            result = decline_order(
                client=client,
                order_id=sell_order,
                operation=operation,
                account_id=user_id.account_id
            )
        if result:
            base_sqlite.command_adw(
                what="update orders set retry=1 where orderId=%s" % sell_order,
                base=base
            )
            return True, {"status": "ok", "telegram_mess_id": mess_id, "operation": operation}
        else:
            return False, {"status": "error"}

    if operation == "Sell":
        left_join = "left join initial on initial.figi = orders.figi"
        sql = "where sell_order='%s' and orders.status='Done' and orders.operation='Buy' " \
              "order by ticker" % sell_order

        stocks_in_portf = base_sqlite.select_adw(
            what="initial.ticker, price, requestedLots, money_spent, orderId",
            table="orders",
            expression="%s %s" % (left_join, sql),
            base=base
        )

        if len(stocks_in_portf) != 0:
            from bot.market_operations.market_operations import decline_order
            # base_sqlite.command_adw("update orders set executedLots=0, target=NULL where orderId=%s" % sell_order)

            with authorize(user_id.token) as client:
                result = decline_order(
                    client=client,
                    order_id=sell_order,
                    operation=operation,
                    base=base,
                    account_id=user_id.account_id
                )
            if result:
                base_sqlite.command_adw(
                    what="update orders set retry=1 where orderId=%s" % sell_order,
                    base=base
                )
                for order in stocks_in_portf:
                    order_id = order[4]
                    base_sqlite.command_adw(
                        what="update orders set sell_order=NULL where orderId=%s" % order_id,
                        base=base
                    )
                return True, {"status": "ok", "telegram_mess_id": mess_id, "operation": operation}
        else:
            return False, {"status": "error"}
