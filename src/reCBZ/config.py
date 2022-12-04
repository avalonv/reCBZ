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
    ignore_err:bool = _cfg["archive"]["ignore"]
    force_write:bool = _cfg["archive"]["force"]
    no_write:bool = _cfg["archive"]["nowrite"]
    loglevel:int = _cfg["archive"]["loglevel"]
    no_parallel:bool = _cfg["archive"]["noparallel"]
    processes:int = _cfg["archive"]["processes"]
    archive_format:str = _cfg["archive"]["archiveformat"]
    compress_zip:int = _cfg["archive"]["compresszip"]
    samples_count:int = _cfg["archive"]["samplecount"]
    blacklisted_fmts:str = _cfg["archive"]["blacklistedfmts"]
    img_format:str = _cfg["archive"]["imageformat"]
    img_quality:int = _cfg["archive"]["quality"]
    img_size:tuple = _cfg["archive"]["size"]
    no_upscale:bool = _cfg["archive"]["noupscale"]
    no_downscale:bool = _cfg["archive"]["nodownscale"]
    grayscale:bool = _cfg["archive"]["grayscale"]
    # LANCZOS sacrifices performance for optimal upscale quality
    resamplemethod = Image.Resampling.LANCZOS
    ebook_profile = None
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
        cls.img_size = profile.size
        # if profile.prefer_epub:
        cls.archive_format = 'epub'
        cls.ebook_profile = profile
        cls.blacklisted_fmts += profile.blacklisted_fmts
