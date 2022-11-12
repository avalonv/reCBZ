import time
from pathlib import Path

import reCBZ
from .config import Config
from .archive import Archive
from .utils import human_bytes, pct_change, shorten


def pprint_fmt_stats(base:tuple, totals:tuple) -> None:
    print('base', base)
    print('totals', totals)
    lines = f'┌─ Disk size ({reCBZ.COMPARESAMPLES}' + \
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
    print(lines[0:-1]) # strip last newline


def pprint_repack_stats(name:str, sizes:tuple, start_t:float) -> None:
    end_t = time.perf_counter()
    width = Config().term_width
    elapsed = f'{end_t - start_t:.2f}s'
    base = sizes[0]
    new = sizes[1]
    if len(name) > width - 33:
        name = shorten(name, width=width - 33)
    line1 = f"┌─ Source: '{name}' completed in {elapsed}"
    if type(new) is str:
        line2 = f"└───■■ {new} " # bad
    else:
        if new > base:
            verb = 'INCREASE!'
        else:
            verb = 'decrease'
        change = pct_change(base, new)
        line2 = f"└───■■ Source: {human_bytes(base)} ■ New: " +\
                f"{human_bytes(new)} ■ {change} {verb} ■■"
    print(line1)
    print(line2)


def compare_fmts_fp(filename:str) -> tuple:
    """Run a sample with each image format, return the results"""
    if Config.loglevel >= 0: print(shorten('[i] Analyzing', filename))
    results = Archive(filename).compute_fmt_sizes()
    pprint_fmt_stats(results[0], results[1:])
    return results


def unpack_fp(filename:str) -> None:
    # not implemented yet
    """Unpack the archive, converting all images within
    Returns path to repacked archive"""
    if Config.loglevel >= 0: print(shorten('[i] Unpacking', filename))
    unpacked = Archive(filename).repack()
    for file in unpacked:
        print(file)
    exit(1)


def repack_fp(filename:str) -> str:
    """Repack the archive, converting all images within
    Returns path to repacked archive"""
    if Config.loglevel >= 0: print(shorten('[i] Repacking', filename))
    source_size = Path(filename).stat().st_size

    start_t = time.perf_counter()
    results = Archive(filename).repack()
    if 'ABORTED:' in results:
        new_size = results
    else:
        new_size = Path(results).stat().st_size
    pprint_repack_stats(Path(filename).name, (source_size, new_size), start_t)
    return results


def assist_repack_fp(filename:str) -> str:
    """Run a sample with each image format, then ask which to repack
    the rest of the archive with
    Returns path to repacked archive"""
    results = compare_fmts_fp(filename)
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
    Config.formatname = selection
    return repack_fp(filename)


def auto_repack_fp(filename:str) -> str:
    """Run a sample with each image format, then automatically pick
    the smallest format to repack the rest of the archive with
    Returns path to repacked archive"""
    results = Archive(filename).compute_fmt_sizes()
    selection = {"desc":results[1][1], "name":results[1][2]}
    fmt_name = selection['name']
    fmt_desc = selection['desc']
    if Config.loglevel >= 0: print(shorten(f'[i] Proceeding with', fmt_desc))
    Config.formatname = fmt_name
    return repack_fp(filename)
