import textwrap
from shutil import get_terminal_size

import reCBZ
from .config import Config


def shorten(*args, width=Config().term_width) -> str:
    text = ' '.join(args)
    return textwrap.shorten(text, width=width, placeholder='...')


def mylog(msg:str, progress=False) -> None:
    if Config.loglevel == -1:
        return
    elif Config.loglevel > 2:
        print(msg, flush=True)
    elif Config.loglevel == 2 and not progress:
        print(msg, flush=True)
    elif Config.loglevel == 1 and progress:
        msg = '[*] ' + msg
        msg = shorten(msg)
        print(msg, end='\n', flush=True)
    elif Config.loglevel == 0 and progress:
        # no newline (i.e. overwrite line)
        # flush last first
        print('[*]'.ljust(Config().term_width), end='\r')
        msg = '[*] ' + msg
        msg = shorten(msg)
        print(msg, end='\r', flush=True)


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
