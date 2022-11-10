import os
import argparse
import platform

from reCBZ import archive, wrappers, SHOWTITLE, CMDNAME, __version__


def print_title() -> None:
    align = int(archive.TERM_COLUMNS / 2) - 11
    if align > 21: align = 21
    if align + 22 > archive.TERM_COLUMNS or align < 0:
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
    config = archive.Config()
    readme='https://github.com/avalonv/reCBZ/blob/master/README.md#usage'
    parser = argparse.ArgumentParser(
            prog=CMDNAME,
            usage="%(prog)s [options] files.cbz",
            epilog=f"for detailed documentation, see {readme}")
    mode_group = parser.add_mutually_exclusive_group()
    fmt_group = parser.add_mutually_exclusive_group()
    ext_group = parser.add_mutually_exclusive_group()
    log_group = parser.add_mutually_exclusive_group()
    process_group = parser.add_mutually_exclusive_group()
    parser.add_argument( "-nw", "--nowrite",
        default=config.nowrite,
        dest="nowrite",
        action="store_true",
        help="dry run, no changes are saved at the end of repacking (safe)")
    mode_group.add_argument( "-u", "--unpack",
        const=0,
        dest="mode",
        action="store_const",
        help="unpack the archive to the currect directory (safe)")
    mode_group.add_argument( "-c", "--compare",
        const=1,
        dest="mode",
        action="store_const",
        help="test a small sample with all formats and print the results (safe)")
    mode_group.add_argument( "-a", "--assist",
        const=2,
        dest="mode",
        action="store_const",
        help="compare, then ask which format to use for a real run")
    mode_group.add_argument( "-A" ,"--auto",
        const=3,
        dest="mode",
        action="store_const",
        help="compare, then automatically picks the best format for a real run")
    fmt_group.add_argument( "--nowebp",
        default=config.blacklistedfmts,
        const=f'{config.blacklistedfmts} webp webpll',
        dest="blacklistedfmts",
        action="store_const",
        help="exclude webp from --auto")
    ext_group.add_argument( "-O", "--overwrite",
        default=config.overwrite,
        dest="overwrite",
        action="store_true",
        help="overwrite the original archive")
    parser.add_argument( "-F", "--force",
        default=config.force,
        dest="force",
        action="store_true",
        help="ignore file errors when using overwrite (dangerous)")
    log_group.add_argument( "-v", "--verbose",
        default=config.loglevel,
        dest="loglevel",
        action="count",
        help="increase verbosity of progress messages, repeatable: -vvv")
    log_group.add_argument( "-s", "--silent",
        const=0,
        dest="loglevel",
        action="store_const",
        help="disable all progress messages")
    process_group.add_argument("--processes",
        default=config.processes,
        choices=(range(1,33)),
        metavar="[1-32]",
        dest="processes",
        type=int,
        help="number of processes to spawn")
    process_group.add_argument( "--sequential",
        default=config.parallel,
        dest="parallel",
        action="store_false",
        help="disable multiprocessing")
    ext_group.add_argument( "--zipext",
        default=config.zipext,
        choices=('.cbz', '.zip'),
        metavar=".cbz/.zip",
        dest="zipext",
        type=str,
        help="extension to save the new archive with")
    parser.add_argument( "--zipcompress",
        default=config.compresslevel,
        choices=(range(10)),
        metavar="[0-9]",
        dest="compresslevel",
        type=int,
        help="compression level for the archive. 0 (default) recommended")
    fmt_group.add_argument( "--fmt",
        default=config.formatname,
        choices=('jpeg', 'png', 'webp', 'webpll'),
        metavar="fmt",
        dest="formatname",
        type=str,
        help="format to convert images to: jpeg, webp, webpll, or png")
    parser.add_argument( "--quality",
        default=config.quality,
        choices=(range(1,101)),
        metavar="[0-95]",
        dest="quality",
        type=int,
        help="save quality for lossy formats. >90 not recommended")
    parser.add_argument( "--size",
        metavar="WidthxHeight",
        default=config.resolution,
        dest="resolution",
        type=str,
        help="rescale images to the specified resolution")
    parser.add_argument( "-noup", "--noupscale",
        default=config.noupscale,
        dest="noupscale",
        action="store_true",
        help="disable upscaling with --size")
    parser.add_argument( "-nodw", "--nodownscale",
        default=config.nodownscale,
        dest="nodownscale",
        action="store_true",
        help="disable downscaling with --size")
    parser.add_argument( "-bw", "--grayscale",
        default=config.grayscale,
        dest="grayscale",
        action="store_true",
        help="convert images to grayscale")
    parser.add_argument( "--version",
        dest="show_version",
        action="store_true",
        help="show version and exit")
    parser.add_argument( "--config",
        dest="show_config",
        action="store_true",
        help="show current settings")
    args, unknown_args = parser.parse_known_args()
    # this is probably not the most pythonic way to do this
    # I'm sorry guido-san...
    for key, val in args.__dict__.items():
        if key in config.__dict__.keys():
            setattr(config, key, val)
    if args.show_config:
        for key, val in config.__dict__.items():
            print(f"{key} = {val}")
    if args.show_version:
        print(f'{CMDNAME} v{__version__}')
        exit(0)

    # parse files
    if platform.system() == 'Windows':
        unknown_args = unix_like_glob(unknown_args)
    paths = []
    for arg in unknown_args:
        if os.path.isfile(arg):
            paths.append(arg)
        elif os.path.isdir(arg):
            print(f'{CMDNAME}: {arg}: is a directory')
            parser.print_usage()
            exit(1)
        else:
            parser.print_help()
            print(f'\nunknown file or option: {arg}')
            exit(1)
    if len(paths) <= 0:
        print(f'{CMDNAME}: missing input file (see --help)')
        parser.print_usage()
        exit(1)
    # everything passed
    if SHOWTITLE: print_title()
    mode = args.mode
    for filename in paths:
        try:
            if mode is None:
                wrappers.repack_fp(filename, config)
            elif mode == 0:
                wrappers.unpack_fp(filename, config)
            elif mode == 1:
                wrappers.compare_fmts_fp(filename, config)
            elif mode == 2:
                wrappers.assist_repack_fp(filename, config)
            elif mode == 3:
                wrappers.auto_repack_fp(filename, config)
        except InterruptedError:
            continue


if __name__ == '__main__':
    main()
