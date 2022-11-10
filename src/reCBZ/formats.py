from PIL import Image
import reCBZ


class LossyFmt():
    lossless:bool = False
    quality:int = reCBZ.QUALITY


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


def determine_format(img:Image.Image):
    PIL_fmt = img.format
    if PIL_fmt is None:
        raise KeyError(f"Image.format returned None")
    elif PIL_fmt == "PNG":
        return Png
    elif PIL_fmt == "JPEG":
        return Jpeg
    elif PIL_fmt == "WEBP":
        # https://github.com/python-pillow/Pillow/discussions/6716
        with open(img.filename, "rb") as fp:
            if fp.read(16)[-1:] == b"L":
                return WebpLossless
            else:
                return WebpLossy
    else:
        raise KeyError(f"'{PIL_fmt}': invalid format")
