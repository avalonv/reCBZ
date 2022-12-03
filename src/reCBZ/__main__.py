import os
import argparse
import platform
import zipfile
import re

import reCBZ
from reCBZ import wrappers, util
from reCBZ.config import Config
from reCBZ.profiles import profiles_list


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
    wiki='https://github.com/avalonv/reCBZ/wiki'
    parser = argparse.ArgumentParser(
            prog=reCBZ.CMDNAME,
            usage="%(prog)s [options] files.cbz",
            epilog=f"for detailed documentation, see {wiki}")
    mode_group = parser.add_mutually_exclusive_group()
    imgfmt_group = parser.add_mutually_exclusive_group()
    ext_group = parser.add_mutually_exclusive_group()
    log_group = parser.add_mutually_exclusive_group()
    process_group = parser.add_mutually_exclusive_group()
    # TODO clean leftover options
    parser.add_argument( "-nw", "--nowrite",
        default=None,
        dest="nowrite",
        action="store_true",
        help="dry run, no changes are saved at the end (safe)")
    ext_group.add_argument( "-O", "--overwrite",
        default=None,
        dest="overwrite",
        action="store_true",
        help="overwrite the original archive")
    parser.add_argument( "-F", "--force",
        default=None,
        dest="ignore",
        action="store_true",
        help="ignore file errors when writing pages (dangerous)")
    log_group.add_argument( "-v", "--verbose",
        default=None,
        dest="loglevel",
        action="count",
        help="increase verbosity of progress messages, repeatable: -vvv")
    log_group.add_argument( "-s", "--silent",
        default=None,
        const=-1,
        dest="loglevel",
        action="store_const",
        help="disable all progress messages")
    # mode_group.add_argument( "-u", "--unpack",
    #     default=None,
    #     const='unpack',
    #     dest="mode",
    #     action="store_const",
    #     help="unpack the archive to the currect directory (safe)")
    mode_group.add_argument( "-c", "--compare",
        default=None,
        const='compare',
        dest="mode",
        action="store_const",
        help=argparse.SUPPRESS)
    mode_group.add_argument( "-a", "--assist",
        default=None,
        const='assist',
        dest="mode",
        action="store_const",
        help="calculate size of each image format, then ask which to repack with")
    mode_group.add_argument( "-A" ,"--auto",
        default=None,
        const='auto',
        dest="mode",
        action="store_const",
        help="calculate size, then automatically pick the best one to repack with")
    mode_group.add_argument( "-J" ,"--join",
        default=None,
        const='join',
        dest="mode",
        action="store_const",
        help="append the contents of each file to the first/leftmost file")
    parser.add_argument( "-p", "--profile",
        default=None,
        metavar="",
        dest="profile",
        type=str,
        help="target device profile. run --profiles to see available options")
    parser.add_argument( "--profiles",
        default=False,
        dest="show_profiles",
        action='store_true',
        help=argparse.SUPPRESS)
    ext_group.add_argument( "--epub",
        default=None,
        const='epub',
        dest="bookformat",
        action="store_const",
        help="save archive as epub")
    ext_group.add_argument( "--zip",
        default=None,
        const='zip',
        dest="outformat",
        action="store_const",
        help="save archive as zip")
    ext_group.add_argument( "--cbz",
        default=None,
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
        default=None,
        dest="compresszip",
        action="store_true",
        help="attempt to further compress the archive when repacking")
    process_group.add_argument("--process",
        default=None,
        choices=(range(1,33)),
        metavar="1-32",
        dest="processes",
        type=int,
        help="maximum number of processes to spawn")
    process_group.add_argument( "--sequential",
        default=None,
        dest="parallel",
        action="store_false",
        help="disable multiprocessing")
    imgfmt_group.add_argument( "--imgfmt",
        default=None,
        choices=('jpeg', 'png', 'webp', 'webpll'),
        metavar="format",
        dest="imageformat",
        type=str,
        help="format to convert pages to: jpeg, webp, webpll, or png")
    parser.add_argument( "--quality",
        default=None,
        choices=(range(1,101)),
        metavar="0-95",
        dest="quality",
        type=int,
        help="save quality for lossy formats. >90 not recommended")
    parser.add_argument( "--size",
        default=None,
        metavar="WidthxHeight",
        dest="size_str",
        type=str,
        help="rescale images to the specified resolution")
    parser.add_argument( "--noup",
        default=None,
        dest="noupscale",
        action="store_true",
        help="disable upscaling with --size")
    parser.add_argument( "--nodown",
        default=None,
        dest="nodownscale",
        action="store_true",
        help="disable downscaling with --size")
    imgfmt_group.add_argument( "--nowebp",
        default=None,
        const=f'{Config.blacklistedfmts} webp webpll',
        dest="blacklistedfmts",
        action="store_const",
        help="exclude webp from --auto and --assist")
    parser.add_argument( "--bw",
        default=None,
        dest="grayscale",
        action="store_true",
        help="convert images to grayscale")
    parser.add_argument( "--color",
        default=None,
        dest="grayscale",
        action="store_false",
        help="force color when using --profile")
    parser.add_argument( "--config",
        default=None,
        dest="show_config",
        action="store_true",
        help="show current settings and exit")
    parser.add_argument( "--version",
        default=None,
        dest="show_version",
        action="store_true",
        help="show version and exit")
    args, unknown_args = parser.parse_known_args()

    # set profile first, ensure it can be overriden by explicit options
    if args.profile is not None:
        prof_name = args.profile.upper()
        try:
            Config.set_profile(prof_name)
        except KeyError:
            print(f'{reCBZ.CMDNAME}: profile: invalid option "{prof_name}"')
            exit(1)

    if args.size_str is not None:
        newsize = args.size_str.lower().strip()
        try:
            newsize = tuple(map(int,newsize.split('x')))
            assert len(newsize) == 2
            Config.size = newsize
        except (ValueError, AssertionError):
            print(f'{reCBZ.CMDNAME}: size: invalid option "{args.size_str}"')
            exit(1)

    # this is probably not the most pythonic way to do this
    # I'm sorry guido-san...
    for key, val in args.__dict__.items():
        if key in Config.__dict__.keys() and val is not None:
            setattr(Config, key, val)

    if args.show_config:
        private = re.compile('classmethod|^_')
        for key, val in Config.__dict__.items():
            if not private.search(str(key)) and not private.search(str(val)):
                print(f"{key} = {val}")
        exit(0)

    if args.show_version:
        print(f'{reCBZ.CMDNAME} v{reCBZ.__version__}')
        exit(0)

    if args.show_profiles:
        print(f'{reCBZ.CMDNAME} -p ...')
        for prof in profiles_list:
            print(prof.nickname, '=', prof.desc)
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
