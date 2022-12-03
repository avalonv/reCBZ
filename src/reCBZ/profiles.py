class Kobo:
    prefer_epub = False
    epub_ext = '.kepub.epub'
    epub_properties = (
        (None, 'meta', 'portrait', {'property': 'rendition:spread'}),
        (None, 'meta', 'portrait', {'property': 'rendition:orientation'}),
        (None, 'meta', 'pre-paginated', {'property': 'rendition:layout'}))
    # epub_properties = '''
    # <meta property="rendition:spread">portrait</meta>
    # <meta property="rendition:orientation">portrait</meta>
    # <meta property="rendition:layout">pre-paginated</meta>'''


class Kindle:
    prefer_epub = True
    epub_ext = '.epub'
    epub_properties = (
        (None, 'meta', '', {'name': 'fixed-layout', 'content': 'true'}),
        (None, 'meta', '', {'name': 'book-type', 'content': 'comic'}),
        (None, 'meta', '', {'name': 'primary-writing-mode', 'content': 'horizontal-lr'}),
        (None, 'meta', '', {'name': 'zero-gutter', 'content': 'true'}),
        (None, 'meta', '', {'name': 'zero-margin', 'content': 'true'}),
        (None, 'meta', '', {'name': 'ke-border-color', 'content': '#FFFFFF'}),
        (None, 'meta', '', {'name': 'ke-border-width', 'content': '0'}),
        (None, 'meta', '', {'name': 'orientation-lock', 'content': 'portrait'}),
        (None, 'meta', '', {'name': 'region-mag', 'content': 'true'}))
    # epub_properties = '''
    # <meta name="fixed-layout" content="true"/>
    # <meta name="book-type" content="comic"/>
    # <meta name="primary-writing-mode" content="horizontal-lr"/>
    # <meta name="zero-gutter" content="true"/>
    # <meta name="zero-margin" content="true"/>
    # <meta name="ke-border-color" content="#FFFFFF"/>
    # <meta name="ke-border-width" content="0"/>
    # <meta name="orientation-lock" content="portrait"/>
    # <meta name="region-mag" content="true"/>'''


class KoboForma(Kobo):
    nickname = 'KOF'
    desc = 'Kobo Forma/Sage'
    size = (1440, 1920)
    gray = True


class KoboLibra(Kobo):
    nickname = 'KOL'
    desc = 'Kobo Libra 1/2'
    size = (1264, 1680)
    gray = True


class KoboElipsa(Kobo):
    nickname = 'KOE'
    desc = 'Kobo Elipsa/Aura One'
    size = (1404, 1872)
    gray = True


class KoboClaraHD(Kobo): # moi
    nickname = 'KOC'
    desc = 'Kobo Clara HD/2E'
    size = (1072, 1448)
    gray = True


class KoboNia(Kobo):
    nickname = 'KON'
    desc = 'Kobo Nia'
    size = (758, 1024)
    gray = True


class Kindle68(Kindle):
    nickname = 'PW5'
    desc = 'Kindle Paperwhite (11th gen)'
    size = (1246, 1648)
    gray = True


class Kindle300(Kindle):
    nickname = 'PW3'
    desc = 'Kindle Paperwhite (7-10th gen)/Basic (10th gen)'
    size = (1072, 1448)
    gray = True


class Kindle212(Kindle):
    nickname = 'PW2'
    desc = 'Kindle Paperwhite (5-6th gen)'
    size = (758, 1024)
    gray = True


class Kindle167(Kindle):
    nickname = 'KT2'
    desc = 'Kindle Basic (7-8th gen)'
    size = (600, 800)
    gray = True


class KindleOasis(Kindle):
    nickname = 'KOA'
    desc = 'Kindle Oasis'
    size = (1264, 1680)
    gray = True


class KindleVoyage(Kindle):
    nickname = 'KVO'
    desc = 'Kindle Voyage'
    size = (1080, 1440)
    gray = True


profiles_list = (KoboForma, KoboLibra, KoboElipsa, KoboClaraHD, Kindle68,
                 Kindle300, Kindle212, Kindle167, KindleOasis, KindleVoyage)
