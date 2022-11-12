import os

from PIL import Image

import reCBZ
from . import formats as fmt


class Config():
    overwrite:bool = reCBZ.OVERWRITE
    force:bool = reCBZ.FORCE
    loglevel:int = reCBZ.LOGLEVEL
    parallel:bool = reCBZ.PARALLEL
    processes:int = reCBZ.PROCESSES
    zipext:str = reCBZ.ZIPEXT
    compresslevel:int = reCBZ.COMPRESSLEVEL
    comparesamples:int = reCBZ.COMPARESAMPLES
    nowrite:bool = reCBZ.NOWRITE
    blacklistedfmts:str = reCBZ.BLACKLISTEDFMTS
    formatname:str = reCBZ.FORMATNAME
    quality:int = reCBZ.QUALITY
    resolution:str = reCBZ.RESOLUTION
    noupscale:bool = reCBZ.NOUPSCALE
    nodownscale:bool = reCBZ.NODOWNSCALE
    grayscale:bool = reCBZ.GRAYSCALE
    # LANCZOS sacrifices performance for optimal upscale quality
    resamplemethod = Image.Resampling.LANCZOS

    @property
    def _get_pcount(cls) -> int:
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

    @property
    def _get_targetformat(cls):
        if cls.formatname in (None, ''): return None
        elif cls.formatname == 'jpeg': return fmt.Jpeg
        elif cls.formatname == 'png': return fmt.Png
        elif cls.formatname == 'webp': return fmt.WebpLossy
        elif cls.formatname == 'webpll': return fmt.WebpLossless
        else: return None

    @property # TODO finish this
    def _get_validformats(cls) -> tuple:
        fmt.LossyFmt.quality = cls.quality
        all_fmts = (fmt.Png, fmt.Jpeg, fmt.WebpLossy, fmt.WebpLossless)
        try:
            blacklist = cls.blacklistedfmts.lower().split(' ')
        except AttributeError: # blacklist is None
            return all_fmts
        valid_fmts = tuple(fmt for fmt in all_fmts if fmt.name not in blacklist)
        assert len(valid_fmts) >= 1, "valid_formats is 0"
        return valid_fmts

    @property
    def _get_newsize(cls) -> tuple:
        default_value = (0,0)
        newsize = cls.resolution.lower().strip()
        try:
            newsize = tuple(map(int,newsize.split('x')))
            assert len(newsize) == 2
            return newsize
        except (ValueError, AssertionError):
            return default_value

    @property
    def _rescale(cls) -> bool:
        if all(cls._get_newsize):
            return True
        else:
            return False

    @property
    def term_width(cls) -> int:
        # limit output message width. ignored if verbose
        TERM_COLUMNS, TERM_LINES = os.get_terminal_size()
        try:
            assert TERM_COLUMNS > 0 and TERM_LINES > 0
            if TERM_COLUMNS > 120: max_width = 120
            elif TERM_COLUMNS < 30: max_width = 30
            else: max_width = TERM_COLUMNS - 2
        except AssertionError:
            print("[!] Can't determine terminal size, defaulting to 78 cols")
            max_width = 78
        return max_width
