# Refactored
import os
from datetime import datetime
from time import sleep

from bot.DB.DB import connect
from bot.DB.Shared import InitialShared
from bot.DB.queries.shared.initial import get_shared_init
from bot.cfg.logs_work import debuginfo
from bot.database import base_sqlite
from bot.market_operations.signals.signals import calculate_signals_new
from bot.settings import daemon_signals_sleep, threads_count

debug_mode = False


def daemon_check_signals():
    """
    проверка сигналов из базы
    """

    data_of_candles = {}
    os.system("cls")
    print("Threads = %s" % threads_count)
    print("Sleep time = %s" % daemon_signals_sleep)

    column_tick_exist = base_sqlite.check_column(base="shared", table="initial",
                                                 column="tick", column_type="integer", default_value=0)
    # if column_tick_exist:
    #     base_sqlite.command_adw(what="UPDATE initial set tick=0", base="shared")

    while True:
        try:
            db_session_shared = connect("shared")
            orders_active = get_shared_init(db_session_shared).filter(
                InitialShared.tick != 0).all()

            for elements in orders_active:
                elements: InitialShared = elements
                table_name = elements.figi
                table_records = elements.tick
                try:
                    old_value = data_of_candles[table_name]["old_value"]
                except:
                    old_value = table_records

                data_of_candles[table_name] = {"new_value": table_records, "old_value": old_value}

            updated = []
            for elements in data_of_candles:
                new_value = data_of_candles[elements]["new_value"]
                old_value = data_of_candles[elements]["old_value"]

                if new_value != old_value:
                    updated.append(elements)
                    data_of_candles[elements]["old_value"] = new_value
        except:
            updated = []

        # if debug_mode:
        #     updated = ['BBG000BL9C59', 'BBG004730RP0', 'BBG000BTR593', 'BBG000C8H633']

        if len(updated) >= 1:
            now = datetime.now()
            date_time = now.strftime("%d.%m.%Y %H:%M:%S")
            os.system("title SIGNALS %s" % date_time)
            try:
                # подсчет осциляторов
                calculate_signals_new(args=updated)

                if 3 < datetime.now().hour <= 6:
                    sleep(daemon_signals_sleep * 10)
                else:
                    sleep(daemon_signals_sleep)

            except Exception as inst:
                debuginfo("Error here")
                print("\t%s" % inst)
                sleep(60)
        else:
            sleep(daemon_signals_sleep)
