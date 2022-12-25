import re
import tempfile
from pathlib import Path
from uuid import uuid4

__version__ = "0.7.5"
CMDNAME = 'recbz'

MODULE_PATH = Path(__file__).resolve().parent

# whether to print the 'recbz.py' title at the beginning
SHOWTITLE = True

# global UUID for files stored in temp, so we can ensure multiple instances
# created under the same process don't delete cache currently used by another
CACHE_PREFIX:str = f'reCBZCACHE_'
GLOBAL_CACHEDIR = Path(tempfile.gettempdir()) / f'{CACHE_PREFIX}{str(uuid4().hex)}'
if not GLOBAL_CACHEDIR.exists():
    GLOBAL_CACHEDIR.mkdir()

IMG_FILES = re.compile('^.*\\.(?!png\\b|webp\\b|jpg\\b|jpeg\\b)\\w*$')
EPUB_FILES = re.compile('^.*(calibre_bookmarks.txt)$|^.*(mimetype)$|.*\\.(?=css\\b|opf\\b|ncx\\b|xhtml\\b|xml\\b)\\w*$')
KEPUB_EPUB = re.compile('^.*(?=\\.kepub\\.epub$)')
