from datetime import datetime


def split_by_n(input_var, n):
    seq = str(input_var)
    output = []
    while seq:
        output.append(seq[-n:])
        seq = seq[:-n]

    output_string = " ".join(map(str, reversed(output)))
    return output_string


# время когда можно производить покупку
def check_buy_time():
    # не покупаем с 23-00 до 9-59
    if datetime.now().hour >= 23 or datetime.now().hour <= 9:
        return False
    # не покупаем с 10-00 до 10-15
    if datetime.now().hour == 10 and datetime.now().minute <= 15:
        return False
    return True


def check_candeles_time():
    # не проверяем с 01-40 до 06-59
    hour = datetime.now().hour
    minute = datetime.now().minute
    if hour == 1 and minute >= 40:
        return False
    elif hour != 1 and hour <= 6:
        return False
    return True
