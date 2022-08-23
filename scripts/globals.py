import bot.cfg.config_data
import os


token = ""
user_login = ""
telegram_token = ""
telegram_id = 0
account_id = ""
sandbox_token = ""

# Для бота телеграм
updater = ""
menu_message = {}
last_message_id = 0
base_list = []
base_name_private = ""
base_name = ""
bck_folder_path = ""
base_folder_path = ""


def init():
    global base_folder_path
    global base_name
    global base_name_private

    global bck_folder_path
    global settings
    global token, sandbox_token

    global telegram_token
    global telegram_id

    # Для бота телеграм
    global last_message_id
    global updater
    global menu_message

    global user_login
    global account_id

    global base_list

    settings = {}

    config = bot.cfg.config_data.config_read()

    token = config["token"]
    sandbox_token = config["sandbox_token"]
    telegram_token = config["telegram_token"]
    try:
        token = config["token"]
    except:
        token = None

    try:
        telegram_token = config["telegram_token"]
    except:
        telegram_token = None

    try:
        telegram_id = config["telegram_id"]
    except:
        telegram_id = 0

    try:
        user_login = config["login"]
    except:
        user_login = ""

    bck_folder_path = config["backup_folder"]
    base_folder_path = config["base_folder"]
    base_name = config["base_main"]

    try:
        base_name_private = config["base_private"]
    except:
        pass

    if token == "your_token" or token is None:
        config_path = os.getcwd() + "\\cfg\\config.ini"
        print("Enter your token to config:\n\t%s" % config_path)
        exit()
