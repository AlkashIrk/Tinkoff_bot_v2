from bot.DB.DB import connect
from bot.DB.queries.shared.user import get_user_by_tgID


def check_user(chat_id):
    db_session = connect("shared")
    user_info = get_user_by_tgID(db_session, chat_id)
    db_session.close_session()

    if user_info is not None:
        return user_info
    else:
        return None
