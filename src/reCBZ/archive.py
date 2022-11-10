#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os
import tempfile
import shutil
from sys import exit
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, BadZipFile
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from functools import partial
from pathlib import Path

from PIL import Image

import reCBZ
from reCBZ.formats import *

# TODO:
# include docstrings

# limit output message width. ignored if verbose
TERM_COLUMNS, TERM_LINES = shutil.get_terminal_size()
try:
    assert TERM_COLUMNS > 0 and TERM_LINES > 0
    if TERM_COLUMNS > 120: max_width = 120
    elif TERM_COLUMNS < 30: max_width = 30
    else: max_width = TERM_COLUMNS - 2
except AssertionError:
    print("[!] Can't determine terminal size, defaulting to 80 cols")
    max_width = 80


class Config():
    def __init__(self):
        self.overwrite:bool = reCBZ.OVERWRITE
        self.force:bool = reCBZ.FORCE
        self.loglevel:int = reCBZ.LOGLEVEL
        self.parallel:bool = reCBZ.PARALLEL
        self.processes:int = reCBZ.PROCESSES
        self.zipext:str = reCBZ.ZIPEXT
        self.compresslevel:int = reCBZ.COMPRESSLEVEL
        self.comparesamples:int = reCBZ.COMPARESAMPLES
        self.nowrite:bool = reCBZ.NOWRITE
        self.blacklistedfmts:str = reCBZ.BLACKLISTEDFMTS
        self.formatname:str = reCBZ.FORMATNAME
        self.quality:int = reCBZ.QUALITY
        self.resolution:str = reCBZ.RESOLUTION
        self.noupscale:bool = reCBZ.NOUPSCALE
        self.nodownscale:bool = reCBZ.NODOWNSCALE
        self.grayscale:bool = reCBZ.GRAYSCALE
        # LANCZOS sacrifices performance for optimal upscale quality
        self.resamplemethod = Image.Resampling.LANCZOS

    @property
    def _get_pcount(self) -> int:
        default_value = 8
        if self.processes > 0:
            return self.processes
        else:
            logical_cores = os.cpu_count()
            try:
                assert logical_cores is not None
                return logical_cores
            except AssertionError:
                return default_value

    @property
    def _get_targetformat(self):
        if self.formatname in (None, ''): return None
        elif self.formatname == 'jpeg': return Jpeg
        elif self.formatname == 'png': return Png
        elif self.formatname == 'webp': return WebpLossy
        elif self.formatname == 'webpll': return WebpLossless
        else: return None

    @property # TODO finish this
    def _get_validformats(self) -> tuple:
        LossyFmt.quality = self.quality
        all_fmts = (Png, Jpeg, WebpLossy, WebpLossless)
        try:
            blacklist = self.blacklistedfmts.lower().split(' ')
        except AttributeError: # blacklist is None
            return all_fmts
        valid_fmts = tuple(fmt for fmt in all_fmts if fmt.name not in blacklist)
        assert len(valid_fmts) >= 1, "valid_formats is 0"
        return valid_fmts

    @property
    def _get_newsize(self) -> tuple:
        default_value = (0,0)
        newsize = self.resolution.lower().strip()
        try:
            newsize = tuple(map(int,newsize.split('x')))
            assert len(newsize) == 2
            return newsize
        except (ValueError, AssertionError):
            return default_value

    @property
    def _rescale(self) -> bool:
        if all(self._get_newsize):
            return True
        else:
            return False


class Archive():
    source_id:str = 'Source'
    temp_prefix:str = f'{reCBZ.CMDNAME}CACHE_'

    def __init__(self, filename:str, config:Config):
        if Path(filename).exists():
            self.source_path:Path = Path(filename)
        else:
            raise ValueError(f"{filename}: invalid path")
        self.source_size = self.source_path.stat().st_size
        self.source_stem = self.source_path.stem
        self.conf:Config = config
        self.valid_formats:tuple = self.conf._get_validformats
        self.tempdir:Path = Path('.')
        self._unpacked:list = []

    def fetch_unpacked(self):
        # caches images for later use, useful for repacking to two book formats
        # at the same time (e.g. epub and cbz)
        if len(self._unpacked) == 0:
            self._unpacked = self.unpack()
        return self._unpacked

    def unpack(self, count:int=0) -> list:
        # check and clean previous tempdirs
        prev_dirs = Path(tempfile.gettempdir()).glob(f'{self.temp_prefix}*')
        for path in prev_dirs:
            assert path != tempfile.gettempdir() # for the love of god
            self._log(f'{path} exists, cleaning up')
            shutil.rmtree(path)

        self.tempdir = Path(tempfile.mkdtemp(prefix=f'{self.temp_prefix}'))
        try:
            source_zip = ZipFile(self.source_path)
        except BadZipFile as err:
            print(f"[Fatal] '{self.source_path}': not a zip file")
            raise ValueError

        compressed_files = source_zip.namelist()
        assert len(compressed_files) >= 1, 'no files in archive'
        if count > 0:
            # select x images from the middle of the archive, in increments of 2
            if count * 2 > len(compressed_files):
                raise ValueError(f"{self.source_path} is smaller than samples * 2")
            delta = int(len(compressed_files) / 2)
            compressed_files = compressed_files[delta-count:delta+count:2]

        self._log(f'Extracting: {self.source_path}', progress=True)
        for file in compressed_files:
            source_zip.extract(file, self.tempdir)
        # god bless you Georgy https://stackoverflow.com/a/50927977/
        unpacked = list(filter(Path.is_file, Path(self.tempdir).rglob('*')))
        return unpacked

    def repack(self) -> tuple:
        start_t = time.perf_counter()

        # extract all and process images in place
        source_imgs = self.fetch_unpacked()
        if self.conf.parallel:
            pcount = min(len(source_imgs), self.conf._get_pcount)
            with Pool(processes=pcount) as MPpool:
                results = MPpool.map(self._transform_img, source_imgs)
        else:
            results = map(self._transform_img, source_imgs)
        imgs_abspath = [path for path in results if path]

        # sanity check
        discarded = len(source_imgs) - len(imgs_abspath)
        if discarded > 0:
            self._log('', progress=True)
            print(f"[!] {discarded} files had errors and will be discarded.")
            if not self.conf.force:
                reply = input("■─■ Proceed with writing archive? [y/n]").lower()
                if reply not in ('y', 'yes'):
                    print('[!] Aborting')
                    return ('ABORTED', )
        if self.conf.overwrite:
            new_path = self.source_path
        else:
            new_path = Path(f'{self.source_stem} [reCBZ]{self.conf.zipext}')

        # write to new local archive
        if self.conf.nowrite:
            end_t = time.perf_counter()
            elapsed = f'{end_t - start_t:.2f}s'
            return (self.source_path, elapsed, 'Dry run')
        elif new_path.exists():
            self._log(f'{new_path} exists, removing...')
            new_path.unlink()
        new_zip = ZipFile(new_path,'w')
        self._log(f'Write {self.conf.zipext}: {new_path}', progress=True)
        for source in imgs_abspath:
            try:
                dest = Path(source).relative_to(self.tempdir)
                # minimal effect on filesize. TODO further testing on how it
                # affects time to open in an ereader required
                new_zip.write(source, dest, ZIP_DEFLATED, 9)
                # new_zip.write(source, dest)
            except ValueError:
                msg = 'Path is being screwy. Does tempdir exist? '
                msg += str(self.tempdir.exists())
                msg += '\nwe might not have joined paths correctly in trans img'
                raise ValueError(msg)
        new_zip.close()
        new_size = new_path.stat().st_size
        end_t = time.perf_counter()
        elapsed = f'{end_t - start_t:.2f}s'
        diff = self._summary_diff_archive(self.source_size, new_size)
        self._log('', progress=True)
        print(new_path)
        return new_path, elapsed, diff

    def analyze(self) -> tuple:
        def compute_fmt_size(sample_imgs, tempdir, fmt) -> tuple:
            fmtdir = Path.joinpath(tempdir, fmt.name)
            Path.mkdir(fmtdir)
            pfunc = partial(self._transform_img, dest=fmtdir, forceformat=fmt)
            if self.conf.parallel:
                pcount = min(len(sample_imgs), self.conf._get_pcount)
                with Pool(processes=pcount) as MPpool:
                    results = MPpool.map(pfunc, sample_imgs)
            else:
                results = map(pfunc, sample_imgs)
            converted_imgs = [path for path in results if path]
            nbytes = sum(Path(f).stat().st_size for f in converted_imgs)
            return nbytes, fmt.desc, fmt.name

        # extract images and compute their original size
        # these aren't saved to cache
        source_imgs = self.unpack(count=self.conf.comparesamples)
        nbytes = sum(Path(f).stat().st_size for f in source_imgs)
        source_fmt = determine_format(Image.open(source_imgs[0]))
        source_fsize = (nbytes, f'{Archive.source_id} ({source_fmt.desc})',
                        source_fmt.name)
        # also compute the size of each valid format after converting
        fmt_fsizes = []
        pfunc = partial(compute_fmt_size, source_imgs, self.tempdir)
        if self.conf.parallel:
            with ThreadPool(processes=len(self.valid_formats)) as Tpool:
                fmt_fsizes.extend(Tpool.map(pfunc, self.valid_formats))
        else:
            fmt_fsizes.extend(map(pfunc, self.valid_formats))

        # finally, compare
        # in multidepth lists, sorted compares the first element by default :)
        sorted_fmts = tuple(sorted(fmt_fsizes))
        summary = self._summary_diff_fmts(source_fsize, sorted_fmts)
        choices_dic = {i : total[2] for i, total in enumerate(sorted_fmts)}
        suggested_fmt = {"desc":sorted_fmts[0][1], "name":sorted_fmts[0][2]}
        self._log(str(sorted_fmts))
        self._log('', progress=True)
        return summary, choices_dic, suggested_fmt, sorted_fmts

    def _transform_img(self, source:Path, dest=None, forceformat=None): #-> None | Str:
        # open
        start_t = time.perf_counter()
        try:
            self._log(f'Read img: {source.name}', progress=True)
            log_buff = f'/open:  {source}\n'
            img = Image.open(source)
        except IOError:
            self._log(f"{source}: can't open file as image, ignoring...'")
            return None

        # determine target format
        try:
            source_fmt = determine_format(img)
        except KeyError:
            self._log(f"{source}: invalid image format, ignoring...'")
            return None
        if forceformat:
            new_fmt = forceformat
        elif self.conf._get_targetformat is not None:
            new_fmt = self.conf._get_targetformat
        else:
            new_fmt = source_fmt

        # apply format specific actions
        if new_fmt is Jpeg:
          if not img.mode == 'RGB':
              log_buff += '|trans: mode RGB\n'
              img = img.convert('RGB')

        # transform
        if self.conf.grayscale:
            log_buff += '|trans: mode L\n' # me lol
            img = img.convert('L')
        if self.conf._rescale:
            log_buff += f'|trans: resize to {self.conf._get_newsize}\n'
            img = self._resize_img(img)

        # save
        ext:str = new_fmt.ext[0]
        if dest:
            p = Path.joinpath(dest, f'{source.stem}{ext}')
        else:
            p = Path.joinpath(source.parents[0], f'{source.stem}{ext}')
        log_buff += f'|trans: {source_fmt.name} -> {new_fmt.name}\n'
        new_fmt.save(img, p)
        end_t = time.perf_counter()
        elapsed = f'{end_t-start_t:.2f}s'
        self._log(f'{log_buff}\\write: {p}: took {elapsed}')
        self._log(f'Save img: {p.name}', progress=True)
        return p

    def _resize_img(self, img:Image.Image) -> Image.Image:
        width, height = img.size
        newsize = self.conf._get_newsize
        # preserve aspect ratio for landscape images
        if width > height:
            newsize = newsize[::-1]
        n_width, n_height = newsize
        # downscaling
        if (width>n_width) and (height>n_height) and not self.conf.nodownscale:
            img = img.resize((newsize), self.conf.resamplemethod)
        # upscaling
        elif not self.conf.noupscale:
            img = img.resize((newsize), self.conf.resamplemethod)
        return img

    def _log(self, msg:str, progress=False) -> None:
        if self.conf.loglevel == -1:
            return
        elif self.conf.loglevel > 2:
            print(msg, flush=True)
        elif self.conf.loglevel == 2 and not progress:
            print(msg, flush=True)
        elif self.conf.loglevel == 1 and progress:
            msg = '[*] ' + msg
            msg = msg[:max_width]
            print(f'{msg: <{max_width}}', end='\n', flush=True)
        elif self.conf.loglevel == 0 and progress:
            # # no newline (i.e. overwrite line)
            msg = '[*] ' + msg
            msg = msg[:max_width]
            print(f'{msg: <{max_width}}', end='\r', flush=True)

    def _summary_diff_fmts(self, base:tuple, totals:tuple) -> str:
        summary = f'┌─ Disk size ({self.conf.comparesamples}' + \
                   ' pages) with present settings:\n'
        # justify to the left and right respectively. effectively the same
        # as using f'{part1: <25} | {part2: >8}\n'
        part1 = f'│   {base[1]}'.ljust(25)
        part2 = f'{Archive._get_human_size(base[0])}'.rjust(8)
        summary += f'{part1} {part2} |  0.00%\n'
        for i, total in enumerate(totals):
            if i == len(totals)-1:
                prefix = '└─'
            else:
                prefix = '├─'
            change = Archive._get_pct_change(base[0], total[0])
            part1 = f'{prefix}{i+1} {total[1]}'.ljust(25)
            part2 = f'{Archive._get_human_size(total[0])}'.rjust(8)
            summary += f'{part1} {part2} | {change}\n'
        return summary[0:-1] # strip last newline

    def _summary_diff_archive(self, base:int, new:int) -> str:
        verb = 'decrease'
        if new > base:
            verb = 'INCREASE!'
        change = Archive._get_pct_change(base, new)
        basepretty = Archive._get_human_size(base)
        newpretty = Archive._get_human_size(new)
        return f'{Archive.source_id}: {basepretty} ■ New:' + \
               f'{newpretty} ■ {change} {verb}'

    @classmethod
    def _get_human_size(cls, b:float) -> str:
        # derived from https://github.com/x4nth055 (MIT)
        suffix = "B"
        FACTOR = 1024
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if b < FACTOR:
                return f"{b:.2f}{unit}{suffix}"
            b /= FACTOR
        return f"{b:.2f}Y{suffix}"

    @classmethod
    def _get_pct_change(cls, base:float, new:float) -> str:
        diff = new - base
        pct_change = diff / base * 100
        if pct_change >= 0:
            return f"+{pct_change:.2f}%"
        else:
            return f"{pct_change:.2f}%"
