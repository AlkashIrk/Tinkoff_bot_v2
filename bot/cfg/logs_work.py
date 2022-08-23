import datetime
import sys
import time
import traceback
from inspect import getframeinfo, stack
from pathlib import Path


def to_log(text_to_log, file_name, time_to_log=False, print_to_console=True):
    ts = time.time()
    year_st = datetime.datetime.fromtimestamp(ts).strftime("%Y")
    month_st = datetime.datetime.fromtimestamp(ts).strftime("%m")
    day_st = datetime.datetime.fromtimestamp(ts).strftime("%d")

    file_path = Path(file_name)
    path_base_d = sys.path[0] + ("/%s/%s/%s" % (file_path.parent, year_st, month_st))
    file_name = path_base_d + ("/%s_%s" % (day_st, file_path.name))

    Path(path_base_d).mkdir(parents=True, exist_ok=True)

    if time_to_log:
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        if print_to_console:
            print(st + " " + text_to_log)
        write_to_file(st + " " + text_to_log, file_name)
    else:
        if print_to_console:
            print(text_to_log)
        write_to_file(text_to_log, file_name)


def write_to_file(text, file_name):
    f = open(file_name, "a+", encoding="utf-8")
    if str(type(text)).find("list") != -1:
        for list_text in text:
            f.write(str(list_text))
    else:
        if text.find("\n") != -1 or text.find("\r") != -1:
            f.write(str(text))
        else:
            f.write(str(text) + "\n")
    f.close()


def debuginfo(message):
    print(traceback.format_exc())
    caller = getframeinfo(stack()[1][0])
    print("\t%s:%d - %s" % (caller.filename, caller.lineno, message))
