import os
import sqlite3
import threading
from os import path
from pathlib import Path

import scripts.globals as global_var

lock = threading.Lock()
pause_period = 0.01


def connect_to_base(base):
    if base == "shared":
        base_name = global_var.base_name
    elif base == "private":
        base_name = global_var.base_name_private
    else:
        base_name = base

    if not path.exists(base_name):
        Path(os.path.dirname(base_name)).mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(base_name, check_same_thread=False, timeout=1)
        c = conn.cursor()
        """
        try:
            lock.acquire(True)
            c.execute('''CREATE TABLE initial
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,        
                        figi TEXT,
                        ticker TEXT              
                        )''')
            conn.commit()
        finally:
            lock.release()
        """
    else:
        # print("Base %s exist" % base_name)
        conn = sqlite3.connect(base_name, check_same_thread=False, timeout=1)
        c = conn.cursor()
    return c, conn


def insert_data(table, data, base):
    global pause_period

    operation_done = False
    while not operation_done:
        c, conn = connect_to_base(base)
        try:
            lock.acquire(True)
            val_count = table.count(",")
            val_count = val_count + 1
            if val_count > 1:
                expression = "?," * val_count
                expression = expression[:-1]
            else:
                expression = "?"
            expression = "(" + expression + ")"
            sql = "INSERT INTO {table} VALUES {ex}"
            sql = sql.format(table=table, ex=expression)
            c.executemany(sql, data)
            conn.commit()
            operation_done = True

        except Exception as inst:
            print("\t%s" % inst)
            if inst.args[0] == "database is locked":
                from time import sleep
                sleep(pause_period)
            else:
                operation_done = True
        finally:
            lock.release()
        conn.close()


def update_data(table, expression, data, base):
    global pause_period

    operation_done = False
    while not operation_done:
        c, conn = connect_to_base(base)
        try:
            lock.acquire(True)
            sql = "UPDATE {table} {ex}"
            sql = sql.format(table=table, ex=expression)
            c.executemany(sql, data)
            conn.commit()
            operation_done = True

        except Exception as inst:
            print("\t%s" % inst)
            if inst.args[0] == "database is locked":
                from time import sleep
                sleep(pause_period)
            else:
                operation_done = True
        finally:
            lock.release()
        conn.close()


def select(what, table, base, expression="", data=None):
    data_str = ""
    operation_done = False
    while not operation_done:
        try:
            c, conn = connect_to_base(base)
            if expression != "":
                sql = "SELECT {what} FROM {table} WHERE {ex}"
                sql = sql.format(what=what, table=table, ex=expression)
            else:
                sql = "SELECT {what} FROM {table}"
                sql = sql.format(what=what, table=table)
            if data is None:
                c.execute(sql)
            else:
                c.execute(sql, data)
            data_str = c.fetchall()
            conn.close()
            operation_done = True
        except Exception as inst:
            if inst.args[0] == "database is locked":
                from time import sleep
                print("database is locked")
                sleep(pause_period)
            else:
                operation_done = True
    return data_str


def select_adw(what, table, expression, base):
    c, conn = connect_to_base(base)
    try:
        lock.acquire(True)
        sql = "SELECT {what} FROM {table} {ex}"
        sql = sql.format(what=what, table=table, ex=expression)
        c.execute(sql)
        data_str = c.fetchall()
    finally:
        lock.release()
    conn.close()
    return data_str


def command_adw(what, base, print_error=True, data=None):
    global pause_period

    operation_done = False
    while not operation_done:
        c, conn = connect_to_base(base)
        try:
            lock.acquire(True)
            if data is None:
                c.execute(what)
            else:
                c.execute(what, data)
            conn.commit()
            operation_done = True

        except Exception as inst:
            if print_error:
                print("\t%s" % inst)
            if inst.args[0] == "database is locked":
                from time import sleep
                sleep(pause_period)
            else:
                operation_done = True
        finally:
            lock.release()
        conn.close()


def check_journal_pragma(base):
    c, conn = connect_to_base(base)
    c.execute("PRAGMA journal_mode")
    if str(c.fetchall()[0][0]).upper() != "WAL":
        c.execute("PRAGMA JOURNAL_MODE = WAL")
        conn.commit()
    conn.close()


global_var.init()


def check_column(base, table, column, column_type, default_value):
    column_exist = select(what="count(*)",
                          table="pragma_table_info('%s')" % table,
                          expression="name='%s'" % column,
                          base=base)[0][0]

    if column_exist == 0:
        command_adw(what="ALTER TABLE %s ADD COLUMN %s %s default %s" % (table, column, column_type, default_value),
                    base=base)
        return False
    else:
        return True
