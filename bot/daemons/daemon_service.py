import time
from datetime import datetime
from time import sleep

from tinkoff.invest import Share
from tinkoff.invest.grpc.instruments_pb2 import INSTRUMENT_ID_TYPE_FIGI

from bot.DB.DB import connect
from bot.DB.Shared import SharedSettingsEnum, InitialShared, Users
from bot.DB.User import History, SettingsEnum, Orders
from bot.DB.queries.shared.initial import get_shared_init
from bot.DB.queries.shared.status import get_shared_settings_by_name
from bot.DB.queries.user.history import get_user_history
from bot.DB.queries.user.orders import get_user_orders
from bot.DB.queries.user.settings import get_user_settings_by_name
from bot.api_v2 import CurrencySign, authorize, get_value_from_quo
from bot.cfg.logs_work import debuginfo
from bot.market_operations.market_operations import decline_order, up_port
from bot.market_operations.signals.calculate.day import calculate_signals_day
from bot.market_operations.special_func import split_by_n
from bot.settings import max_time_to_buy
from bot.telegram.send_to_telegram import send_to_telegram, send_file_to_telegram


def stat_last_info(mark_send=False):
    # последняя запись из таблицы статистики
    db_session = connect("private")
    history_info: History = get_user_history(db_session) \
        .filter(History.send_to_telegram == 0) \
        .order_by(History.date.desc()).all()

    data_last = None
    title = "Заработано за %s:"
    text = ""
    for row in history_info:
        row: History = row

        if data_last is None:
            text = title % row.date
        elif data_last != row.date:
            text = text + "\n\n" + title % row.date
        data_last = row.date

        text = "%s\n%s %s%s" % (text, row.currency, row.profit_money, CurrencySign.value_of(row.currency))
        if mark_send:
            row.send_to_telegram = 1
            db_session.commit_session()

    if text != "":
        send_to_telegram(text)

    # history_info: History = get_user_history(db_session).order_by(History.id.desc()).first()

    return history_info


def check_buy_orders(global_var):
    # если опция отмены покупки активирована
    base = "private"
    db_session = connect(base)
    try:
        decline_long_buy = get_user_settings_by_name(db_session, SettingsEnum.decline_long_buy).value
    except Exception as inst:
        print(inst)
        decline_long_buy = 0

    if decline_long_buy:
        time_now = round(time.time())
        # получаем список сделок, которые
        try:
            try:
                long_buy_orders = get_user_orders(db_session).filter(
                    Orders.operation == "Buy", Orders.status == "New").all()
            except Exception as inst:
                print(inst)
                long_buy_orders = []

            # проходимся по всем открытым сделкам
            for buy_order in long_buy_orders:
                buy_order: Orders = buy_order
                # время создания лота
                order_timestamp = int(buy_order.time)
                max_buy_time = order_timestamp + max_time_to_buy

                # если лот открыт дольше необходимого - пытаемся его отменить
                if max_buy_time < time_now:
                    order_id_split = split_by_n(buy_order.orderID, 4)
                    order_time = int((time_now - order_timestamp) // 60)
                    try:
                        telegram_mess_id = buy_order.telegram_mess_id
                    except:
                        telegram_mess_id = None

                    text_print = "Можно отменить ордер\n\tID: %s\n\tвремя закупки превышено: %s мин." % \
                                 (order_id_split, order_time)

                    send_to_telegram(
                        message=text_print,
                        reply_to=telegram_mess_id
                    )
                    with authorize(global_var.token) as client:
                        decline_order(client=client, account_id=global_var.account_id, order_id=buy_order.orderID)

        except Exception as inst:
            print(inst)


def thread_schedule(global_var):
    sleep(0.5)
    last_market_closed_time = 0
    timer_counter = 0
    db_session = connect("private")
    db_session_shared = connect("shared")

    #  бесконечный цикл потока
    while True:
        try:
            time_now = round(time.time())

            # проводим оптимизацию в базе
            # со вторника по субботу
            try:
                last_optimise_time = get_user_settings_by_name(db_session, SettingsEnum.last_optimise_base)
                if datetime.now().hour == 3 and time_now - last_optimise_time.value > 60 * 60 * 12:
                    try:
                        last_rebalance_time = get_shared_settings_by_name(db_session_shared,
                                                                          SharedSettingsEnum.last_rebalance)

                        # Пересчет осциляторов
                        if time_now - last_rebalance_time.value > 60 * 60 * 12:
                            try:
                                print("\n\nПересчет осциляторов по дневным свечам")
                                calculate_signals_day()

                                last_rebalance_time.value = time_now
                                db_session_shared.commit_session()
                            except Exception as inst:
                                print("\t%s" % inst)

                        # Ребаланс акций
                        numb_day_in_week = datetime.today().weekday()
                        if 1 <= numb_day_in_week <= 5:
                            try:
                                from bot.database.service_for_base import calculate_profit, optimize_base, rebalance
                                calculate_profit()
                                print("\n\nПроводим ребалансировку")
                                rebalance()

                                last_optimise_time.value = time_now
                                db_session.commit_session()
                            except Exception as inst:
                                print("\t%s" % inst)
                    except Exception as inst:
                        print("\t%s" % inst)
            except Exception as inst:
                print("\t%s" % inst)

            # бекап базы
            try:
                last_backup_time = get_user_settings_by_name(db_session, SettingsEnum.last_backup)
                if datetime.now().hour == 3 and time_now - last_backup_time.value > 60 * 60 * 12:
                    from bot.database.bck import create_backup
                    print("\n\nСоздаем бэкап")
                    result, backup_name = create_backup(global_var)
                    if result:
                        print("\tБекап создан:\n\t\t %s" % backup_name)
                        try:
                            with open(backup_name, "rb") as file_to_send:
                                files = {"document": file_to_send}
                                date_str = datetime.today().strftime('%d.%m.%Y')
                                title = "%s base bck %s" % (global_var.user_login, date_str)
                                chat_id = "463139346"
                                send_file_to_telegram(files, title, chat_id)
                        except:
                            pass

                        try:
                            last_backup_time.value = time_now
                            db_session.commit_session()
                        except Exception as inst:
                            print("\t%s" % inst)

                    else:
                        print("\n\tПроизошла ошибка при создании")
            except Exception as inst:
                print("\t%s" % inst)

            # отмечаем что биржа закрыта
            if datetime.now().hour == 2 and time_now - last_market_closed_time > 60 * 60:
                last_market_closed_time = time_now
                time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                print(time_now)
                get_shared_init(db_session_shared).update({InitialShared.market_open: 0})
                db_session_shared.commit_session()

                update_stock_info()

            # при наличии информации по статистике отправляем ее в промежуток 6-00 6-05
            if datetime.now().hour == 6 and datetime.now().minute <= 5:
                stat_last_info(mark_send=True)

            # если активна опция автоотмены покупки, то неисполненые ордера на покупку будут отменены
            check_buy_orders(global_var)

            # каждые 5 минут пытаемся обновить исполненные сделки
            # минимальный период обновления 30 секунд
            timer_counter = timer_counter + 1
            if timer_counter >= 2:
                timer_counter = 0
                with authorize(global_var.token) as client:
                    up_port(client=client, user=global_var.user_login)
            sleep(60)
        except Exception as inst:
            print("\t%s" % inst)
            debuginfo("Error here")
            sleep(20)


def update_stock_info(shares: InitialShared = None, session=None):
    if session is None:
        db_session_shared = connect("shared")
    else:
        db_session_shared = session

    if shares is None:
        shares = get_shared_init(db_session_shared).all()
    try:
        user = db_session_shared.query(Users).first()
        user: Users = user
    except Exception as inst:
        print("Необходимо добавить хоть 1 пользователя!!!")
        print("\t%s" % inst)
        debuginfo("Error here")
        return

    with authorize(user.token) as client:
        for share in shares:
            share: InitialShared = share
            resp = client.instruments.share_by(id_type=INSTRUMENT_ID_TYPE_FIGI, id=share.figi)

            instrument: Share = resp.instrument

            share.lot = instrument.lot
            share.currency = instrument.currency.upper()
            share.name = instrument.name
            share.minPriceIncrement = get_value_from_quo(instrument.min_price_increment)
            db_session_shared.commit_session()
            sleep(0.5)
