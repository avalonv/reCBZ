#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os
from sys import exit
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from tempfile import TemporaryDirectory
from functools import partial
from shutil import get_terminal_size

from PIL import Image

import recbz
from recbz.formats import *

# TODO:
# include docstrings
# consider replacing os.path with pathlib, as it might be simpler:
# https://docs.python.org/3/library/pathlib.html#correspondence-to-tools-in-the-os-module

# limit output message width. ignored if verbose
TERM_COLUMNS, TERM_LINES = get_terminal_size()
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
        self.overwrite:bool = recbz.OVERWRITE
        self.force:bool = recbz.FORCE
        self.loglevel:int = recbz.LOGLEVEL
        self.parallel:bool = recbz.PARALLEL
        self.processes:int = recbz.PROCESSES
        self.zipext:str = recbz.ZIPEXT
        self.compresslevel:int = recbz.COMPRESSLEVEL
        self.comparesamples:int = recbz.COMPARESAMPLES
        self.nowrite:bool = recbz.NOWRITE
        self.blacklistedfmts:str = recbz.BLACKLISTEDFMTS
        self.formatname:str = recbz.FORMATNAME
        self.quality:int = recbz.QUALITY
        self.resolution:str = recbz.RESOLUTION
        self.noupscale:bool = recbz.NOUPSCALE
        self.nodownscale:bool = recbz.NODOWNSCALE
        self.grayscale:bool = recbz.GRAYSCALE
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

    def __init__(self, filename:str, config:Config):
        if os.path.isfile(filename): self.filename:str = filename
        else: raise ValueError(f"{filename}: invalid path")
        self.conf:Config = config
        # only used in analyze(). might i move it there?
        self.valid_formats:tuple = self.conf._get_validformats

    def repack(self) -> tuple:
        start_t = time.perf_counter()
        self._log(f'Extracting: {self.filename}', progress=True)
        try:
            source_zip = ZipFile(self.filename)
        except BadZipFile as err:
            print(f"[Fatal] '{self.filename}': not a zip file")
            exit(2)
        source_size = os.path.getsize(self.filename)
        source_stem = os.path.splitext(str(source_zip.filename))[0]
        # extract all
        with TemporaryDirectory() as tempdir:
            source_zip.extractall(tempdir)
            source_zip.close()
            # https://stackoverflow.com/a/3207973/8225672 absolutely nightmarish
            # but this is the only way to avoid problems with subfolders
            source_imgs = [os.path.join(dpath,f) for (dpath, dnames, fnames)
                            in os.walk(tempdir) for f in fnames]
            assert len(source_imgs) >= 1, 'no files in archive'

            # process images in place
            if self.conf.parallel:
                pcount = min(len(source_imgs), self.conf._get_pcount)
                with Pool(processes=pcount) as MPpool:
                    results = MPpool.map(self._transform_img, source_imgs)
            else:
                results = map(self._transform_img, source_imgs)
            imgs_abspath = [path for path in results if path]
            imgs_names = [os.path.basename(f) for f in imgs_abspath] # not unecessary (I think)

            # sanity check
            discarded = len(source_imgs) - len(imgs_abspath)
            if discarded > 0:
                self._log('', progress=True)
                print(f"[!] {discarded} files had errors and had to be discarded.")
            if self.conf.overwrite:
                if discarded and not self.conf.force:
                    reply = input("■─■ Proceed with overwriting? [y/n]").lower()
                    if reply not in ('y', 'yes'):
                        print('[!] Aborting')
                        exit(1)
                new_path = self.filename
            else:
                new_path = f'{source_stem} [reCBZ]{self.conf.zipext}'

            if self.conf.nowrite:
                end_t = time.perf_counter()
                elapsed = f'{end_t - start_t:.2f}s'
                return (self.filename, elapsed, 'Dry run')
            # write to new local archive
            if os.path.exists(new_path):
                self._log(f'{new_path} exists, removing...')
                os.remove(new_path)
            new_zip = ZipFile(new_path,'w')
            self._log(f'Write {self.conf.zipext}: {new_path}', progress=True)
            for source, dest in zip(imgs_abspath, imgs_names):
                new_zip.write(source, dest, ZIP_DEFLATED, self.conf.compresslevel)
            new_zip.close()
            new_size = os.path.getsize(new_path)
        end_t = time.perf_counter()
        elapsed = f'{end_t - start_t:.2f}s'
        diff = Archive._diff_summary_repack(source_size, new_size)
        self._log('', progress=True)
        return new_path, elapsed, diff

    def analyze(self) -> tuple:
        def test_fmt(sample_imgs, tempdir, fmt) -> tuple:
            fmtdir = os.path.join(tempdir, fmt.name)
            os.mkdir(fmtdir)
            pfunc = partial(self._transform_img, dest=fmtdir, forceformat=fmt)
            if self.conf.parallel:
                pcount = min(len(sample_imgs), self.conf._get_pcount)
                with Pool(processes=pcount) as MPpool:
                    results = MPpool.map(pfunc, sample_imgs)
            else:
                results = map(pfunc, sample_imgs)
            converted_imgs = [path for path in results if path]
            nbytes = sum(os.path.getsize(f) for f in converted_imgs)
            return nbytes, fmt.desc, fmt.name

        self._log(f'Extracting: {self.filename}', progress=True)
        try:
            source_zip = ZipFile(self.filename)
        except BadZipFile as err:
            print(f"[Fatal] '{self.filename}': not a zip file")
            exit(2)
        compressed_files = source_zip.namelist()

        # select x images from the middle of the archive, in increments of two
        sample_size = self.conf.comparesamples
        if sample_size * 2 > len(compressed_files):
            raise ValueError(f"{self.filename} is smaller than sample_size * 2")
        delta = int(len(compressed_files) / 2)
        sample_imgs = compressed_files[delta-sample_size:delta+sample_size:2]

        # extract them and compute their size
        size_totals = []
        with TemporaryDirectory() as tempdir:
            for name in sample_imgs:
                source_zip.extract(name, tempdir)
            source_zip.close()
            sample_imgs = [os.path.join(dpath,f) for (dpath, dnames, fnames)
                            in os.walk(tempdir) for f in fnames]
            nbytes = sum(os.path.getsize(f) for f in sample_imgs)
            sample_fmt = determine_format(Image.open(sample_imgs[0]))
            size_totals = [(nbytes, f'{sample_fmt.desc} ({Archive.source_id})',
                           sample_fmt.name)]
            # also compute the size of each valid format after converting
            pfunc = partial(test_fmt, sample_imgs, tempdir)
            if self.conf.parallel:
                with ThreadPool(processes=len(self.valid_formats)) as Tpool:
                    size_totals.extend(Tpool.map(pfunc, self.valid_formats))
            else:
                size_totals.extend(map(pfunc, self.valid_formats))

        # finally, compare
        # in multidepth lists, sorted compares the first element by default :)
        sorted_raw = tuple(sorted(size_totals))
        summary = Archive._diff_summary_analyze(sorted_raw, sample_size)
        choices_dic = {i : total[2] for i, total in enumerate(sorted_raw)}
        suggested_fmt = {"desc": sorted_raw[0][1], "name": sorted_raw[0][2]}
        self._log(str(sorted_raw))
        self._log('', progress=True)
        return summary, choices_dic, suggested_fmt, sorted_raw

    def _transform_img(self, source:str, dest=None, forceformat=None): #-> None | Str:
        start_t = time.perf_counter()
        source_stem, source_ext = os.path.splitext(source)
        source_ext = source_ext.lower()
        # open
        try:
            self._log(f'Read img: {os.path.basename(source)}', progress=True)
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
            log_buff += '|trans: mode L\n'
            img = img.convert('L')
        if self.conf._rescale:
            log_buff += f'|trans: resize to {self.conf._get_newsize}\n'
            img = self._resize_img(img)

        # save
        ext:str = new_fmt.ext[0]
        path:str
        if dest:
            path = os.path.join(dest, f'{os.path.basename(source_stem)}{ext}')
        else:
            path = f'{source_stem}{ext}'
        log_buff += f'|trans: {source_fmt.name} -> {new_fmt.name}\n'
        new_fmt.save(img, path)
        end_t = time.perf_counter()
        elapsed = f'{end_t-start_t:.2f}s'
        self._log(f'{log_buff}\\write: {path}: took {elapsed}')
        self._log(f'Save img: {os.path.basename(path)}', progress=True)
        return path

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

    @classmethod
    def _get_size_format(cls, b:float) -> str:
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

    @classmethod
    def _diff_summary_repack(cls, base:int, new:int) -> str:
        verb = 'decrease'
        if new > base:
            verb = 'INCREASE!'
        change = cls._get_pct_change(base, new)
        basepretty = cls._get_size_format(base)
        newpretty = cls._get_size_format(new)
        return f"{cls.source_id}: {basepretty} ■ New: {newpretty} ■ {change} {verb}"

    @classmethod
    def _diff_summary_analyze(cls, totals:tuple, sample_size:int) -> str:
        base = [total[0] for total in totals if cls.source_id in total[1]][0]
        summary = f'┌─ Disk size ({sample_size} pages) with present settings:\n'
        for i, total in enumerate(totals):
            if i == len(totals)-1:
                prefix = '└─'
            # elif i == 0:
            #     prefix = '┌───'
            else:
                prefix = '├─'
            change = cls._get_pct_change(base, total[0])
            fmt_name = total[1]
            human_size = cls._get_size_format(total[0])
            # justify to the left and right respectively. effectively the same
            # as using f'{part1: <25} | {part2: >8}\n'
            part1 = f'{prefix}■{i+1} {fmt_name}'.ljust(25)
            part2 = f'{human_size}'.rjust(8)
            summary += f'{part1} {part2} | {change}\n'
        return summary[0:-1] # strip last newline