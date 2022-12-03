import os
from importlib import resources

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from PIL import Image

from reCBZ.profiles import profiles_list
import reCBZ


class Config():
    _cfg = tomllib.loads(resources.read_text("reCBZ", "defaults.toml"))
    tempuuid:str = reCBZ.TEMPUUID
    overwrite:bool = _cfg["archive"]["overwrite"]
    ignore:bool = _cfg["archive"]["ignore"]
    nowrite:bool = _cfg["archive"]["nowrite"]
    loglevel:int = _cfg["archive"]["loglevel"]
    parallel:bool = _cfg["archive"]["parallel"]
    processes:int = _cfg["archive"]["processes"]
    bookformat:str = _cfg["archive"]["bookformat"]
    compresszip:int = _cfg["archive"]["compresszip"]
    samplescount:int = _cfg["archive"]["samplecount"]
    blacklistedfmts:str = _cfg["archive"]["blacklistedfmts"]
    imageformat:str = _cfg["archive"]["imageformat"]
    quality:int = _cfg["archive"]["quality"]
    size:tuple = _cfg["archive"]["size"]
    noupscale:bool = _cfg["archive"]["noupscale"]
    nodownscale:bool = _cfg["archive"]["nodownscale"]
    grayscale:bool = _cfg["archive"]["grayscale"]
    # LANCZOS sacrifices performance for optimal upscale quality
    resamplemethod = Image.Resampling.LANCZOS
    bookprofile = None
    ZIPCOMMENT:str = 'repacked with reCBZ'

    @classmethod
    def pcount(cls) -> int:
        default_value = 4
        if cls.processes > 0:
            return cls.processes
        else:
            logical_cores = os.cpu_count()
            try:
                assert logical_cores is not None
                if logical_cores > 1:
                    logical_cores -= 1 # be kind
                return logical_cores
            except AssertionError:
                return default_value

    @classmethod
    def term_width(cls) -> int:
        # limit output message width. ignored if verbose
        try:
            TERM_COLUMNS, TERM_LINES = os.get_terminal_size()
            assert TERM_COLUMNS > 0 and TERM_LINES > 0
            if TERM_COLUMNS > 120: max_width = 120
            elif TERM_COLUMNS < 30: max_width = 30
            else: max_width = TERM_COLUMNS - 2
        except (AssertionError, OSError):
            print("[!] Can't determine terminal size, defaulting to 78 cols")
            max_width = 78
        return max_width

    @classmethod
    def set_profile(cls, name) -> None:
        dic = {prof.nickname:prof for prof in profiles_list}
        try:
            profile = dic[name]
        except KeyError:
            raise ValueError(f'Invalid profile {name}')
        cls.grayscale = profile.gray
        cls.size = profile.size
        # if profile.prefer_epub:
        cls.bookformat = 'epub'
        cls.bookprofile = profile
