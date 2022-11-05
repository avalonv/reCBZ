#!/usr/bin/python3
# -*- coding: utf-8 -*-
from sys import argv, exit
import time
import os
from zipfile import ZipFile, ZIP_DEFLATED
from multiprocessing import Pool
from tempfile import TemporaryDirectory
from functools import partial
from shutil import get_terminal_size
try:
    from PIL import Image
except ModuleNotFoundError:
    print("Please install Pillow!\nrun 'pip3 install pillow'")
    exit(1)

# TODO:
# may prove useful for determing format of the images in the archive, although
# its too new (python 3.11) at the moment:
# https://docs.python.org/3/library/zipfile.html#zipfile.Path.suffixes
# consider replacing os.path with pathlib, as it might be simpler:
# https://docs.python.org/3/library/pathlib.html#correspondence-to-tools-in-the-os-module

# limit output message width. ignored if verbose
TERM_COLUMNS, TERM_LINES = get_terminal_size()
assert TERM_COLUMNS > 0 and TERM_LINES > 0, "can't determine terminal size"
if TERM_COLUMNS > 120: max_width = 120
elif TERM_COLUMNS < 30: max_width= 30
else: max_width = TERM_COLUMNS - 2


class LossyFmt():
    lossless:bool = False
    quality:int = 80


class LosslessFmt():
    lossless:bool = True
    quality:int = 100


class Jpeg(LossyFmt):
    name:str = 'jpeg'
    ext:tuple = '.jpeg', '.jpg'
    desc:str = 'JPEG'

    @classmethod
    def save(cls, img:Image.Image, dest):
        img.save(dest, optimize=True, quality=cls.quality)


class WebpLossy(LossyFmt):
    # conclusions: optmize appears to have no effect. method >4 has a very mild
    # effect (~1% reduction with 800MB jpeg source), but takes twice as long
    name:str = 'webp'
    ext:tuple = '.webp',
    desc:str = 'WebP'

    @classmethod
    def save(cls, img:Image.Image, dest):
        img.save(dest, lossless=cls.lossless, method=5, quality=cls.quality)


class WebpLossless(LosslessFmt):
    name:str = 'webpll'
    ext:tuple = '.webp',
    desc:str = 'WebP Lossless'

    @classmethod
    def save(cls, img:Image.Image, dest):
        # for some reason 'quality' is akin to Png compress_level when lossless
        img.save(dest, lossless=cls.lossless, method=4, quality=100)


class Png(LosslessFmt):
    name:str = 'png'
    ext:tuple = '.png',
    desc:str = 'PNG'

    @classmethod
    def save(cls, img:Image.Image, dest):
        img.save(dest, optimize=True, compress_level=9)


class Config():
    def __init__(self):
        # General options:
        # ---------------------------------------------------------------------
        # whether to overwrite the original archive. dangerous
        self.overwrite:bool = False
        # ignore errors when overwrite is true. very dangerous
        self.force:bool = False
        # level of logging. 0 = quiet. 1 = overlapping progress report.
        # 2 = streaming progress report. 3 = verbose messages. >3 = everything
        self.loglevel:int = 1
        # whether to enable multiprocessing. fast, uses lots of memory
        self.parallel:bool = True
        # number of processes to spawn
        self.processes:int = 16
        # this only affects the extension name. will always be a zip archive
        self.zipext:str = '.cbz'
        # compresslevel for the archive. barely affects file size (images are
        # already compressed), but negatively impacts performance
        self.compresslevel:int = 0
        # number of images to sample in compare
        self.comparesamples:int = 10
        # dry run. archive won't be saved, even if overwrite is used
        self.dry:bool = False
        # TODO finish implementings this
        # list of formats to exclude from auto and assist
        self.blacklistedfmts:tuple = (WebpLossless, WebpLossy)

        # Options which affect image quality and/or file size:
        # ---------------------------------------------------------------------
        # default format to convert images to. leave empty to preserve original
        self.formatname:str = ''
        # compression quality for lossy images
        self.quality:int = 80
        # new image width / height. set to 0 to preserve original dimensions
        self.resolution:str = "0x0"
        # set to True to not upscale images smaller than newsize
        self.noupscale:bool = False
        # whether to convert images to grayscale
        self.grayscale:bool = False
        # LANCZOS sacrifices performance for optimal upscale quality
        self.resamplemethod = Image.Resampling.LANCZOS


    @property
    def get_targetformat(self):
        if self.formatname in (None, ''): return None
        elif self.formatname == 'jpeg': return Jpeg
        elif self.formatname == 'png': return Png
        elif self.formatname == 'webp': return WebpLossy
        elif self.formatname == 'webpll': return WebpLossless
        else: return None


    @property
    def get_newsize(self):
        default_value = (0,0)
        newsize = self.resolution.lower().strip()
        try:
            newsize = tuple(map(int,newsize.split('x')))
            assert len(newsize) == 2
            return newsize
        except (ValueError, AssertionError):
            return default_value


    @property
    def rescale(self) -> bool:
        if all(self.get_newsize):
            return True
        else:
            return False


class Archive():
    source_id:str = 'Source'


    def __init__(self, filename:str, config:Config):
        if os.path.isfile(filename): self.filename:str = filename
        else: raise ValueError(f"{filename}: invalid path")
        self.config:Config = config
        LossyFmt.quality = self.config.quality
        self.valid_formats:tuple = (Png, Jpeg, WebpLossy, WebpLossless)


    def analyze(self) -> tuple:
        self._log(f'Extracting: {self.filename}', progress=True)
        source_zip = ZipFile(self.filename)
        compressed_files = source_zip.namelist()

        # select x images from the middle of the archive, in increments of two
        sample_size = self.config.comparesamples
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
            # https://stackoverflow.com/a/3207973/8225672 absolutely nightmarish
            # but this is the only way to avoid problems with subfolders
            sample_imgs = [os.path.join(dpath,f) for (dpath, dnames, fnames)
                            in os.walk(tempdir) for f in fnames]
            nbytes = sum(os.path.getsize(f) for f in sample_imgs)
            sample_fmt = self._determine_format(Image.open(sample_imgs[0]))
            size_totals.append((nbytes,f'{sample_fmt.desc} ({Archive.source_id})'))

            # also compute the size of each valid format after converting
            for fmt in self.valid_formats:
                fmtdir = os.path.join(tempdir, fmt.name)
                os.mkdir(fmtdir)
                func = partial(self._transform_img, dest=fmtdir, forceformat=fmt)
                if self.config.parallel:
                    with Pool(processes=sample_size) as pool:
                        results = pool.map(func, sample_imgs)
                else:
                    results = map(func, sample_imgs)
                converted_imgs = [path for path in results if path]
                nbytes = sum(os.path.getsize(f) for f in converted_imgs)
                size_totals.append((nbytes,fmt.desc))

        # finally, compare
        # in multidepth lists, sorted compares the first element by default :)
        size_totals = tuple(sorted(size_totals))
        suggested_fmt = size_totals[0][1]
        summary = Archive._diff_summary_analyze(size_totals, sample_size)
        self._log(str(size_totals))
        self._log('', progress=True)
        return suggested_fmt, summary


    def repack(self) -> tuple:
        start_t = time.perf_counter()
        self._log(f'Extracting: {self.filename}', progress=True)
        source_zip = ZipFile(self.filename)
        source_size = os.path.getsize(self.filename)
        source_name = os.path.splitext(str(source_zip.filename))[0]
        # extract all
        with TemporaryDirectory() as tempdir:
            source_zip.extractall(tempdir)
            source_zip.close()
            source_imgs = [os.path.join(dpath,f) for (dpath, dnames, fnames)
                            in os.walk(tempdir) for f in fnames]

            # process images in place
            if self.config.parallel:
                with Pool(processes=self.config.processes) as pool:
                    results = pool.map(self._transform_img, source_imgs)
            else:
                results = map(self._transform_img, source_imgs)
            imgs_abspath = [path for path in results if path]
            imgs_names = [os.path.basename(f) for f in imgs_abspath] # not unecessary (I think)

            # sanity check
            discarded = len(source_imgs) - len(imgs_abspath)
            if discarded > 0:
                self._log('', progress=True)
                print(f"[!] {discarded} files had errors and had to be discarded.")
            if self.config.overwrite:
                if discarded and not self.config.force:
                    reply = input("■─■ Proceed with overwriting? [y/n]").lower()
                    if reply not in ('y', 'yes'):
                        print('[!] Aborting')
                        exit(1)
                new_name = self.filename
            else:
                new_name = f'{source_name} [reCBZ]{self.config.zipext}'

            if self.config.dry:
                end_t = time.perf_counter()
                elapsed = f'{end_t - start_t:.2f}s'
                return (self.filename, elapsed, 'Dry run')
            # write to new local archive
            if os.path.exists(new_name):
                self._log(f'{new_name} exists, removing...')
                os.remove(new_name)
            new_zip = ZipFile(new_name,'w')
            self._log(f'Write {self.config.zipext}: {new_name}', progress=True)
            for source, dest in zip(imgs_abspath, imgs_names):
                new_zip.write(source, dest, ZIP_DEFLATED, self.config.compresslevel)
            new_zip.close()
            new_size = os.path.getsize(new_name)
        end_t = time.perf_counter()
        elapsed = f'{end_t - start_t:.2f}s'
        diff = Archive._diff_summary_repack(source_size, new_size)
        self._log('', progress=True)
        return new_name, elapsed, diff


    def _transform_img(self, source:str, dest=None, forceformat=None): #-> None | Str:
        start_t = time.perf_counter()
        source_stem, source_ext = os.path.splitext(source)
        source_ext = source_ext.lower()
        # open
        try:
            self._log(f'Read file: {os.path.basename(source)}', progress=True)
            log_buff = f'/open:  {source}\n'
            img = Image.open(source)
        except IOError:
            self._log(f"{source}: can't open file as image, ignoring...'")
            return None

        # determine target format
        try:
            source_fmt = self._determine_format(img)
        except KeyError:
            self._log(f"{source}: invalid image format, ignoring...'")
            return None
        if forceformat:
            new_fmt = forceformat
        elif self.config.get_targetformat is not None:
            new_fmt = self.config.get_targetformat
        else:
            new_fmt = source_fmt

        # apply format specific actions
        if new_fmt is Jpeg:
          if not img.mode == 'RGB':
              log_buff += '|trans: mode RGB\n'
              img = img.convert('RGB')

        # transform
        if self.config.grayscale:
            log_buff += '|trans: mode L\n'
            img = img.convert('L')
        if self.config.rescale:
            log_buff += f'|trans: resize to {self.config.get_newsize}\n'
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
        self._log(f'Save file: {os.path.basename(path)}', progress=True)
        return path


    def _determine_format(self, img:Image.Image):
        PIL_fmt = img.format
        if PIL_fmt is None:
            raise KeyError(f"Image.format returned None")
        elif PIL_fmt == "PNG":
            return Png
        elif PIL_fmt == "JPEG":
            return Jpeg
        elif PIL_fmt == "WEBP":
            # it's possible to test but doesn't appear to be very reliable :(
            # https://github.com/python-pillow/Pillow/discussions/6716
            # with open(img.filename, "rb") as fp:
            #     if fp.read(15)[-1:] == b"L":
            #         return WebpLossless
            #     else:
            return WebpLossy
        else:
            raise KeyError(f"'{PIL_fmt}': invalid format")


    def _resize_img(self, img:Image.Image) -> Image.Image:
        width, height = img.size
        newsize = self.config.get_newsize
        # preserve aspect ratio for landscape images
        if width > height:
            newsize = newsize[::-1]
        n_width, n_height = newsize
        # downscaling
        if (width > n_width) and (height > n_height):
            img = img.resize((newsize), self.config.resamplemethod)
        # upscaling
        elif not self.config.noupscale:
            img = img.resize((newsize), self.config.resamplemethod)
        return img


    def _log(self, msg:str, progress=False) -> None:
        if self.config.loglevel == 0:
            return
        elif self.config.loglevel > 3:
            print(msg, flush=True)
        elif self.config.loglevel == 3 and not progress:
            print(msg, flush=True)
        elif self.config.loglevel == 2 and progress:
            msg = '[*] ' + msg
            msg = msg[:max_width]
            print(f'{msg: <{max_width}}', end='\r', flush=True)
        elif self.config.loglevel == 1 and progress:
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


def print_title() -> None:
    align = int(TERM_COLUMNS / 2) - 11
    if align > 21: align = 21
    if align + 22 > TERM_COLUMNS or align < 0:
        align = 0
    align = align * ' '
    title_multiline = (f"{align}┬─┐┌─┐┌─┐┌┐ ┌─┐ ┌─┐┬ ┬\n"
                       f"{align}├┬┘├┤ │  ├┴┐┌─┘ ├─┘└┬┘\n"
                       f"{align}┴└─└─┘└─┘└─┘└─┘o┴   ┴")
    print(title_multiline)


if __name__ == '__main__':
    import argparse
    mode = 0
    config = Config()
    parser = argparse.ArgumentParser(prog="reCBZ.py")
    mode_group = parser.add_mutually_exclusive_group()
    ext_group = parser.add_mutually_exclusive_group()
    log_group = parser.add_mutually_exclusive_group()
    process_group = parser.add_mutually_exclusive_group()
    parser.add_argument( "-t", "--test",
        default=config.dry,
        dest="dry",
        action="store_true",
        help="dry run, no changes are saved at the end (safe)")
    mode_group.add_argument( "-c", "--compare",
        const=2,
        dest="mode",
        action="store_const",
        help="test a small sample with all formats and print the results (safe)")
    mode_group.add_argument( "-a", "--assist",
        const=3,
        dest="mode",
        action="store_const",
        help="compare, then ask which format to use for a real run")
    mode_group.add_argument( "-A" ,"--auto",
        const=4,
        dest="mode",
        action="store_const",
        help="compare, then automatically pick the best format for a real run")
    ext_group.add_argument( "-O", "--overwrite",
        default=config.overwrite,
        dest="overwrite",
        action="store_true",
        help="overwrite the original archive")
    parser.add_argument( "-F", "--force",
        default=config.force,
        dest="force",
        action="store_true",
        help="ignore file errors when using overwrite (dangerous)")
    log_group.add_argument( "-v", "--verbose",
        default=config.loglevel,
        dest="loglevel",
        action="count",
        help="increase verbosity of progress messages, repeatable: -vvv")
    log_group.add_argument( "-s", "--silent",
        const=0,
        dest="loglevel",
        action="store_const",
        help="disable all progress messages")
    process_group.add_argument("--processes",
        default=config.processes,
        metavar="[1-32]",
        dest="processes",
        type=int,
        help="number of processes to spawn")
    process_group.add_argument( "--sequential",
        default=config.parallel,
        dest="parallel",
        action="store_false",
        help="disable multiprocessing")
    ext_group.add_argument( "--zipext",
        default=config.zipext,
        choices=('.cbz', '.zip'),
        metavar=".cbz/.zip",
        dest="zipext",
        type=str,
        help="extension to save the new archive with")
    parser.add_argument( "--zipcompress",
        default=config.compresslevel,
        metavar="[0-9]",
        dest="compresslevel",
        type=int,
        help="compression level for the archive. 0 (default) recommended")
    parser.add_argument( "--fmt",
        default=config.formatname,
        choices=('jpeg', 'png', 'webp', 'webpll'),
        metavar="fmt",
        dest="formatname",
        type=str,
        help="format to convert images to: jpeg, webp, webpll, or png")
    parser.add_argument( "--quality",
        default=config.quality,
        choices=(range(1,101)),
        metavar="[0-95]",
        dest="quality",
        type=int,
        help="save quality for lossy formats. >90 not recommended")
    parser.add_argument( "--size",
        metavar="WidthxHeight",
        default=config.resolution,
        dest="resolution",
        type=str,
        help="rescale images to the specified resolution")
    parser.add_argument( "-noup", "--noupscale",
        default=config.noupscale,
        dest="noupscale",
        action="store_true",
        help="disable upscaling with --size")
    parser.add_argument( "-bw", "--grayscale",
        default=config.grayscale,
        dest="grayscale",
        action="store_true",
        help="convert images to grayscale")
    args = parser.parse_args()
    # this is probably a not the most pythonic way to do this
    # I'm sorry guido-san...
    for key, val in args.__dict__.items():
        if key in config.__dict__.keys():
            setattr(config, key, val)
    print()
    print()
    print()
    print()
    print([f'{k} = {v}' for k, v in config.__dict__.items()])
    exit(1)

    if len(argv) > 1 and os.path.isfile(argv[1]):
        soloarchive = Archive(argv[1], config)
    else:
        print('BAD!!! >:(')
        exit(1)
    print_title()
    if len(argv) > 2 and argv[2] == '-a':
        results = soloarchive.analyze()
        print(results[1])
        print(f'Suggested format: {results[0]}')
    else:
        results = soloarchive.repack()
        print(f"┌─ '{results[0]}' completed in {results[1]}")
        print(f"└───■■ {results[2]} ■■")
