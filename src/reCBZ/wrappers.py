from os import path

from reCBZ.archive import Archive, Config


def compare_fmts_fp(filename:str, config=Config()) -> tuple:
    """Run a sample with each image format, return the results"""
    if config.loglevel >= 0: print('[i] Analyzing', filename)
    return Archive(filename, config).analyze()


def unpack_fp(filename:str, config=Config()) -> None:
    # not implemented yet
    """Unpack the archive, converting all images within
    Returns path to repacked archive"""
    if config.loglevel >= 0: print('[i] Unpacking', filename)
    unpacked = Archive(filename, config).unpack()
    for file in unpacked:
        print(file)
    exit(1)


def repack_fp(filename:str, config=Config()) -> str:
    """Repack the archive, converting all images within
    Returns path to repacked archive"""
    if config.loglevel >= 0: print('[i] Repacking', filename)
    results = Archive(filename, config).repack()
    if results[0] == 'ABORTED':
        raise InterruptedError
    print(f"┌─ '{path.basename(results[0])}' completed in {results[1]}")
    print(f"└───■■ {results[2]} ■■")
    return results[0]


def assist_repack_fp(filename:str, config=Config()) -> str:
    """Run a sample with each image format, then ask which to repack
    the rest of the archive with
    Returns path to repacked archive"""
    results = compare_fmts_fp(filename, config)
    print(results[0])
    options = results[1]
    metavar = f'[1-{len(options)}]'
    while True:
        try:
            reply = int(input(f"■─■ Proceed with {metavar}: ")) - 1
            selection = options[reply]
            break
        except (ValueError, KeyError):
            print('[!] Ctrl+C to cancel')
            continue
        except KeyboardInterrupt:
            print('[!] Aborting')
            exit(1)
    config.formatname = selection
    return repack_fp(filename, config)


def auto_repack_fp(filename:str, config=Config()) -> str:
    """Run a sample with each image format, then automatically pick
    the smallest format to repack the rest of the archive with
    Returns path to repacked archive"""
    selection = compare_fmts_fp(filename, config)[2]
    fmt_name = selection['name']
    fmt_desc = selection['desc']
    if config.loglevel >= 0: print('[i] Proceeding with', fmt_desc)
    config.formatname = fmt_name
    return repack_fp(filename, config)
