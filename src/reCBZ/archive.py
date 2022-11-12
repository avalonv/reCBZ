#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os
import tempfile
import shutil
import copy
from sys import exit
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, BadZipFile
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from functools import partial
from pathlib import Path

from PIL import Image

import reCBZ
from .formats import *
from .config import Config
from .utils import mylog

# TODO:
# include docstrings

class Archive():
    source_id:str = 'Source'
    new_id:str = ' [reCBZ]'
    temp_prefix:str = f'{reCBZ.CMDNAME}CACHE_'

    def __init__(self, filename:str):
        mylog('Archive: __init__')
        if Path(filename).exists():
            self.source_path:Path = Path(filename)
        else:
            raise ValueError(f"{filename}: invalid path")
        self.source_stem = self.source_path.stem
        # ideally, changing one shouldn't affect the other. changing one
        # instance's targetformat shouldn't apply to future instances. might not
        # actually need deepcopy(), haven't fully wrapped my head around it yet
        # self.opt:Config = Config()
        self.opt:Config = copy.deepcopy(Config())
        self.valid_formats:tuple = self.opt._get_validformats
        self.tempdir:Path = Path('.')
        self._extracted:list = []
        self._converted:list = []

    def fetch_extracted(self):
        """Fetches extracted files from cache if it exists, otherwise extracts
        them first."""
        if len(self._extracted) == 0:
            self._extracted = self.extract()
        return self._extracted

    def extract(self, count:int=0) -> list:
        # check and clean previous tempdirs
        prev_dirs = Path(tempfile.gettempdir()).glob(f'{self.temp_prefix}*')
        for path in prev_dirs:
            assert path != tempfile.gettempdir() # for the love of god
            mylog(f'{path} exists, cleaning up')
            shutil.rmtree(path)

        self.tempdir = Path(tempfile.mkdtemp(prefix=f'{self.temp_prefix}'))
        try:
            source_zip = ZipFile(self.source_path)
        except BadZipFile as err:
            raise ValueError(f"Fatal: '{self.source_path}': not a zip file")

        compressed_files = source_zip.namelist()
        assert len(compressed_files) >= 1, 'no files in archive'
        if count > 0:
            # select x images from the middle of the archive, in increments of 2
            if count * 2 > len(compressed_files):
                raise ValueError(f"{self.source_path} is smaller than samples * 2")
            delta = int(len(compressed_files) / 2)
            compressed_files = compressed_files[delta-count:delta+count:2]

        mylog(f'Extracting: {self.source_path}', progress=True)
        for file in compressed_files:
            source_zip.extract(file, self.tempdir)
        # god bless you Georgy https://stackoverflow.com/a/50927977/
        extracted = list(filter(Path.is_file, Path(self.tempdir).rglob('*')))
        mylog('', progress=True)
        return extracted

    def repack(self, booktype=None) -> str:
        # TODO fetch converted, fetch extracted otherwise
        # extract all and process images in place
        source_imgs = self.fetch_extracted()
        if self.opt.parallel:
            pcount = min(len(source_imgs), self.opt._get_pcount)
            with Pool(processes=pcount) as MPpool:
                results = MPpool.map(self._transform_img, source_imgs)
        else:
            results = map(self._transform_img, source_imgs)
        imgs_abspath = [path for path in results if path]

        # sanity check
        discarded = len(source_imgs) - len(imgs_abspath)
        if discarded > 0:
            mylog('', progress=True)
            if not self.opt.force:
                # TODO raise an error here, which we will except in wrappers.
                # check self.discarded for the total
                return f'ABORTED: {discarded} files had errors'
        if self.opt.overwrite:
            new_path = self.source_path
        else:
            new_path = Path(f'{self.source_stem}{Archive.new_id}{self.opt.zipext}')

        # write to new local archive
        if self.opt.nowrite:
            return 'DRY RUN'
        elif new_path.exists():
            mylog(f'{new_path} exists, removing...')
            new_path.unlink()
        new_zip = ZipFile(new_path,'w')
        mylog(f'Write {self.opt.zipext}: {new_path}', progress=True)
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
        mylog('', progress=True)
        return str(new_path)

    def compute_fmt_sizes(self) -> tuple:
        # TODO add convert_images method which will supplant most of this.
        # then we can call convert_images with ThreadPool :)
        def compute_fmt(sample_imgs, tempdir, fmt) -> tuple:
            fmtdir = Path.joinpath(tempdir, fmt.name)
            Path.mkdir(fmtdir)
            pfunc = partial(self._transform_img, dest=fmtdir, forceformat=fmt)
            if self.opt.parallel:
                pcount = min(len(sample_imgs), self.opt._get_pcount)
                with Pool(processes=pcount) as MPpool:
                    results = MPpool.map(pfunc, sample_imgs)
            else:
                results = map(pfunc, sample_imgs)
            converted_imgs = [path for path in results if path]
            nbytes = sum(Path(f).stat().st_size for f in converted_imgs)
            return nbytes, fmt.desc, fmt.name

        # extract images and compute their original size
        # these aren't saved to cache
        source_imgs = self.extract(count=self.opt.comparesamples)
        nbytes = sum(Path(f).stat().st_size for f in source_imgs)
        source_fmt = determine_format(Image.open(source_imgs[0]))
        source_fsize = [nbytes, f'{Archive.source_id} ({source_fmt.desc})',
                        source_fmt.name]
        # also compute the size of each valid format after converting
        fmt_fsizes = []
        pfunc = partial(compute_fmt, source_imgs, self.tempdir)
        if self.opt.parallel:
            with ThreadPool(processes=len(self.valid_formats)) as Tpool:
                fmt_fsizes.extend(Tpool.map(pfunc, self.valid_formats))
        else:
            fmt_fsizes.extend(map(pfunc, self.valid_formats))

        # finally, compare
        # in multidepth lists, sorted compares the first element by default :)
        sorted_fmts = list(sorted(fmt_fsizes))
        sorted_fmts.insert(0, source_fsize)
        mylog(str(sorted_fmts))
        mylog('', progress=True)
        return tuple(sorted_fmts)

    def _transform_img(self, source:Path, dest=None, forceformat=None): #-> None | Str:
        # open
        start_t = time.perf_counter()
        try:
            mylog(f'Read img: {source.name}', progress=True)
            log_buff = f'/open:  {source}\n'
            img = Image.open(source)
        except IOError:
            mylog(f"{source}: can't open file as image, ignoring...'")
            return None

        # determine target format
        try:
            source_fmt = determine_format(img)
        except KeyError:
            mylog(f"{source}: invalid image format, ignoring...'")
            return None
        if forceformat:
            new_fmt = forceformat
        elif self.opt._get_targetformat is not None:
            new_fmt = self.opt._get_targetformat
        else:
            new_fmt = source_fmt

        # apply format specific actions
        if new_fmt is Jpeg:
          if not img.mode == 'RGB':
              log_buff += '|trans: mode RGB\n'
              img = img.convert('RGB')

        # transform
        if self.opt.grayscale:
            log_buff += '|trans: mode L\n' # me lol
            img = img.convert('L')
        if self.opt._rescale:
            log_buff += f'|trans: resize to {self.opt._get_newsize}\n'
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
        mylog(f'{log_buff}\\write: {p}: took {elapsed}')
        mylog(f'Save img: {p.name}', progress=True)
        return p

    def _resize_img(self, img:Image.Image) -> Image.Image:
        width, height = img.size
        newsize = self.opt._get_newsize
        # preserve aspect ratio for landscape images
        if width > height:
            newsize = newsize[::-1]
        n_width, n_height = newsize
        # downscaling
        if (width>n_width) and (height>n_height) and not self.opt.nodownscale:
            img = img.resize((newsize), self.opt.resamplemethod)
        # upscaling
        elif not self.opt.noupscale:
            img = img.resize((newsize), self.opt.resamplemethod)
        return img
