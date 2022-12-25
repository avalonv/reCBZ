import argparse
import platform
import zipfile
import re
import sys
import shutil
from pathlib import Path

import reCBZ
import reCBZ.config as config
from reCBZ import wrappers, util
from reCBZ.profiles import ProfileDict


def print_title() -> None:
    align = int(config.term_width() / 2) - 11
    if align > 21: align = 21
    if align + 22 > config.term_width() or align < 0:
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
    mutually_exclusive_groups = []
    wiki='https://github.com/avalonv/reCBZ/wiki'
    desc='''accepted formats: .zip, .epub, .cbz. repacks to .cbz by default'''
    parser = argparse.ArgumentParser(
            prog=reCBZ.CMDNAME,
            usage="%(prog)s [options] files",
            description=desc,
            epilog=f"for detailed documentation, see {wiki}",)

    parser.add_argument( "-v", "--verbose", # log_group
        default=None,
        dest="loglevel",
        action="count",
        help="increase verbosity of messages, repeatable: -vv")
    parser.add_argument( "-s", "--silent", # log_group
        default=None,
        const=-1,
        dest="loglevel",
        action="store_const",
        help="disable progress messages")
    parser.add_argument( "-d", "--dry",
        default=None,
        dest="no_write",
        action="store_true",
        help="dry run, no changes are saved at the end (safe)")
    parser.add_argument( "-O", "--overwrite",
        default=None,
        dest="overwrite",
        action="store_true",
        help="overwrite the original archive")
    parser.add_argument( "-F", "--force",
        default=None,
        dest="force_write",
        action="store_true",
        help="write archive even if there are page errors (dangerous)")
    # parser.add_argument( "-u", "--unpack", # mode_group
    #     default=None,
    #     const='unpack',
    #     dest="mode",
    #     action="store_const",
    #     help="unpack the archive to the current directory (safe)")
    parser.add_argument( "--compare", # mode_group
        default=None,
        const='compare',
        dest="mode",
        action="store_const",
        help=argparse.SUPPRESS)
    parser.add_argument( "-a", "--assist", # mode_group
        default=None,
        const='assist',
        dest="mode",
        action="store_const",
        help="calculate size for each image format, ask which to use")
    parser.add_argument( "-A" ,"--auto", # mode_group
        default=None,
        const='auto',
        dest="mode",
        action="store_const",
        help="calculate size for each image format, pick smallest one")
    parser.add_argument( "-J" ,"--join", # mode_group
        default=None,
        const='join',
        dest="mode",
        action="store_const",
        help="append the contents of each file to the leftmost file")
    parser.add_argument( "--noprev",
        default=False,
        dest="noprev",
        action="store_true",
        help="ignore previously repacked files")
    log_group = ('verbose', 'silent')
    mutually_exclusive_groups.append(log_group)
    mode_group = ('compare', 'assist', 'a', 'auto', 'A', 'join', 'J')
    mutually_exclusive_groups.append(mode_group)

    archive_group = parser.add_argument_group(title="archive options")
    archive_group.add_argument( "-p", "--profile",
        default=None,
        # best to handle it externally as we always convert to upper case
        # choices=([prof.nickname for prof in profiles_list]),
        metavar="",
        dest="profile",
        type=str,
        help="target eReader profile. run --profiles to see options")
    archive_group.add_argument( "--profiles",
        default=False,
        dest="show_profiles",
        action='store_true',
        help=argparse.SUPPRESS)
    archive_group.add_argument( "--epub", # ext_group
        default=None,
        const='epub',
        dest="archive_format",
        action="store_const",
        help="save archive as epub")
    archive_group.add_argument( "--zip", # ext_group
        default=None,
        const='zip',
        dest="archive_format",
        action="store_const",
        help="save archive as zip")
    archive_group.add_argument( "--cbz", # ext_group
        default=None,
        const='cbz',
        dest="archive_format",
        action="store_const",
        help="save archive as cbz")
    archive_group.add_argument( "--compress",
        default=None,
        dest="compress_zip",
        action="store_true",
        help="attempt to further compress the archive when repacking")
    archive_group.add_argument( "--rtl",
        default=None,
        dest="right_to_left",
        action="store_true",
        help="sort pages from right to left. only affects epub")
    ext_group = ('epub', 'zip', 'cbz')
    mutually_exclusive_groups.append(ext_group)

    images_group = parser.add_argument_group(title="image options")
    images_group.add_argument( "-c", "--convert",
        default=None,
        choices=('jpeg', 'png', 'webp', 'webpll'),
        metavar="",
        dest="img_format",
        type=str,
        help="format to convert pages to: jpeg, webp, webpll, or png")
    images_group.add_argument( "--imgfmt", # deprecated
        default=None,
        choices=('jpeg', 'png', 'webp', 'webpll'),
        metavar="",
        dest="img_format",
        type=str,
        help=argparse.SUPPRESS)
    images_group.add_argument( "--quality",
        default=None,
        choices=(range(1,101)),
        metavar="0-95",
        dest="img_quality",
        type=int,
        help="save quality for lossy formats. >90 not recommended")
    images_group.add_argument( "--size",
        default=None,
        metavar="WidthxHeight",
        dest="size_str",
        type=str,
        help="rescale images to the specified resolution")
    images_group.add_argument( "--noup", # rescale_group
        default=None,
        dest="no_upscale",
        action="store_true",
        help="disable upscaling with --size")
    images_group.add_argument( "--nodown", # rescale_group
        default=None,
        dest="no_downscale",
        action="store_true",
        help="disable downscaling with --size")
    images_group.add_argument( "--nowebp",
        default=None,
        const=f'{config.blacklisted_fmts} webp webpll',
        dest="blacklisted_fmts",
        action="store_const",
        help="exclude webp from --auto and --assist")
    images_group.add_argument( "--bw", # color_group
        default=None,
        dest="grayscale",
        action="store_true",
        help="convert images to grayscale")
    images_group.add_argument( "--color", # color_group
        default=None,
        dest="grayscale",
        action="store_false",
        help="preserve color when using --profile")
    rescale_group = ('noup', 'nodown')
    color_group = ('bw', 'color')
    mutually_exclusive_groups.append(rescale_group)
    mutually_exclusive_groups.append(color_group)

    others_group = parser.add_argument_group(title="other")
    others_group.add_argument("--process", # process_group
        default=None,
        choices=(range(1,65)),
        metavar="2-64",
        dest="processes",
        type=int,
        help="maximum number of processes to spawn")
    others_group.add_argument( "--sequential", # process_group
        default=None,
        const=1,
        dest="processes",
        action="store_const",
        help="disable multiprocessing")
    others_group.add_argument( "--config",
        default=None,
        dest="show_config",
        action="store_true",
        help="show settings and exit")
    others_group.add_argument( "--version",
        default=None,
        dest="show_version",
        action="store_true",
        help="show version and exit")
    process_group = ('process', 'sequential')
    mutually_exclusive_groups.append(process_group)

    args, unknown_args = parser.parse_known_args()

    if args.show_version:
        print(f'{reCBZ.CMDNAME} v{reCBZ.__version__}')
        exit(0)

    # this is admittedly rather dumb, but we're trying to overcome argparse's
    # inability to include options in both groups and mutually_exclusive_groups
    # at the same time
    # more details here: https://github.com/python/cpython/issues/55193
    bad_args = []
    for mutex_group in mutually_exclusive_groups:
        group_matches = []
        for arg in sys.argv:
            for mutex_arg in mutex_group:
                p = re.compile(f'^[-]{{1,2}}{mutex_arg}')
                if p.match(arg) and arg not in group_matches:
                    group_matches.append(arg)
        if len(group_matches) >= 2: # only handle one pair at a time
            bad_args.append(group_matches[:2])

    if len(bad_args) >= 1:
        arg1, arg2 = bad_args[0] # only handle one group at a time
        print(f'{reCBZ.CMDNAME}: error: argument {arg1} not allowed with argument {arg2}')
        exit(1)

    # set profile first, ensure it can be overridden by explicit options
    if args.profile is not None:
        prof_name = args.profile.upper()
        try:
            config.set_profile(prof_name)
        except ValueError:
            print(f'{reCBZ.CMDNAME}: profile: invalid option "{prof_name}"')
            exit(1)

    if args.size_str is not None:
        newsize = args.size_str.lower().strip()
        try:
            newsize = tuple(map(int,newsize.split('x')))
            assert len(newsize) == 2
            config.img_size = newsize
        except (ValueError, AssertionError):
            print(f'{reCBZ.CMDNAME}: size: invalid option "{args.size_str}"')
            exit(1)

    # this is probably not the most pythonic way to do this
    # I'm sorry guido-san...
    for key, val in args.__dict__.items():
        if key in config.__dict__.keys() and val is not None:
            setattr(config, key, val)

    if args.show_config:
        for section in config._cfg.items():
            print(f'\n{section[0].upper()}:')
            for key, val in section[1].items():
                modified = config.__dict__[key]
                print(f"{key} =".ljust(18),
                      f"'{modified}'".ljust(8),
                      f"(default '{val}')")
        defaults_path = Path.joinpath(reCBZ.MODULE_PATH, 'defaults.toml')
        print(f'\nConfig location: {defaults_path}')
        exit(0)

    if args.show_profiles:
        print(f'{reCBZ.CMDNAME} -p ...')
        for prof_key, prof_class in ProfileDict.items():
            print(prof_key, '=', prof_class.desc)
        exit(0)

    # parse files
    if platform.system() == 'Windows':
        unknown_args = unix_like_glob(unknown_args)
    paths = []
    for arg in unknown_args:
        if Path(arg).is_file():
            paths.append(arg)
        elif Path(arg).is_dir():
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
            if not comment == str.encode(config.ZIPCOMMENT):
                new.append(filename)
        diff = len(paths) - len(new)
        if diff > 0:
            print(f'{reCBZ.CMDNAME}: noprev: ignoring {diff} files')
            if len(new) == 0:
                exit(1)
            else:
                paths = new

    # everything passed. do stuff
    exit_code = 0
    if reCBZ.SHOWTITLE and config.loglevel >= 0: print_title()
    try:
        if args.mode == 'join':
            wrappers.join_archives(paths[0], paths[1:])
        for filename in paths:
            try:
                if args.mode is None:
                    wrappers.repack_archive(filename)
                elif args.mode == 'unpack':
                    wrappers.unpack_archive(filename)
                elif args.mode == 'compare':
                    wrappers.compare_fmts_archive(filename)
                elif args.mode == 'assist':
                    wrappers.assist_repack_archive(filename)
                elif args.mode == 'auto':
                    wrappers.auto_repack_archive(filename)
            except (wrappers.AbortedRepackError, wrappers.AbortedCompareError):
                exit_code = 2
                continue
    except (KeyboardInterrupt, util.MPrunnerInterrupt):
        print('\nGoooooooooodbye')
        exit(1)
    except wrappers.AbortedRepackError:
        exit_code = 2
    finally:
        g_cache = reCBZ.GLOBAL_CACHEDIR
        if g_cache.exists():
            try:
                util.mylog(f'cleanup(): {g_cache}')
                shutil.rmtree(g_cache)
            except PermissionError:
                util.mylog(f"PermissionError, couldn't clean {g_cache}")

    return exit_code

if __name__ == '__main__':
    # catching errors here won't always work, presumably because of namespace
    # mangling
    exit(main())
