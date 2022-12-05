# reCBZ - comic book repacker

### Abstract

Originally, I created this to save disk space. I own a large digital manga library, which unsurprisingly uses a lot of space. This isn't really a problem most of the time, but it limits what I can put on my Kobo e-Reader (which has "only" 32GB of storage). I prefer to keep the original files intact on [Calibre](https://github.com/kovidgoyal/calibre) on my computer, but use this tool to optimize the .cbz files in bulk so they use less space on my Kobo.

For example, by repacking with WebP with the default settings, this can cut the size of the first volume of Chainsaw Man from 180MB to just under 96MB, without affecting image quality. Over the 11 published volumes, that amounts to over 1GB saved (which is a lot when you consider many e-Readers still have only 4GB)! And that's without touching the resolution, the size can be further reduced by another 50MB by downscaling to the actual display resolution — easily tripling the amount of manga that can be stored on your device, while maintaining the same perceived quality. Simply put, the amount of pixels in most comics, and the compression used to store those pixels (or lack thereof), is usually overkill for the type of screens *I* read from, and this program attempts to rectify that by doing hundreds of simple but tedious image operations in just a few seconds.

This now has a few other tricks up its sleeve which exist mainly to make the process of managing a manga library (a patchwork of individual chapters downloaded from dynastyscans) less frustrating, as well as supporting conversion to EPUBs, as the traditional tool for this, [KCC](https://github.com/ciromattia/kcc), has been unmaintained for some time (and is somewhat fiddly to install on Linux).

In short, it can:

- Upscale, downscale, desaturate, and convert comic book pages (or images in general).

- Convert them to lossy or lossless formats.

- Do this automatically to try to reduce disk space.

- Combine multiple files into a single contiguous book (transform multiple chapters into a single volume).

- Convert CBZ files into fixed-layout EPUBs, with support for most [Kindle](https://github.com/avalonv/reCBZ/wiki/Ebook-profiles#kindle) & [Kobo](https://github.com/avalonv/reCBZ/wiki/Ebook-profiles#kobo) devices.

- Make your CPU fan spin really fast.

## Install

Requires [Python  ≥ 3.9](https://www.python.org/downloads/)

<details>
  <summary>Windows setup</summary>

If you're on the latest Python version (3.11), you may need to manually install `lxml` first:

    pip install https://download.lfd.uci.edu/pythonlibs/archived/lxml-4.9.0-cp311-cp311-win_amd64.whl
</details>

Linux, MacOS, and Windows:

    python -m pip install reCBZ

or build from source:

    git clone https://github.com/avalonv/reCBZ

    python -m pip install -e reCBZ


## Usage

    recbz [options] files

Accepts a valid .cbz, .epub, or .zip file, or a collection of files. With no arguments passed, it will try to repack the file(s) with slightly more compression.

The output file(s) will always be saved to the current directory as `filename [reCBZ].extension`, unless **--overwrite** is specified.

### Config

Use `--help` or see the [Wiki](https://github.com/avalonv/reCBZ/wiki) for a list options and ebook [profiles](https://github.com/avalonv/reCBZ/wiki/Ebook-profiles).

Default values for most options can be modified in `defaults.toml`

## Examples

Create a fixed-layout ebook from a standard .cbz file, optimized for a 6" Kindle Paperwhite:

    recbz --epub --profile PW3 'Our Dreams at Dusk.cbz'

Automatically convert the pages in Blame! v01 and v02 to whichever format uses less space:

    recbz --auto 'Blame! Master Edition v01.cbz' 'Blame! Master Edition v01.cbz'

To reference many files in the same directory (e.g. a series), you can use a '*'.[^1]  
Merge the contents of all files starting with 'How do We Relationship' into a single file:

    recbz --join 'How do We Relationship'*.cbz

Rescale and convert all .cbz files on the current folder to high quality, black & white WebPs:

    recbz --size 1440x1920 --bw --convert webp --quality 90 *.cbz

## Note about WebP

Generally speaking, the WebP format tends to compress images much more efficiently than both JPEG and PNG, allowing both lossy and lossless methods. This leads to a few noticeable quirks when converting from lossy to lossless and vice versa, which are covered [here](https://developers.google.com/speed/webp/faq#can_a_webp_image_grow_larger_than_its_source_image), but overall, if you're confident your reading software supports it, this almost always translates into less disk usage. Higher compression ratios also tend to affect image quality much less than with JPEG, which makes it better at preserving fine detail in busy images.

It isn't perfect however: WebP adoption outside of web browsers has been glacial, and it is not universally supported yet, meaning it might not open on older devices and some e-Readers (Kobo) — although [Koreader](https://github.com/koreader/koreader/) allows you to get around this limitation.

**TL;DR** If you're repacking content for the purpose of sharing with others on the web, it is recommended to avoid this format, as many devices still aren't capable of displaying them.

## Why not support .cbr and .cb7 archives?

Both WinRAR (.cbr) and 7zip (.cb7) are non-standard file compression programs. Undoubtedly they have helped many people compress files on PC, but they are not pre-installed on most operating systems, and thus cannot be opened on most mobile devices and e-Readers without some tinkering. Additionally, WinRAR is a proprietary program which limits official access to Windows, as the name suggests, which makes it annoying for future users that plan to read in other devices, and cannot be bundled with free software (such as this).

Also, the compression algorithm used to pack images into a comic book archive has a negligible effect on the finished archive size, as the images are already compressed, so even if these programs *can* achieve higher compression ratios than zlib/zip in most cases, they offer little to no advantage for image content.

**TL;DR** If distributing manga or comics over the web **PLEASE** stick to the standard .cbz format, as it's guaranteed to work on nearly every device. RAR is bad. Stop using RAR for this.

You can use [7zip](https://www.7-zip.org/) to convert .cbr and .cb7 files to .cbz.

## Credits

Thanks to aerkalov for creating [Ebooklib](https://github.com/aerkalov/ebooklib), which allows EPUB conversion.

KCC, which partly inspired this program.

[^1]: This is known as [globbing](https://en.wikipedia.org/wiki/Glob_(programming)). On Windows, slashes '/' should be replaced with backslashes '\\'.
