import os

from PIL import Image

import reCBZ


class Config():
    tempuuid:str = reCBZ.TEMPUUID
    overwrite:bool = reCBZ.OVERWRITE
    ignore:bool = reCBZ.IGNORE
    nowrite:bool = reCBZ.NOWRITE
    loglevel:int = reCBZ.LOGLEVEL
    parallel:bool = reCBZ.PARALLEL
    processes:int = reCBZ.PROCESSES
    outformat:str = reCBZ.OUTFORMAT
    compresszip:int = reCBZ.COMPRESSZIP
    samplescount:int = reCBZ.SAMPLECOUNT
    blacklistedfmts:str = reCBZ.BLACKLISTEDFMTS
    imageformat:str = reCBZ.IMAGEFORMAT
    quality:int = reCBZ.QUALITY
    resolution:str = reCBZ.RESOLUTION
    noupscale:bool = reCBZ.NOUPSCALE
    nodownscale:bool = reCBZ.NODOWNSCALE
    grayscale:bool = reCBZ.GRAYSCALE
    # LANCZOS sacrifices performance for optimal upscale quality
    resamplemethod = Image.Resampling.LANCZOS
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
