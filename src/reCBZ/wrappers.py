import time
from pathlib import Path

from PIL import UnidentifiedImageError

from reCBZ.config import Config
from reCBZ.archive import Archive
from reCBZ.util import human_bytes, pct_change, shorten, mylog


class AbortedRepackError(IOError):
    """Pages missing in repacked archive"""


class AbortedCompareError(IOError):
    """Caught PIL.UnidentifiedImageError in Archive.compute_fmt_sizes"""


def pprint_fmt_stats(base:tuple, totals:tuple) -> None:
    lines = f'┌─ Disk size ({Config.samples_count}' + \
             ' pages) with present settings:\n'
    # justify to the left and right respectively. effectively the same
    # as using f'{part1: <25} | {part2: >8}\n'
    part1 = f'│   {base[1]}'.ljust(37)
    part2 = f'{human_bytes(base[0])}'.rjust(8)
    lines += f'{part1} {part2} |  0.00%\n'
    for i, total in enumerate(totals):
        if i == len(totals)-1:
            prefix = '└─'
        else:
            prefix = '├─'
        change = pct_change(base[0], total[0])
        part1 = f'{prefix}{i+1} {total[1]}'.ljust(37)
        part2 = f'{human_bytes(total[0])}'.rjust(8)
        lines += f'{part1} {part2} | {change}\n'
    mylog('', progress=True)
    print(lines[0:-1]) # strip last newline


def pprint_repack_stats(source:dict, new:dict, start_t:float) -> None:
    end_t = time.perf_counter()
    elapsed = f'{end_t - start_t:.2f}s'
    max_width = Config.term_width()
    new_size = new['size']
    source_size = source['size']
    name = new['name']
    op = f"{source['type'].upper()} -> {new['type'].upper()}"
    if len(name) > max_width - 36:
        name = shorten(name, width=max_width - 36)
    if new_size > source_size:
        verb = 'INCREASE!'
    else:
        verb = 'decrease'
    change = pct_change(source_size, new_size)
    line1 = f"┌─ {op}: '{name}' completed in {elapsed}"
    line2 = f"└───■■ Source: {human_bytes(source_size)} ■ New: " +\
            f"{human_bytes(new_size)} ■ {change} {verb} ■■"
    mylog('', progress=True)
    print(line1)
    print(line2)


def compare_fmts_archive(fp:str, quiet=False) -> tuple:
    """Run a sample with each image format, return the results"""
    try:
        results = Archive(fp).compute_fmt_sizes()
    except UnidentifiedImageError as err:
        print("[!] Can't calculate size: PIL.UnidentifiedImageError. Aborting")
        raise AbortedCompareError
    if not quiet:
        pprint_fmt_stats(results[0], results[1:])
    return results


def unpack_archive(fp:str) -> None:
    # not implemented yet
    """Unpack the archive, converting all images within
    Returns path to repacked archive"""
    if Config.loglevel >= 0: print(shorten('[i] Unpacking', fp))
    unpacked = Archive(fp).extract()
    for file in unpacked:
        print(file)
    exit(1)


def repack_archive(fp:str) -> str:
    """Repack the archive, converting all images within
    Returns path to repacked archive"""
    if Config.loglevel >= 0: print(shorten('[i] Repacking', fp))
    start_t = time.perf_counter()
    book = Archive(fp)
    book.extract()
    source_pages = len(book.fetch_pages())
    source_stats = {'name':Path(fp).stem,
                    'size':Path(fp).stat().st_size,
                    'type':Path(fp).suffix[1:]}
    book.convert_pages() # page attributes are inherited from Config at init
    new_pages = len(book.fetch_pages())
    discarded = source_pages - new_pages
    if discarded > 0:
        print(f"[!] {discarded} files couldn't be written")
        if not Config.force_write:
            print('[!] Aborting (--force not specified)')
            return ''
    if not Config.no_write:
        if Config.overwrite:
            name = str(Path.joinpath(Path(fp).parents[0], f'{Path(fp).stem}'))
            Path(fp).unlink()
        # elif savedir TODO
        else:
            name = str(Path.joinpath(Path.cwd(), f'{Path(fp).stem} [reCBZ]'))
        results = book.write_archive(Config.archive_format, file_name=name)
    else:
        results = fp
    new_stats = {'name':Path(results).stem,
                 'size':Path(results).stat().st_size,
                 'type':Path(results).suffix[1:]}
    pprint_repack_stats(source_stats, new_stats, start_t)
    book.cleanup()
    return results


def assist_repack_archive(fp:str) -> str:
    """Run a sample with each image format, then ask which to repack
    the rest of the archive with
    Returns path to repacked archive"""
    results = compare_fmts_archive(fp)
    options_dic = {i : total[2] for i, total in enumerate(results[1:])}
    metavar = f'[1-{len(options_dic)}]'
    while True:
        try:
            reply = int(input(f"■─■ Proceed with {metavar}: ")) - 1
            selection = options_dic[reply]
            break
        except (ValueError, KeyError):
            print('[!] Ctrl+C to cancel')
            continue
        except KeyboardInterrupt:
            print('[!] Aborting (--force not specified)')
            exit(1)
    Config.img_format = selection
    return repack_archive(fp)


def auto_repack_archive(fp:str) -> str:
    """Run a sample with each image format, then automatically pick
    the smallest format to repack the rest of the archive with
    Returns path to repacked archive"""
    results = compare_fmts_archive(fp, quiet=True)
    selection = {"desc":results[1][1], "name":results[1][2]}
    fmt_name = selection['name']
    fmt_desc = selection['desc']
    if Config.loglevel >= 0: print(shorten(f'[i] Proceeding with', fmt_desc))
    Config.img_format = fmt_name
    return repack_archive(fp)


def join_archives(main_path:str, paths:list) -> str:
    """Concatenates the contents of paths to main_path and repacks
    Returns path to concatenated archive"""
    if Config.loglevel >= 0: print(shorten('[i] Repacking', main_path))
    start_t = time.perf_counter()
    main_book = Archive(main_path)
    sum_size = sum(Path(file).stat().st_size for file in paths)
    source_stats = {'name':Path(main_path).stem,
                    'size':sum_size,
                    'type':Path(main_path).suffix[1:]}
    for file in paths:
        book = Archive(file)
        main_book.add_chapter(book)
    source_pages = len(main_book.fetch_pages())
    main_book.convert_pages() # page attributes are inherited from Config at init
    new_pages = len(main_book.fetch_pages())
    discarded = source_pages - new_pages
    if discarded > 0:
        print(f"[!] {discarded} files couldn't be written")
        if not Config.force_write:
            print('[!] Aborting')
            return ''
    if not Config.no_write:
        if Config.overwrite:
            name = str(Path.joinpath(Path(main_path).parents[0], f'{Path(main_path).stem}'))
            Path(main_path).unlink()
        # elif savedir TODO
        else:
            name = str(Path.joinpath(Path.cwd(), f'{Path(main_path).stem} [reCBZ]'))
        results = main_book.write_archive(Config.archive_format, file_name=name)
    else:
        results = main_path
    new_stats = {'name':Path(results).stem,
                 'size':Path(results).stat().st_size,
                 'type':Path(results).suffix[1:]}
    pprint_repack_stats(source_stats, new_stats, start_t)
    main_book.cleanup()
    return results
