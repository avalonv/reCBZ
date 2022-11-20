import os
import argparse
import platform
import zipfile

import reCBZ
from reCBZ import wrappers, util
from reCBZ.config import Config


def print_title() -> None:
    align = int(Config.term_width() / 2) - 11
    if align > 21: align = 21
    if align + 22 > Config.term_width() or align < 0:
        align = 0
    align = align * ' '
    title_multiline = (f"{align}┬─┐┌─┐┌─┐┌┐ ┌─┐ ┌─┐┬ ┬\n"
                       f"{align}├┬┘├┤ │  ├┴┐┌─┘ ├─┘└┬┘\n"
                       f"{align}┴└─└─┘└─┘└─┘└─┘o┴   ┴")
    print(title_multiline)


def unix_like_glob(arglist:list) -> list:
    """What we're essentially trying to supplant here is powershell's obtuse
    Get-ChildItem 'pattern' | foreach {cmd $_.FullName}, because it's just
    ridiculous expecting users to memorize that when a simple asterisk could do
    the job. PS if you're using Windows this is a reminder your OS SUCKS ASS"""
    import glob

    new = []
    for arg in arglist:
        if '*' in arg:
            new.extend(glob.glob(str(arg)))
        else:
            new.append(arg)

    return new


def main():
    # o god who art in heaven please guard mine anime girls
    readme='https://github.com/avalonv/reCBZ/blob/master/README.md#usage'
    parser = argparse.ArgumentParser(
            prog=reCBZ.CMDNAME,
            usage="%(prog)s [options] files.cbz",
            epilog=f"for detailed documentation, see {readme}")
    mode_group = parser.add_mutually_exclusive_group()
    fmt_group = parser.add_mutually_exclusive_group()
    ext_group = parser.add_mutually_exclusive_group()
    log_group = parser.add_mutually_exclusive_group()
    process_group = parser.add_mutually_exclusive_group()
    # TODO clean leftover options
    parser.add_argument( "-nw", "--nowrite",
        default=Config.nowrite,
        dest="nowrite",
        action="store_true",
        help="dry run, no changes are saved at the end (safe)")
    ext_group.add_argument( "-O", "--overwrite",
        default=Config.overwrite,
        dest="overwrite",
        action="store_true",
        help="overwrite the original archive")
    parser.add_argument( "-F", "--force",
        default=Config.ignore,
        dest="ignore",
        action="store_true",
        help="ignore file errors when writing pages (dangerous)")
    log_group.add_argument( "-v", "--verbose",
        default=Config.loglevel,
        dest="loglevel",
        action="count",
        help="increase verbosity of progress messages, repeatable: -vvv")
    log_group.add_argument( "-s", "--silent",
        const=-1,
        dest="loglevel",
        action="store_const",
        help="disable all progress messages")
    # mode_group.add_argument( "-u", "--unpack",
    #     const='unpack',
    #     dest="mode",
    #     action="store_const",
    #     help="unpack the archive to the currect directory (safe)")
    mode_group.add_argument( "-c", "--compare",
        const='compare',
        dest="mode",
        action="store_const",
        help="calculate filesize when converting to each image format (safe)")
    mode_group.add_argument( "-a", "--assist",
        const='assist',
        dest="mode",
        action="store_const",
        help="compare, then ask which format to repack with")
    mode_group.add_argument( "-A" ,"--auto",
        const='auto',
        dest="mode",
        action="store_const",
        help="compare, then automatically pick the best format to repack with")
    mode_group.add_argument( "-J" ,"--join",
        const='join',
        dest="mode",
        action="store_const",
        help="append the contents of each file to the first/leftmost file")
    fmt_group.add_argument( "--nowebp",
        default=Config.blacklistedfmts,
        const=f'{Config.blacklistedfmts} webp webpll',
        dest="blacklistedfmts",
        action="store_const",
        help="exclude webp from --auto and --assist")
    ext_group.add_argument( "--epub",
        default=Config.outformat,
        const='epub',
        dest="outformat",
        action="store_const",
        help="save archive as epub")
    ext_group.add_argument( "--zip",
        default=Config.outformat,
        const='zip',
        dest="outformat",
        action="store_const",
        help="save archive as zip")
    ext_group.add_argument( "--cbz",
        default=Config.outformat,
        const='cbz',
        dest="outformat",
        action="store_const",
        help="save archive as cbz")
    parser.add_argument( "--noprev",
        default=False,
        dest="noprev",
        action="store_true",
        help="ignore previously repacked files")
    parser.add_argument( "--compress",
        default=Config.compresszip,
        dest="compresszip",
        action="store_true",
        help="attempt to further compress the archive when repacking")
    process_group.add_argument("--process",
        default=Config.processes,
        choices=(range(1,33)),
        metavar="1-32",
        dest="processes",
        type=int,
        help="maximum number of processes to spawn")
    process_group.add_argument( "--sequential",
        default=Config.parallel,
        dest="parallel",
        action="store_false",
        help="disable multiprocessing")
    fmt_group.add_argument( "--fmt",
        default=Config.imageformat,
        choices=('jpeg', 'png', 'webp', 'webpll'),
        metavar="format",
        dest="imageformat",
        type=str,
        help="format to convert pages to: jpeg, webp, webpll, or png")
    parser.add_argument( "--quality",
        default=Config.quality,
        choices=(range(1,101)),
        metavar="0-95",
        dest="quality",
        type=int,
        help="save quality for lossy formats. >90 not recommended")
    parser.add_argument( "--size",
        metavar="WidthxHeight",
        default=Config.resolution,
        dest="resolution",
        type=str,
        help="rescale images to the specified resolution")
    parser.add_argument( "--noup",
        default=Config.noupscale,
        dest="noupscale",
        action="store_true",
        help="disable upscaling with --size")
    parser.add_argument( "--nodown",
        default=Config.nodownscale,
        dest="nodownscale",
        action="store_true",
        help="disable downscaling with --size")
    parser.add_argument( "--bw",
        default=Config.grayscale,
        dest="grayscale",
        action="store_true",
        help="convert images to grayscale")
    parser.add_argument( "--config",
        dest="show_config",
        action="store_true",
        help="show current settings")
    parser.add_argument( "--version",
        dest="show_version",
        action="store_true",
        help="show version and exit")
    args, unknown_args = parser.parse_known_args()

    # this is probably not the most pythonic way to do this
    # I'm sorry guido-san...
    for key, val in args.__dict__.items():
        if key in Config.__dict__.keys():
            setattr(Config, key, val)
    if args.show_config:
        for key, val in Config.__dict__.items():
            print(f"{key} = {val}")
    if args.show_version:
        print(f'{reCBZ.CMDNAME} v{reCBZ.__version__}')
        exit(0)

    # parse files
    if platform.system() == 'Windows':
        unknown_args = unix_like_glob(unknown_args)
    paths = []
    for arg in unknown_args:
        if os.path.isfile(arg):
            paths.append(arg)
        elif os.path.isdir(arg):
            print(f'{reCBZ.CMDNAME}: {arg}: is a directory')
            parser.print_usage()
            exit(1)
        else:
            parser.print_help()
            print(f'\nunknown file or option: {arg}')
            exit(1)

    if len(paths) <= 0:
        print(f'{reCBZ.CMDNAME}: missing input file (see --help)')
        parser.print_usage()
        exit(1)

    if args.mode == 'join':
        if not len(paths) >= 2:
            print(f'{reCBZ.CMDNAME}: join: at least two files are needed')
            exit(1)

    if args.noprev:
        new = []
        for filename in paths:
            comment = zipfile.ZipFile(filename).comment
            if not comment == str.encode(Config.ZIPCOMMENT):
                new.append(filename)
        diff = len(paths) - len(new)
        if diff > 0:
            print(f'{reCBZ.CMDNAME}: noprev: ignoring {diff} files')
            if len(new) == 0:
                exit(1)
            else:
                paths = new

    # everything passed
    if reCBZ.SHOWTITLE: print_title()
    try:
        if args.mode == 'join':
            wrappers.join_fps(paths[0], paths[1:])
        for filename in paths:
                if args.mode is None:
                    wrappers.repack_fp(filename)
                elif args.mode == 'unpack':
                    wrappers.unpack_fp(filename)
                elif args.mode == 'compare':
                    wrappers.compare_fmts_fp(filename)
                elif args.mode == 'assist':
                    wrappers.assist_repack_fp(filename)
                elif args.mode == 'auto':
                    wrappers.auto_repack_fp(filename)
    except (KeyboardInterrupt, util.MPrunnerInterrupt):
        print('\nGoooooooooodbye')
        exit(1)


if __name__ == '__main__':
    # catching errors here won't work, presumably because of namespace mangling
    main()
