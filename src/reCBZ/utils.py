from shutil import get_terminal_size

import reCBZ
from .config import Config


def mylog(msg:str, progress=False) -> None:
    max_width = Config().term_width
    if Config.loglevel == -1:
        return
    elif Config.loglevel > 2:
        print(msg, flush=True)
    elif Config.loglevel == 2 and not progress:
        print(msg, flush=True)
    elif Config.loglevel == 1 and progress:
        msg = '[*] ' + msg
        msg = msg[:max_width]
        print(f'{msg: <{max_width}}', end='\n', flush=True)
    elif Config.loglevel == 0 and progress:
        # # no newline (i.e. overwrite line)
        msg = '[*] ' + msg
        msg = msg[:max_width]
        print(f'{msg: <{max_width}}', end='\r', flush=True)


def human_bytes(b:float) -> str:
    # derived from https://github.com/x4nth055 (MIT)
    suffix = "B"
    FACTOR = 1024
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < FACTOR:
            return f"{b:.2f}{unit}{suffix}"
        b /= FACTOR
    return f"{b:.2f}Y{suffix}"


def pct_change(base:float, new:float) -> str:
    diff = new - base
    pct_change = diff / base * 100
    if pct_change >= 0:
        return f"+{pct_change:.2f}%"
    else:
        return f"{pct_change:.2f}%"
