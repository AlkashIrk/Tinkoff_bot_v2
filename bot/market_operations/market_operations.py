import time
from datetime import timedelta
from pathlib import Path

from pytz import timezone
from tinkoff.invest import OrderDirection, OrderType

import bot.database.base_sqlite as base_sqlite
from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.User import SettingsEnum, Orders
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.user.initial import get_user_init_by_figi
from bot.DB.queries.user.orders import get_user_orders
from bot.DB.queries.user.settings import get_user_settings_by_name, set_user_settings_by_name
from bot.DB.queries.shared.user import get_user_by_name
from bot.api_v2 import get_value_from_quo, set_price_to_quo, get_status, round_price
from bot.cfg.logs_work import to_log, debuginfo
from bot.database.service.update_balance import db_upd_balance
from bot.market_operations.order_edit.edit import edit_order_v2
from bot.market_operations.special_func import *


# размещение нового ордера на бирже
from bot.telegram.send_to_telegram import send_to_telegram


def create_request(client, account_id: str, figi: str, lots: int, operation, order_price: float,
                   order_price_target=0, sell_order=None, base=None):
    create_logs = True

    db_session_shared = connect("shared")
    # получаем валюту акции
    share_info: InitialShared = get_shared_init(db_session_shared).filter(InitialShared.figi == figi).one()
    db_session_shared.close_session()

    min_incremen = share_info.minPriceIncrement

    if base is None:
        base = "private"

    account_id = str(account_id)

    if order_price_target == 0:
        order_price_target = order_price
    try:
        base_sqlite.command_adw(
            what="""CREATE TABLE orders(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                time REAL, 
                                figi TEXT,
                                orderId TEXT, 
                                operation TEXT,
                                price REAL,
                                target REAL,
                                status TEXT,
                                requestedLots INTEGER,
                                executedLots INTEGER,       
                                commission_currency TEXT, 
                                commission_value REAL)""",
            base=base
        )
    except:
        pass

    if operation == "Buy":
        direction = OrderDirection.ORDER_DIRECTION_BUY
    elif operation == "Sell":
        direction = OrderDirection.ORDER_DIRECTION_SELL
    else:
        return

    price_quo = set_price_to_quo(order_price)
    try:
        responses = client.orders.post_order(figi=figi, quantity=lots, price=price_quo,
                                             direction=direction,
                                             account_id=account_id, order_type=OrderType.ORDER_TYPE_LIMIT)
    except Exception as inst:
        print("\t%s" % inst)

        if inst.details == '30049':
            message = "\t Ошибка выставления заявки  - цена вне лимитов!"
            send_to_telegram(message=message)
            print(message)

            time.sleep(1)
            try:
                new_price = order_price_target - share_info.minPriceIncrement
                new_price = round_price(new_price, share_info.minPriceIncrement)
                price_quo = set_price_to_quo(new_price)
                responses = client.orders.post_order(figi=figi, quantity=lots, price=price_quo,
                                                     direction=direction,
                                                     account_id=account_id, order_type=OrderType.ORDER_TYPE_LIMIT)
            except Exception as inst:
                print("\t%s" % inst)
                return


    try:
        if create_logs:
            import scripts.globals as global_var
            global_var.init()
            time_now = datetime.now().strftime("%d-%m-%Y__%H_%M_%S")
            file_name = "logs/operations/%s/%s/%s/%s/orders/%s_%s.log" % \
                        (global_var.user_login, datetime.now().year, datetime.now().month, datetime.now().day, time_now,
                         responses.order_id)
            file_name_full = "logs/operations/%s/%s/%s/%s/orders/%s_%s_full.log" % \
                             (global_var.user_login, datetime.now().year, datetime.now().month, datetime.now().day,
                              time_now,
                              responses.order_id)
            file_path = Path(file_name)
            Path(file_path.parent).mkdir(parents=True, exist_ok=True)

            with open(file_name, "a+", encoding="utf-8") as full_log:
                print(responses, file=full_log)

            with open(file_name_full, "a+", encoding="utf-8") as full_log:
                print(responses, file=full_log)
    except Exception as inst:
        print("\t%s" % inst)

    try:
        order_id = responses.order_id
    except:
        order_id = -1

    # косяк тинька со сделками R
    try:
        import re
        pattern_market = r'^R'
        pattern_good = r'\d*$'

        if not re.match(pattern_good, order_id):
            if re.match(pattern_market, order_id):
                result = re.split(pattern_market, order_id)[1]
                if re.match(pattern_good, result):
                    order_id = result
                else:
                    print("bad id %s" % order_id)
            else:
                print("bad id %s" % order_id)

    except:
        pass

    if order_id != -1:
        if operation == "Sell":
            sell_order = order_id

        try:
            commission_currency = responses.executed_commission.currency
            commission_currency = str(commission_currency).upper()
        except:
            commission_currency = "-"

        try:
            commission_value = get_value_from_quo(responses.executed_commission)
        except:
            commission_value = 0

        order_time = round(time.time())

        try:
            data = (
                order_time, figi,
                order_id,
                operation,
                order_price, order_price_target,
                get_status(responses.execution_report_status),
                responses.lots_requested,
                responses.lots_executed,
                commission_currency,
                commission_value,
                sell_order,
            )
            data = [tuple(data)]
            base_sqlite.insert_data(
                table="orders("
                      "time, figi, orderId, "
                      "operation, price, target, status,"
                      "requestedLots, executedLots,"
                      "commission_currency, commission_value,"
                      "sell_order)",
                data=data,
                base=base
            )
        except:
            pass

    return order_id


# обновленние данных в локальной базе


# отмена ордера
def decline_order(client, account_id, order_id, operation=None, base=None):
    if base is None:
        base = "private"
    db_session = connect(base)

    try:
        order_info: Orders = get_user_orders(db_session).filter(Orders.orderID == order_id).one()
        figi = order_info.figi
        order_price = round(order_info.target, 2)
        order_lots = order_info.requestedLots
    except:
        debuginfo("Error here")
        return -1
    try:
        response = client.orders.cancel_order(account_id=str(account_id), order_id=str(order_id))
        print(response)
        try:
            order_info.status = "Decline"
            db_session.commit_session()

            try:
                select_ticker = get_user_init_by_figi(db_session, figi)
                ticker = select_ticker.ticker

                if operation == "Buy":
                    select_ticker.buy = select_ticker.buy + order_lots
                    db_session.commit_session()

            except:
                debuginfo("Error here")
                ticker = figi

            text_print = "Declined buy\n\t%s (id=%s)\n\tprice: %s$\n" \
                         % (ticker, order_id, order_price)
            to_log("\t" + text_print, "logs/%s_orders.log" % ticker, True)
            return True
        except:
            debuginfo("Error here")
    except Exception as er:
        print(er)
        debuginfo("Error here")
        print("Order %s (id=%s) allready declined\n\tprice: %s$\n\tcount: %s"
              % (figi, order_id, order_price, order_lots))
        return -1


# выгрузка данных в файл
def operation_to_file(operations):
    to_file = "ID\tDate\tTime\tType\tCode\tCount\tPrice\tTotal\tCommision\tCurrency\tStatus\n"
    for element in operations:
        op_id = element._id

        op_date = element._date

        try:
            op_time = str(op_date.hour) + ":" + str(op_date.minute) + ":" + str(op_date.second)
        except:
            op_time = ""

        try:
            op_date = str(op_date.day) + ";" + str(op_date.month) + ";" + str(op_date.year)
        except:
            op_date = ""

        try:
            op_code = str(element._figi)
        except:
            op_code = ""

        op_type = element._operation_type

        try:
            op_payment = str(element._payment)
        except:
            op_payment = ""

        try:
            op_price_per = str(element._price)
        except:
            op_price_per = ""

        try:
            op_count = str(element._quantity)
        except:
            op_count = ""

        try:
            op_commission = str(element._commission._value)
        except:
            op_commission = ""

        try:
            op_status = str(element._status)
        except:
            op_status = ""

        try:
            op_curr = str(element._currency)
        except:
            op_curr = ""

        data = op_id + "\t" + str(op_date) + "\t" + str(op_time) + "\t" + \
               op_type + "\t" + op_code + "\t" + \
               str(op_count) + "\t" + str(op_price_per) + "\t" + str(op_payment) + "\t" + str(op_commission) + "\t" + \
               op_curr + "\t" + op_status + "\n"

        to_file = to_file + data

    to_file = to_file.replace(".", ",")
    to_file = to_file.replace("None", "")
    to_file = to_file.replace(";", ".")

    # current date and time
    now = datetime.now()
    file_name = now.strftime("%Y_%m_%d__%H_%M_%S")

    with open("%s.txt" % file_name, "a", encoding="utf-8") as myfile:
        myfile.write(to_file)


def update_balance(client, account_id):
    """
    запрос баланса и дальнейшее обновление в локальной базе
    """
    info = client.operations.get_withdraw_limits(account_id=account_id)

    balance_list = {}
    if info.money:
        for curr in info.money:
            curr_name = curr.currency.upper()
            balance_list.update(
                {
                    curr_name: {'balance': get_value_from_quo(curr), 'blocked': 0}
                })

    if info.blocked:
        for curr in info.blocked:
            curr_name = curr.currency.upper()
            value = balance_list.get(curr_name)
            value.update({'blocked': get_value_from_quo(curr)})

    if len(balance_list) != 0:
        # обновление баланса в локальной базе
        db_upd_balance(balance_list)


# обновление локальной базы
#   исполненные сделки
def update_portfolio(client, to_file=False, user=None, days_delta=None):
    if user is None:
        user = "_"
    if days_delta is None:
        days_delta = 1

    # стоимость лота с учетом комиссии
    base_sqlite.check_column(base="private", table="orders",
                             column="lot_spent", column_type="integer", default_value=0)

    # db_session = connect("private")
    # try:
    #     min_profit = get_user_settings_by_name(db_session, SettingsEnum.min_profit).value
    # except Exception as inst:
    #     debuginfo("Error here")
    #     print("\t%s" % inst)
    #     min_profit = def_minimal_profit

    print("\tUpdate portfolio for: %s" % user)
    db_session_shared = connect("shared")
    user_info = get_user_by_name(db_session_shared, user)
    account_id = str(user_info.account_id)

    update_balance(client, account_id=account_id)

    time_today = datetime.now()
    year_today = time_today.year
    month_today = time_today.month
    day_today = time_today.day

    d1 = datetime(year_today, month_today, day_today, 0, 0, 0, tzinfo=timezone("Europe/Moscow"))
    d1 = d1 - timedelta(days=days_delta)

    # timezone нужно указывать. Иначе - ошибка
    d2 = datetime.now(tz=timezone("Europe/Moscow"))
    # По настоящее время

    ops = client.operations.get_operations(account_id=account_id, from_=d1, to=d2)

    try:
        ops_list = ops.operations
    except:
        ops_list = []

    create_logs = True

    if create_logs:
        time_now = datetime.now().strftime("%d-%m-%Y__%H_%M_%S")
        if user is not None:
            file_name = "logs/operations/%s/%s/%s/%s/log_%s.log" % \
                        (user, datetime.now().year, datetime.now().month, datetime.now().day, time_now)
        else:
            file_name = "logs/operations/%s/%s/%s/log_%s.log" % \
                        (datetime.now().year, datetime.now().month, datetime.now().day, time_now)
        file_path = Path(file_name)
        Path(file_path.parent).mkdir(parents=True, exist_ok=True)

        with open(file_name, "a+", encoding="utf-8") as full_log:
            print(ops_list, file=full_log)

    if len(ops_list) != 0:
        if not to_file:
            try:
                for order in ops_list:
                    edit_order_v2(order)
            except:
                pass
        else:
            operation_to_file(ops.payload.operations)


def up_port(client, user: str):
    time_now = round(time.time())
    db_session = connect("private")
    try:
        last_update_portfolio = get_user_settings_by_name(db_session, SettingsEnum.last_update_portfolio).value
    except Exception as inst:
        print("\t%s" % inst)
        last_update_portfolio = 0
    if time_now - last_update_portfolio > 30:
        try:
            update_portfolio(client=client, user=user)
            try:
                set_user_settings_by_name(db_session, SettingsEnum.last_update_portfolio, time_now)
            except Exception as inst:
                print("\t%s" % inst)
        except Exception as inst:
            print("\t\tFail: update portfolio")
            print("\t%s" % inst)
