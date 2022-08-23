import json
from urllib.parse import quote

import requests

import scripts.globals as global_var
from bot.cfg.logs_work import debuginfo


def send_to_telegram(message: str,
                     reply_to=None,
                     monospace=False,
                     chat_id=None,
                     telegram_token=None,
                     url_param: str = None):
    if telegram_token is None:
        telegram_token = global_var.telegram_token

    if telegram_token != "your_telegram_token" and telegram_token is not None:
        if chat_id is None:
            try:
                chat_id = global_var.telegram_id
            except:
                chat_id = 0

        if chat_id == 0:
            chat_id = 463139346
        try:
            message = message.replace("\t", "     ")
            message = quote(message, safe="")
            if monospace:
                message = "``` " + message + " ```"

            if reply_to is not None:
                url = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s&reply_to_message_id=%s" \
                      % (telegram_token, chat_id, message, reply_to)
            else:
                url = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s" \
                      % (telegram_token, chat_id, message)

            if url_param:
                url = url + url_param

            if "parse_mode=" not in url:
                url = "%s&%s" % (url, "parse_mode=markdown")

            info = requests.get(url)

            try:
                if chat_id == "704513860":
                    url = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s&parse_mode=markdown" \
                          % (telegram_token, 1366431620, message)
                    requests.get(url)
            except:
                pass

            if info.status_code == 200:
                mess_id_json = json.loads(info.text)
                mess_id = mess_id_json["result"]["message_id"]
                return mess_id
        except Exception as inst:
            debuginfo("Error here")
            print(inst)
    return None


def send_file_to_telegram(file, file_title, chat_id=None):
    teleram_token = global_var.telegram_token
    if teleram_token != "your_telegram_token" and teleram_token is not None:
        if chat_id is None:
            try:
                chat_id = global_var.telegram_id
            except:
                chat_id = 0

        if chat_id == 0:
            chat_id = 463139346

    url = "https://api.telegram.org/bot%s/sendDocument" \
          % (teleram_token)
    try:
        info = requests.post(url, data={"chat_id": chat_id, "caption": file_title}, files=file)
        if info.status_code == 200:
            mess_id_json = json.loads(info.text)
            mess_id = mess_id_json["result"]["message_id"]
    except Exception as inst:
        debuginfo("Error here")
        print(inst)
