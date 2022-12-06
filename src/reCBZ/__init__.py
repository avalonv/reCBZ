import re
from uuid import uuid4

__version__ = "0.7.3"
CMDNAME = 'recbz'

# whether to print the 'recbz.py' title at the beginning
SHOWTITLE = True

# global UUID for files stored in temp, so we can ensure multiple instances
# created under the same process don't delete cache currently used by another
TEMPUUID = str(uuid4().hex)

IMG_FILES = re.compile('^.*\\.(?!png\\b|webp\\b|jpg\\b|jpeg\\b)\\w*$')
EPUB_FILES = re.compile('^.*(calibre_bookmarks.txt)$|^.*(mimetype)$|.*\\.(?=css\\b|opf\\b|ncx\\b|xhtml\\b|xml\\b)\\w*$')
KEPUB_EPUB = re.compile('^.*(?=\\.kepub\\.epub$)')
