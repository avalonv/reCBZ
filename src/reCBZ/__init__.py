from importlib import resources
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

__version__ = "0.5.0"
CMDNAME = 'recbz'

_cfg = tomllib.loads(resources.read_text("reCBZ", "defaults.toml"))
OVERWRITE = _cfg["archive"]["overwrite"]
IGNORE = _cfg["archive"]["ignore"]
LOGLEVEL = _cfg["archive"]["loglevel"]
PARALLEL = _cfg["archive"]["parallel"]
PROCESSES = _cfg["archive"]["processes"]
OUTFORMAT = _cfg["archive"]["outformat"]
COMPRESSZIP = _cfg["archive"]["compresszip"]
SAMPLECOUNT = _cfg["archive"]["samplecount"]
NOWRITE = _cfg["archive"]["nowrite"]
BLACKLISTEDFMTS = _cfg["archive"]["blacklistedfmts"]
IMAGEFORMAT = _cfg["archive"]["imageformat"]
QUALITY = _cfg["archive"]["quality"]
RESOLUTION = _cfg["archive"]["resolution"]
NOUPSCALE = _cfg["archive"]["noupscale"]
NODOWNSCALE = _cfg["archive"]["nodownscale"]
GRAYSCALE = _cfg["archive"]["grayscale"]
SHOWTITLE = _cfg["archive"]["showtitle"]
