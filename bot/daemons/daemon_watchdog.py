# Refactored
import time
from datetime import datetime

from bot.DB.DB import connect
from bot.DB.Shared import SharedSettingsEnum
from bot.DB.queries.shared.initial import get_ticks_in_DB
from bot.DB.queries.shared.status import set_shared_settings_by_name, get_shared_settings_by_name
from bot.market_operations.special_func import check_candeles_time
# задержка перед стартом / интервал проверки в минутах
from bot.settings import watchdog_delay, watchdog_interval


def watchdog():
    import os
    import signal
    os.system("cls")
    time.sleep(watchdog_delay)

    while True:
        now = datetime.now()
        date_time = now.strftime("%d.%m.%Y %H:%M:%S")
        os.system("title WATCHDOG last check: %s" % date_time)

        time_now = round(time.time())

        db_session_shared = connect("shared")
        full_data = get_ticks_in_DB(db_session_shared)
        last_data = get_shared_settings_by_name(db_session_shared, SharedSettingsEnum.last_value).value

        if check_candeles_time():
            import platform

            print("%s\n\tcheck now:\t%s\n\tcheck last:\t%s" % (date_time, full_data, last_data))

            if full_data == last_data:
                try:
                    pid = get_shared_settings_by_name(db_session_shared, SharedSettingsEnum.pid).value
                    os.kill(pid, signal.SIGTERM)
                except:
                    pass

                set_shared_settings_by_name(db_session_shared, SharedSettingsEnum.last_restart, time_now)

                if platform.system() == "Windows":
                    filepath = "_daemon_candels.bat"
                    os.system("start cmd /c start /min %s" % filepath)
                elif platform.system() == "Linux":
                    import subprocess
                    # TODO захардкожен путь
                    filepath = "/home/alkash/tinkoff/sh/candels.sh"
                    subprocess.call(['sh', filepath])

        # обновляем значения в БД
        set_shared_settings_by_name(db_session_shared, SharedSettingsEnum.last_check, time_now)
        set_shared_settings_by_name(db_session_shared, SharedSettingsEnum.last_value, full_data)

        time.sleep(60 * watchdog_interval)
