#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import tempfile
import shutil
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, BadZipFile
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from functools import partial
from pathlib import Path

from PIL import Image

import reCBZ
from reCBZ.formats import *
from reCBZ.config import Config
from reCBZ.util import mylog, MP_run_tasks, SIGNINT_ctrl_c

# TODO:
# include docstrings


class Archive():
    source_id:str = 'Source'
    new_id:str = ' [reCBZ]'
    temp_prefix:str = f'reCBZCACHE_'

    def __init__(self, filename:str):
        mylog('Archive: __init__')
        if Path(filename).exists():
            self.source_path:Path = Path(filename)
        else:
            raise ValueError(f"{filename}: invalid path")
        self.source_stem = self.source_path.stem
        self.opt_parallel = Config.parallel
        self.opt_ignore = Config.ignore
        self._zip_compress = Config.compresszip
        self._fmt_blacklist = Config.blacklistedfmts
        self._convert_samples = Config.samplescount
        self._convert_format = Config.imageformat
        self._convert_quality = Config.quality
        self._convert_size = Config.resolution
        self._convert_bw = Config.grayscale
        self._convert_noup = Config.noupscale
        self._convert_nodown = Config.nodownscale
        self._convert_filter = Config.resamplemethod
        self._pages:list = []
        self.tempdir:Path = Path('.')

    def fetch_pages(self):
        """Fetches extracted files from cache if it exists, otherwise extracts
        them first."""
        if len(self._pages) == 0:
            self._pages = list(self.extract())
        return self._pages

    def extract(self, count:int=0) -> tuple:
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
        if count == 0: # we extracted the whole thing, update pages
            self._pages = extracted
        mylog('', progress=True)
        return tuple(extracted)

    def pack_archive(self, bookformat='cbz', dest='') -> str:
        if bookformat in ('cbz', 'zip'):
            if dest != '':
                new_path = Path.joinpath(Path(dest),
                                         Path(f'{self.source_path}.{bookformat}'))
            else:
                new_path = Path(f'{self.source_stem}{Archive.new_id}.{bookformat}')
            if new_path.exists():
                mylog(f'Write .{bookformat}: {new_path}', progress=True)
                mylog(f'{new_path} exists, removing...')
                new_path.unlink()
            new_zip = ZipFile(new_path,'w')
            for source in self.fetch_pages():
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
            return str(new_path)

        elif bookformat == 'epub':
            from reCBZ.epub import single_volume_epub
            title = self.source_stem
            mylog(f'Write .epub: {title}.epub', progress=True)
            new_path = single_volume_epub(title, self.fetch_pages())
            return new_path

        elif bookformat == 'mobi':
            # unimplemented
            return ''

        else:
            raise ValueError(f"Invalid format '{bookformat}'")

    def convert_pages(self, format, quality=None, grayscale=None, size=None) -> tuple:
        if quality is not None: self._convert_quality = int(quality)
        if grayscale is not None: self._convert_bw = bool(grayscale)
        if size is not None: self._convert_size = size
        source_imgs = self.fetch_pages()
        if self.opt_parallel:
            results = MP_run_tasks(self._transform_img, source_imgs)
        else:
            results = map(self._transform_img, source_imgs)
        self._pages = [path for path in results if path]
        return tuple(self._pages)

    def compute_fmt_sizes(self) -> tuple:
        # TODO add convert_images method which will supplant most of this.
        # then we can call convert_images with ThreadPool :)
        def compute_fmt(sample_imgs, tempdir, fmt) -> tuple:
            fmtdir = Path.joinpath(tempdir, fmt.name)
            Path.mkdir(fmtdir)
            pfunc = partial(self._transform_img, dest=fmtdir, forceformat=fmt)
            if self.opt_parallel:
                results = MP_run_tasks(pfunc, sample_imgs)
            else:
                results = map(pfunc, sample_imgs)
            converted_imgs = [path for path in results if path]
            nbytes = sum(Path(f).stat().st_size for f in converted_imgs)
            return nbytes, fmt.desc, fmt.name

        # extract images and compute their original size
        # these aren't saved to cache
        source_imgs = self.extract(count=self._convert_samples)
        nbytes = sum(Path(f).stat().st_size for f in source_imgs)
        source_fmt = determine_format(Image.open(source_imgs[0]))
        source_fsize = [nbytes, f'{Archive.source_id} ({source_fmt.desc})',
                        source_fmt.name]
        # also compute the size of each valid format after converting
        fmt_fsizes = []
        pfunc = partial(compute_fmt, source_imgs, self.tempdir)
        if self.opt_parallel:
            with ThreadPool(processes=len(self._img_validformats)) as Tpool:
                fmt_fsizes.extend(Tpool.map(pfunc, self._img_validformats))
        else:
            fmt_fsizes.extend(map(pfunc, self._img_validformats))

        # finally, compare
        # in multidepth lists, sorted compares the first element by default :)
        sorted_fmts = list(sorted(fmt_fsizes))
        sorted_fmts.insert(0, source_fsize)
        mylog(str(sorted_fmts))
        mylog('', progress=True)
        return tuple(sorted_fmts)

    @SIGNINT_ctrl_c
    def _transform_img(self, source:Path, dest=None, forceformat=None): #-> None | Str:
        # open
        start_t = time.perf_counter()
        try:
            mylog(f'Read img: {source.name}', progress=True)
            log_buff = f'/open:  {source}\n'
            img = Image.open(source)
        except IOError as err:
            if self.opt_ignore:
                mylog(f"{source}: can't open file as image, ignoring...'")
                return None
            else:
                raise err

        # determine target format
        try:
            source_fmt = determine_format(img)
        except KeyError as err:
            if self.opt_ignore:
                mylog(f"{source}: invalid image format, ignoring...'")
                return None
            else:
                raise err
        if forceformat:
            new_fmt = forceformat
        elif self._img_formatclass is not None:
            new_fmt = self._img_formatclass
        else:
            new_fmt = source_fmt

        # apply format specific actions
        if new_fmt is Jpeg:
          if not img.mode == 'RGB':
              log_buff += '|trans: mode RGB\n'
              img = img.convert('RGB')

        # transform
        if self._convert_bw:
            log_buff += '|trans: mode L\n' # me lol
            img = img.convert('L')
        if all(self._img_newsize):
            log_buff += f'|trans: resize to {self._img_newsize}\n'
            width, height = img.size
            newsize = self._img_newsize
            # preserve aspect ratio for landscape images
            if width > height:
                newsize = newsize[::-1]
            n_width, n_height = newsize
            # downscaling
            if (width > n_width and height > n_height
                and not self._convert_nodown):
                img = img.resize((newsize), self._convert_filter)
            # upscaling
            elif not self._convert_noup:
                    img = img.resize((newsize), self._convert_filter)

        # save
        ext:str = new_fmt.ext[0]
        if dest:
            fp = Path.joinpath(dest, f'{source.stem}{ext}')
        else:
            fp = Path.joinpath(source.parents[0], f'{source.stem}{ext}')
        log_buff += f'|trans: {source_fmt.name} -> {new_fmt.name}\n'
        new_fmt.save(img, fp)
        end_t = time.perf_counter()
        elapsed = f'{end_t-start_t:.2f}s'
        mylog(f'{log_buff}\\write: {fp}: took {elapsed}')
        mylog(f'Save img: {fp.name}', progress=True)
        return fp

    @property
    def _img_formatclass(self):
        if self._convert_format in (None, ''): return None
        elif self._convert_format == 'jpeg': return Jpeg
        elif self._convert_format == 'png': return Png
        elif self._convert_format == 'webp': return WebpLossy
        elif self._convert_format == 'webpll': return WebpLossless
        else: return None

    @property
    def _img_validformats(self) -> tuple:
        LossyFmt.quality = self._convert_quality
        all_fmts = (Png, Jpeg, WebpLossy, WebpLossless)
        try:
            blacklist = self._fmt_blacklist.lower().split(' ')
        except AttributeError: # blacklist is None
            return all_fmts
        valid_fmts = tuple(fmt for fmt in all_fmts if fmt.name not in blacklist)
        assert len(valid_fmts) >= 1, "valid_formats is 0"
        return valid_fmts

    @property
    def _img_newsize(self) -> tuple:
        default_value = (0,0)
        newsize = self._convert_size.lower().strip()
        try:
            newsize = tuple(map(int,newsize.split('x')))
            assert len(newsize) == 2
            return newsize
        except (ValueError, AssertionError):
            return default_value
