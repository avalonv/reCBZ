from PIL import Image
from reCBZ.config import Config


class LossyFmt():
    lossless:bool = False
    quality:int = Config.quality


class LosslessFmt():
    lossless:bool = True
    quality:int = 100


class Jpeg(LossyFmt):
    name:str = 'jpeg'
    ext:tuple = '.jpeg', '.jpg'
    desc:str = 'JPEG'
    mime:str = 'image/jpeg'

    @classmethod
    def save(cls, img:Image.Image, dest):
        img.save(dest, format='JPEG', optimize=True, quality=cls.quality)


class WebpLossy(LossyFmt):
    # conclusions: optmize appears to have no effect. method >4 has a very mild
    # effect (~1% reduction with 800MB jpeg source), but takes twice as long
    name:str = 'webp'
    ext:tuple = '.webp',
    desc:str = 'WebP'
    mime:str = 'image/webp'

    @classmethod
    def save(cls, img:Image.Image, dest):
        img.save(dest, fomrat='WEBP', lossless=cls.lossless, method=5, quality=cls.quality)


class WebpLossless(LosslessFmt):
    name:str = 'webpll'
    ext:tuple = '.webp',
    desc:str = 'WebP Lossless'
    mime:str = 'image/webp'

    @classmethod
    def save(cls, img:Image.Image, dest):
        # for some reason 'quality' is akin to Png compress_level when lossless
        img.save(dest, format='WEBP', lossless=cls.lossless, method=4, quality=100)


class Png(LosslessFmt):
    name:str = 'png'
    ext:tuple = '.png',
    desc:str = 'PNG'
    mime:str = 'image/png'

    @classmethod
    def save(cls, img:Image.Image, dest):
        img.save(dest, format='PNG', optimize=True, compress_level=9)
