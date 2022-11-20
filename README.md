# reCBZ - comic book repacker

CLI utility to convert, merge, upscale, and optimize comics & manga for reading on e-Readers and mobile devices. Also doubles as an extremely fast image converter.

### Purpose

I own a fairly large library of manga, which takes quite a bit of space on disk. This isn't really a problem most of the time, but it limits what I can put on my Kobo e-Reader (which has "only" 32GB of storage). I prefer to keep the original files intact on [calibre](https://github.com/kovidgoyal/calibre) on my computer, but use this tool to optimize the .cbz files in bulk so they use less space on my Kobo.

For example, by repacking with WebP at default settings, this can cut the size of the first volume of Chainsaw Man from 180MB to just under 96MB, without affecting image quality. Over the 11 published volumes, that amounts to over 1GB saved (which is a lot when you consider many e-Readers still have only 4GB)! And that's without touching the resolution, the size can be further reduced by another 50MB by downscaling to the actual display resolution — easily tripling the amount of manga that can be stored on your device, while maintaining the same perceived quality.

### Converting pages

CBZ files (which are essentially just ZIP files under a different name) are often published with little to no image compression. This is good for the purposes of preservation, but is usually overkill for the type of devices many people read from. Additionally, if you're reading from a black and white screen, removing the color information can further reduce its size by 15% to 30%. I wouldn't advise using this on your entire library, specially if you have the storage to spare, but if you're like me and want to carry 200 high quality tankobons on your pocket, this is one way to achieve it.

Although this was explicitly created with manga and comics in mind, it can be used for bulk rescaling and conversion of images in general, you just need to pack them into a ZIP archive first. There's an important caveat: non-image files will be automatically discarded, be very careful when using **--overwrite**.

Note that due to how lossy images formats like JPEG/WebP work, compressing and overwriting the same image many times over *will* eventually lead to image degradation that is noticeable to the naked eye, so by default this program creates an optimized copy while preserving the original, although lossless formats are also available. As a general rule, you can be more aggressive with compression (**--quality**) on black and white images.

### Joining volumes

Combine multiple CBZ files into a single file! If you have dozens of small chapters (or even a full series of volumes) which you'd rather store as a single contiguous unit, this tool does a pretty good job of linking them while keeping the pages in order. When writing EPUBs, it will also save each chapter/volume to the table of contents.

### EPUBs

This program can also be used to convert CBZ files to EPUB on the fly so they can be read on Kindle devices, which now support EPUB through "send to Kindle". Disclaimer: huge files might be discarded by the service, ask Amazon to properly support this format if you're upset by this.

EPUB support is a work in progress, currently only writing is supported. If your device supports CBZ, you might prefer it over EPUB, images usually fill more of the screen.

## Install

Requires [Python](https://www.python.org/downloads/) ≥ 3.7

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

Accepts a valid .cbz or .zip file, or a collection of files. With no arguments passed, it will try to repack the file(s) with slightly more compression.

The output file(s) will always be saved to the current directory as `filename [reCBZ].extension`, unless **--overwrite** is specified.

### Examples:
<details>
  <summary>Click to expand</summary>
<br>

Convert pages in 'Blame! Master Edition v06.cbz' to various formats and ask which one to repack with:

    recbz --assist 'Blame! Master Edition v06.cbz'

Rescale two volumes to the Kindle Paperwhite resolution, and save as EPUB:

    recbz --epub --size 1125x1500 'Our Dreams at Dusk v01.cbz' 'Our Dreams at Dusk v02.cbz'

To reference many files at once (e.g. a series), use a '*'. This is known as [pattern globbing](https://en.wikipedia.org/wiki/Glob_(programming)).

To match all .cbz files in the current directory:

    recbz ./*.cbz

- On Windows, slashes '/' should be replaced with backslashes '\\'

Merge the contents of all volumes of 'How do We Relationship' into a single ebook:

    recbz --epub --join 'How do We Relationship'*.cbz

Automatically convert and repack all books on the 'Blame!' folder:

    recbz --auto ./'Blame!'/*.cbz

Rescale all .cbz files on the current folder to 1440p 3:4, convert pages to grayscale and save as high quality JPEG:

    recbz --size 1440x1920 --bw --fmt jpeg --quality 90 *.cbz
</details>

## Configuration

### General options:
<details>
  <summary>Click to expand</summary>
<br>

**--nowrite**  **-nw**  
<ul>Dry run. The repacked archive isn't saved at the end, making other options completely safe.</ul>

**--overwrite**  **-O**  
<ul>Overwrite original archive. Specifically, it will be converted to a valid .cbz structure, meaning that non-image files will be discarded. Make sure you understand what this means before using this.</ul>

**--compare**  **-c**  
<ul>Calculate the filesize of each image format by converting a small sample of images, then displays a disk usage summary for each. Safe as it does not save anything.</ul>

**--assist**  **-a**  
<ul>Same as <b>--compare</b>, except it then asks you which format to repack the archive with.</ul>

**--auto**  **-A**  
<ul>Same as <b>--compare</b>, except it automatically picks the best/smallest format to repack the archive with.</ul> 

<ul>Most of the time this will be a <a href="#note-about-webp">.webp</a>. If you wish to exclude this format, you can add <b>--nowebp</b>.</ul>

**--join**  **-J**   *file1, file2 [, file3, file4, etc]*  
<ul>Concatenate files. Append the contents of n files to the leftmost file, in the order they appear.</ul>

<ul><b>Note:</b> to ensure chapters are properly shown in the table of contents when converting to <b>--epub</b>, it is recommended to join all files at once (in a single command), instead of one at a time.</ul>

**--noprev**  
<ul>Ignore files previously repacked by this program. Recommended when using file pattern globbing (*), specially with <b>--join</b>.</ul>

**--verbose**  **-v**  
<ul>More progress messages. Can be repeated (-vv) for debug output.</ul>

**--silent**  **-s**  
<ul>No progress messages.</ul>

**--processes** *1 - 32*  
default: Core count - 1 (close to 100% utilization)  
<ul>Max number of processes to spawn. This will only improve performance if your CPU has cores to spare (it's not magic!). <b>Warning:</b> May choke lower end systems, set this to 2 or 4 if you're experiencing high memory usage.</ul>

**--sequential**  
<ul>Disable multiprocessing altogether. Use this only if you're still experiencing memory issues, or for debugging.</ul>

</details>

### Archive options:
<details>
  <summary>Click to expand</summary>
<br>

**--epub**  
<ul>Save archive as EPUB.</ul>

**--zip**  
<ul>Save archive as ZIP.</ul>
 
**--cbz**  
<ul>Save archive as CBZ. This is the default.</ul>

~~**--unpack**~~ (TODO/Unimplemented)  
<ul>Extract archive contents to a folder</ul>

**--compress**  
<ul>Attempt to further compress the archive after images have been converted. This will have a very negligible effect on file size, and is generally not recommended.</ul>

</details>

### Image options:
<details>
  <summary>Click to expand</summary>
<br>

**--fmt** *format*  
default: same as source  
<ul>Format to convert images to. One of: <i>jpeg, png, webp</i> or <i>webpll</i> — png and webpll are <a href='https://en.wikipedia.org/wiki/Lossless_compression'>lossless</a>. Try <b>-c</b> to get an idea of how they compare, this will vary depending on the source format. Omitting this option will preserve the original format.</ul>

**--quality** *0 - 95*  
default: 80  
<ul>Image compression quality for lossy formats, will have a large impact on file size. Smaller values produce smaller files at the cost of visual quality. This option only applies to lossy formats</ul>

<ul><b>Notes:</b>

<ul>Low values degrade image quality less in WebP than they do in JPEG. Similarly, grayscale images are less affected by this setting that color ones, so generally speaking, you can lower it even more when using <b>--fmt webp</b> or <b>--bw</b> to save extra space.</ul>

<ul>Values higher than 95 will usually <b>increase</b> file size without actually improving quality.</ul></ul>

**--size** *WidthxHeight*  
default: don't rescale  

<ul>Rescale images to the specified resolution, using Lanczos interpolation. Does its best to detect and preserve landscape images.</ul> 

<ul>Add <b>--noup</b> to disable upscaling, so images can only be downscaled (as long as they're greater than value).</ul>

<ul>Add <b>--nodown</b> to disable downscaling, so images can only be upscaled (as long as they're less than value).</ul>

<ul>1440x1920 (3:4) is more than suitable for 6"/7" e-Reader screens. For smaller devices, setting this to 150% of your screen's resolution is usually the best compromise between quality and file size, still allowing you to zoom-in to read the lore critical thoughts of that moe character.</ul>

<ul><b>Note:</b> this isn't magic. Please don't upscale a low quality source to upload to manga sites and claim yours is higher quality, because it isn't, and it will annoy people.</ul>

**--bw**  
<ul>Convert images to grayscale. Useful for e-Paper screens, reducing file size by another 10% to 20%. Provides no benefit to comics which only have a few coloured pages (manga).</ul>

</details>

Default values for these options can be changed in `defaults.toml`
## Note about WebP

Generally speaking, the WebP format tends to compress images more efficiently than both JPEG and PNG, allowing both lossy and lossless methods. This leads to a few noticeable quirks when converting from lossy to lossless and vice versa, which are covered [here](https://developers.google.com/speed/webp/faq#can_a_webp_image_grow_larger_than_its_source_image), but overall, if you're confident your reading software supports it, this is probably the best option for saving disk space.

It isn't perfect however: WebP adoption outside of web browsers has been glacial, and it is not universally supported yet, meaning it might not open on older devices and most e-Readers (Kindle/Kobo) — although [Koreader](https://github.com/koreader/koreader/) allows you to get around this limitation.

**TL;DR** If you're repacking content for the purpose of sharing with others on the web, it is **strongly** advised to avoid this format, as many devices still aren't incapable of displaying them.

## Why not support .cbr and .cb7 archives?

Both WinRAR (.cbr) and 7zip (.cb7) are non-standard file compression programs. Undoubtedly they have helped many people compress files on PC, but they are not pre-installed on most operating systems, and thus cannot be opened on most mobile devices and e-Readers without some tinkering. Additionally, WinRAR is a proprietary program which limits official access to Windows, as the name suggests, which makes it annoying for future users that plan to read in other devices, and cannot be bundled with free software (such as this).

Also, the compression algorithm used to pack images into a comic book archive has a negligible effect on the finished archive size, as the images are already compressed, so even if these programs *can* achieve higher compression ratios than zlib/zip in most cases, they offer little to no advantage for image content.

**TL;DR** If distributing manga or comics over the high seas **PLEASE** stick to the standard .cbz format, as it's guaranteed to work on nearly every device. RAR is bad. Stop using RAR for this.

You can use [7zip](https://www.7-zip.org/) to convert .cbr and .cb7 files to .cbz.

## Credits

Thanks to aerkalov for creating [Ebooklib](https://github.com/aerkalov/ebooklib), which allows EPUB conversion.
