from copy import deepcopy

from db import get_script, save_script
from bot.utils import normalize_key


def get_script_or_none(script_key: str):
    return get_script(normalize_key(script_key))


def clone_script(script: dict):
    return deepcopy(script)


def save_script_record(script: dict):
    save_script(script)
