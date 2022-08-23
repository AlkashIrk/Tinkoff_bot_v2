import scripts.globals as global_var
import configparser
import os

from os import path
from pathlib import Path
from bot.cfg.parse_params import get_params

args = get_params()

if args.cfg:
    cfg_path = args.cfg
else:
    cfg_path = "cfg/config.ini"
config = configparser.ConfigParser()


def config_write(need_init=False):
    # global config
    if need_init:
        base_folder_path = os.getcwd() + "\\base\\"
        bck_folder_path = os.getcwd() + "\\bck\\"

        config["Folders"] = \
            {
                "Base_folder": base_folder_path,
                "Backup_folder": bck_folder_path
            }
        config["Files"] = {"Base_main": "market.db"}
        config["Options"] = \
            {
                "Backup_base": "False",
                "token": "your_token",
                "sandbox_token": "your_token"
            }

        config["Telegram"] = \
            {
                "telegram_token": "your_telegram_token"
            }

    Path(os.path.dirname(cfg_path)).mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w") as configfile:
        config.write(configfile)


def config_read():
    global settings

    if not path.exists(cfg_path):
        config_write(need_init=True)

    config.read(cfg_path)

    for each_section in config.sections():
        for (each_key, each_val) in config.items(each_section):
            global_var.settings[each_key] = each_val
    return global_var.settings
