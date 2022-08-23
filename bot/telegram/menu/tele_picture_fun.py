global white_list


def check_if_in_list(id: int):
    if id in white_list:
        return True
    return False
