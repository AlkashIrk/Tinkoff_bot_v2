from bot.DB.DB import connect
from bot.cfg.logs_work import debuginfo
from bot.database import base_sqlite


def db_upd_balance(balance: dict):
    """
        обновление баланса в локальной базе
    """
    try:
        base_sqlite.command_adw(
            what="""CREATE TABLE balance(id INTEGER PRIMARY KEY AUTOINCREMENT
            name TEXT,
            balance REAL,
            blocked REAL
            )""",
            base="private",
            print_error=False)
    except Exception as inst:
        if inst.args[0] != "table balance already exists":
            debuginfo("Error here: CREATE TABLE balance")
            print("\t%s" % inst)
    for curr in balance:
        currency_name = curr
        currency_balance = balance[curr].get('balance')
        currency_blocked = balance[curr].get('blocked')
        select_currency = base_sqlite.select(
            what="*",
            table="balance",
            expression="name='%s'" % currency_name,
            base="private"
        )
        if len(select_currency) != 0:
            try:
                data = (
                    currency_balance,
                    currency_blocked,
                )
                data = [tuple(data)]
                base_sqlite.update_data(
                    table="balance",
                    expression="set balance=?, blocked=? "
                               "WHERE name='%s'" % currency_name,
                    data=data,
                    base="private"
                )
            except Exception as inst:
                print("\t%s" % inst)
        else:
            try:
                data = (
                    currency_name,
                    currency_balance,
                    currency_blocked,
                )
                data = [tuple(data)]
                base_sqlite.insert_data(
                    table="balance(name,balance,blocked)",
                    data=data,
                    base="private"
                )
            except Exception as inst:
                print("\t%s" % inst)
