# -*- coding: utf-8 -*-
from sys import argv, exit
import time
import os
from zipfile import ZipFile, ZIP_DEFLATED
from multiprocessing import Pool
from tempfile import TemporaryDirectory
try:
    from PIL import Image
except ModuleNotFoundError:
    print("Please install Pillow!\nrun 'pip3 install pillow'")
    exit(1)

header = """                    ┬─┐┌─┐┌─┐┌┐ ┌─┐ ┌─┐┬ ┬
                    ├┬┘├┤ │  ├┴┐┌─┘ ├─┘└┬┘
                    ┴└─└─┘└─┘└─┘└─┘o┴   ┴"""


class Config():
    def __init__(self):
        # General options:
        # ---------------------------------------------------------------------
        # whether to enable multiprocessing. fast, uses lots of memory
        self.parallel:bool = True
        # number of processes to spawn
        self.pcount:int = 16
        # this only affects the extension name. will always be a zip archive
        self.zipextension:str = 'cbz'
        # debugging
        self.verbose:bool = False

        # Options which affect image quality and/or file size:
        # ---------------------------------------------------------------------
        # new image width / height. set to 0 to preserve original dimensions
        self.newsize:tuple = (1440,1920)
        # set to True to not upscale images smaller than newsize
        self.shrinkonly:bool = False
        # compression quality for images (not the archive). greatly affects
        # file size. values higher than 95% will increase file size
        self.quality:int = 80
        # compresslevel for the archive. barely affects file size (images are
        # already compressed) but has a significant impact on performance,
        # which persists when reading the archive, so 0 is strongly recommended
        self.compresslevel:int = 0
        # LANCZOS sacrifices performance for optmial upscale quality. doesn't
        # affect file size. less critical for downscaling, use BOX or
        # BILINEAR if performance is important
        self.resamplemethod = Image.Resampling.LANCZOS
        # whether to convert images to grayscale. moderate effect on file size
        # on full-color comics. useless on BW manga
        self.grayscale:bool = False
        # least to most space respectively: WEBP, JPEG, or PNG. WEBP uses the
        # least space but is not universally supported and may cause errors on
        # old devices, so JPEG is recommended. leave empty to preserve original
        self.newimgformat:str = 'jpeg'

        self.rescale:bool = False
        if all(self.newsize):
            self.rescale = True

class Archive():
    def __init__(self, filename:str, config:Config):
        self.filename = filename
        self.config = config


    def resize_img(self, img:Image.Image) -> Image.Image:
        width, height = img.size
        newsize = self.config.newsize
        # preserve aspect ratio for landscape images
        if width > height:
            newsize = newsize[::-1]
        n_width, n_height = newsize
        # downscaling
        if (width > n_width) and (height > n_height):
            img = img.resize((newsize), self.config.resamplemethod)
        # upscaling
        elif not self.config.shrinkonly:
            img = img.resize((newsize), self.config.resamplemethod)
        return img


    def transform_img(self, path:str) -> str:
        start_t = time.perf_counter()
        img = Image.open(path)
        if self.config.rescale:
            img = self.resize_img(img)
        if self.config.grayscale:
            img = img.convert('L')
        if not self.config.newimgformat == '':
            name = os.path.splitext(path)[0]
            path = f'{name}.{self.config.newimgformat}'
        img.save(path, optimize=True, quality=self.config.quality)
        end_t = time.perf_counter()
        self.log(f'{path}: completed in {end_t-start_t:.2f}')
        return path


    def repack_zip(self) -> tuple:
        start_t = time.perf_counter()
        source_zip = ZipFile(self.filename)
        source_zip_size = os.path.getsize(self.filename)
        source_zip_name = os.path.splitext(str(source_zip.filename))[0]
        with TemporaryDirectory() as tempdir:
            # extract images to temp storage
            source_zip.extractall(tempdir)
            source_zip.close()
            # https://stackoverflow.com/a/3207973/8225672 nightmarish...
            source_paths = [os.path.join(dpath,f) for (dpath, dnames, fnames)
                     in os.walk(tempdir) for f in fnames]

            # transform in place
            # if changing file format, paths will diverge from source_paths
            paths = []
            if self.config.parallel:
                with Pool(processes=self.config.pcount) as pool:
                    results = pool.map(self.transform_img, source_paths)
                    for path in results:
                        paths.append(path)
            else:
                for path in source_paths:
                    paths.append(self.transform_img(path))
            names = [os.path.basename(f) for f in paths]

            # write to new local archive
            zip_name = f'{source_zip_name} [reCBZ].{self.config.zipextension}'
            if os.path.exists(zip_name):
                os.remove(zip_name)
            new_zip = ZipFile(zip_name,'w')
            for source, dest in zip(paths, names):
                new_zip.write(source, dest, ZIP_DEFLATED, self.config.compresslevel)
            new_zip.close()
            zip_size = os.path.getsize(zip_name)

        end_t = time.perf_counter()
        elapsed = f'{end_t - start_t:.2f}s'
        diff = Archive.pretty_size_diff(source_zip_size, zip_size)
        return zip_name, elapsed, diff


    def log(self, text:str) -> None:
        if self.config.verbose:
            print(text)
        else:
            pass


    @classmethod
    def get_size_format(cls, b:float) -> str:
        # derived from https://github.com/x4nth055, MIT
        suffix = "B"
        factor = 1024
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if b < factor:
                return f"{b:.2f}{unit}{suffix}"
            b /= factor
        return f"{b:.2f}Y{suffix}"


    @classmethod
    def pretty_size_diff(cls, base:int, new:int) -> str:
        verb = 'decrease'
        if new > base:
            verb = 'increase'
        diff = new - base
        pct_diff = f"{diff / base * 100:.2f}%"
        basepretty = cls.get_size_format(base)
        newpretty = cls.get_size_format(new)
        return f"Original: {basepretty} ■ New: {newpretty} ■ {pct_diff} {verb}"



# class ArchiveList():
#     def __init__(self, )

if __name__ == '__main__':
    config = Config()
    if len(argv) > 1 and os.path.isfile(argv[1]):
        soloarchive = Archive(argv[1], config)
    else:
        print('BAD!!! >:(')
        exit(1)
    results = soloarchive.repack_zip()
    print(header)
    print(f"┌─ '{results[0]}' completed in {results[1]}")
    print(f"└───■■ {results[2]} ■■")
