import time
import re
from pathlib import Path

from PIL import UnidentifiedImageError

import reCBZ
import reCBZ.config as config
from reCBZ.archive import ComicArchive
from reCBZ.util import human_bytes, pct_change, shorten, mylog

actual_stem = ''


class AbortedRepackError(IOError):
    """Some files couldn't be converted and are missing from the archive"""


class AbortedCompareError(IOError):
    """Caught PIL.UnidentifiedImageError in Archive.compute_fmt_sizes"""


def pprint_fmt_stats(base:tuple, totals:tuple) -> None:
    lines = f'┌─ Disk size ({config.samples_count}' + \
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
    max_width = config.term_width()
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
    line1 = f"┌─ {op}: '{name}' completed in {elapsed}\n"
    line2 = f"└───■■ Source: {human_bytes(source_size)} ■ New: " +\
            f"{human_bytes(new_size)} ■ {change} {verb} ■■"
    length = len(line1) if len(line1) > len(line2) else len(line2)
    splitter = ''.rjust(length, '-')
    lines = line1 + line2 + '\n' + splitter
    mylog('', progress=True)
    if config.loglevel >= 0: print(lines)


def save(book):
    global actual_stem
    bad_files = book.bad_files
    if len(bad_files) > 0:
        if re.compile('\\.epub$').match(book.fp.suffix):
            old_len = len(bad_files)
            bad_files = [f for f in bad_files if not reCBZ.EPUB_FILES.match(str(f))]
            filtered = old_len - len(bad_files)
            if config.loglevel >= 0:
                print(f'[i] EPUB: filtered {filtered} files')
        if not config.force_write and len(bad_files) > 0:
            print(f'{book.fp.name}:')
            [print(f'error: {file.name}') for file in bad_files]
            print(f"[!] {len(bad_files)} files couldn't be converted")
            print('[!] Aborting (--force not specified)')
            print(''.rjust(config.term_width(), '^'))
            raise AbortedRepackError

    # fix suffix when source has two suffixes (kobo epub)
    try:
        actual_stem = reCBZ.KEPUB_EPUB.match(book.fp.name).group(0)
        # suffix = '.kepub.epub'
    except AttributeError:
        actual_stem = book.fp.stem
        # suffix = book.fp.suffix
    if not config.no_write:
        if config.overwrite:
            name = str(Path.joinpath(book.fp.parents[0], actual_stem))
            book.fp.unlink()
        # elif savedir TODO
        else:
            name = str(Path.joinpath(Path.cwd(), f'{actual_stem} [reCBZ]'))
        new_fp = Path(book.write_archive(config.archive_format, file_name=name))
    else:
        new_fp = book.fp
    book.cleanup()
    return str(new_fp)


def compare_fmts_archive(fp:str, quiet=False) -> tuple:
    """Run a sample with each image format, return the results"""
    try:
        results = ComicArchive(fp).compute_fmt_sizes()
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
    if config.loglevel >= 0: print(shorten('[i] Unpacking', fp))
    unpacked = ComicArchive(fp).extract()
    for file in unpacked:
        print(file)
    exit(1)


def repack_archive(fp:str) -> str:
    """Repack the archive, converting all images within
    Returns path to repacked archive"""
    if config.loglevel >= 0: print(shorten('[i] Repacking', fp))
    source_fp = Path(fp)
    start_t = time.perf_counter()
    book = ComicArchive(str(source_fp))
    book.extract()
    source_stats = {'name':source_fp.stem,
                    'size':source_fp.stat().st_size,
                    'type':source_fp.suffix[1:]}
    book.convert_pages() # page attributes are inherited from Config at init
    new_fp = Path(save(book))
    new_stats = {'name':new_fp.name,
                 'size':new_fp.stat().st_size,
                 'type':new_fp.suffix[1:]}
    pprint_repack_stats(source_stats, new_stats, start_t)
    return str(new_fp)


def join_archives(main_path:str, paths:list) -> str:
    """Concatenates the contents of paths to main_path and repacks
    Returns path to concatenated archive"""
    if config.loglevel >= 0: print(shorten('[i] Repacking', main_path))
    source_fp = Path(main_path)
    start_t = time.perf_counter()
    main_book = ComicArchive(main_path)
    sum_size = sum(Path(file).stat().st_size for file in paths)
    source_stats = {'name':source_fp.stem,
                    'size':sum_size,
                    'type':source_fp.suffix[1:]}
    for file in paths:
        book = ComicArchive(file)
        main_book.add_chapter(book)
    main_book.convert_pages()
    new_fp = Path(save(main_book))
    new_stats = {'name':new_fp.name,
                 'size':new_fp.stat().st_size,
                 'type':new_fp.suffix[1:]}
    pprint_repack_stats(source_stats, new_stats, start_t)
    main_book.cleanup()
    return str(new_fp)


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
            print('[!] Aborting')
            exit(1)
    config.img_format = selection
    return repack_archive(fp)


def auto_repack_archive(fp:str) -> str:
    """Run a sample with each image format, then automatically pick
    the smallest format to repack the rest of the archive with
    Returns path to repacked archive"""
    results = compare_fmts_archive(fp, quiet=True)
    selection = {"desc":results[1][1], "name":results[1][2]}
    fmt_name = selection['name']
    fmt_desc = selection['desc']
    config.img_format = fmt_name
    return repack_archive(fp)
