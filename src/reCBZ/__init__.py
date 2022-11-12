from importlib import resources
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

__version__ = "0.3.0"
CMDNAME = 'recbz'

_cfg = tomllib.loads(resources.read_text("reCBZ", "config.toml"))
OVERWRITE = _cfg["archive"]["overwrite"]
FORCE = _cfg["archive"]["force"]
LOGLEVEL = _cfg["archive"]["loglevel"]
PARALLEL = _cfg["archive"]["parallel"]
PROCESSES = _cfg["archive"]["processes"]
ZIPEXT = _cfg["archive"]["zipext"]
COMPRESSLEVEL = _cfg["archive"]["compresslevel"]
COMPARESAMPLES = _cfg["archive"]["comparesamples"]
NOWRITE = _cfg["archive"]["nowrite"]
BLACKLISTEDFMTS = _cfg["archive"]["blacklistedfmts"]
FORMATNAME = _cfg["archive"]["formatname"]
QUALITY = _cfg["archive"]["quality"]
RESOLUTION = _cfg["archive"]["resolution"]
NOUPSCALE = _cfg["archive"]["noupscale"]
NODOWNSCALE = _cfg["archive"]["nodownscale"]
GRAYSCALE = _cfg["archive"]["grayscale"]
SHOWTITLE = _cfg["archive"]["showtitle"]
