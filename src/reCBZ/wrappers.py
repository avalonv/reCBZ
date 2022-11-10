from os import path

from reCBZ.archive import Archive, Config


def compare_fmts_fp(filename:str, config=Config()) -> None:
    """Run a sample with each image format, then print the results"""
    print('[!] Analyzing', filename)
    results = Archive(filename, config).analyze()
    print(results[0])


def unpack_fp(filename:str, config=Config()) -> None:
    """Unpack the archive, converting all images within
    Returns path to repacked archive"""
    print('[!] Repacking', filename)
    unpacked = Archive(filename, config).unpack()
    for file in unpacked:
        print(file)
    exit(1)


def repack_fp(filename:str, config=Config()) -> str:
    """Repack the archive, converting all images within
    Returns path to repacked archive"""
    print('[!] Repacking', filename)
    results = Archive(filename, config).repack()
    print(f"┌─ '{path.basename(results[0])}' completed in {results[1]}")
    print(f"└───■■ {results[2]} ■■")
    return results[0]


def assist_repack_fp(filename:str, config=Config()) -> str:
    """Run a sample with each image format, then ask which to repack
    the rest of the archive with
    Returns path to repacked archive"""
    print('[!] Analyzing', filename)
    results = Archive(filename, config).analyze()
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
    print('[!] Analyzing', filename)
    selection = Archive(filename, config).analyze()[2]
    fmt_name = selection['name']
    fmt_desc = selection['desc']
    print('[!] Proceeding with', fmt_desc)
    config.formatname = fmt_name
    return repack_fp(filename, config)
