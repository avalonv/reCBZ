## Purpose 

I own a fairly large library of manga, and it takes quite a bit of space on disk. This isn't really a problem most of the time, but it limits what I can put on my Kobo e-Reader (which has "only" 32GB of storage). I prefer to keep the original files intact on [calibre](https://github.com/kovidgoyal/calibre) on my computer, but use this tool to optimize the .cbz files in bulk so they use less space on my Kobo, by resizing to a slightly lower resolution (1920 x 2560), and converting them to WebP, which can cut the size of a high quality .cbz by half.

For example, by repacking with --auto/WebP, this can halve the size of the first volume of Chainsaw Man from 180MB to just under 96MB without degrading image quality. Over the 11 published volumes, that amounts to over 1GB saved, which is quite a lot when you consider most e-Readers still have only 4GB! And that's just by changing the format, the size can be further reduced by another 50MB by downscaling to 120% display resolution and converting images to grayscale, while still maintaining optimal visual clarity on a 6" 300PPI screen — effectively tripling the amount of manga you can store on your device.

Note that due to how lossy images formats like JPEG/WebP work, compressing and overwriting the same file many times over *will* eventually lead to image degradation that is noticeable to the naked eye, so by default this program creates an optimized copy while preserving the original, although lossless formats are also supported. As a general rule, you can be more aggressive with compression on black and white images.

It can also be used to upscale low quality images with reasonable success. It is not as good as neural networks, but is capable of doubling the resolution of an image with pretty good anti-aliasing, which is useful if you happen to read lots of of scanlations.

Although this was explicitly created with manga and comics (.cbz files) in mind, it can be used for bulk rescaling and conversion of images in general (and is pretty fast at that due to parallelism), with some caveats: non-image files will be discarded, and the folder structure will be flattened (every image will be written to the same folder, files which share a name will be overwritten).

This program should work on Windows, MacOS, and Linux. Image operations are done through [Pillow](https://github.com/python-pillow/Pillow), the rest uses the standard Python library.

Lastly, this program is new and can lead to unintended loss of data if used carelessly. It's recommended to have a backup somewhere when using --overwrite.

## Usage


Accepts a valid .cbz or .zip file, or a collection of files. Returns a repacked copy based on current settings. See options for defaults.

The output file(s) will always be saved as `filename [reCBZ].extension`, unless **--overwrite** is specified.
  
### MacOS/Linux:  

    ./reCBZ.py [options] files
### Windows:  

    python reCBZ.py [options] files


### General options (no effect on file size):
<details>
  <summary>Click to expand</summary>
<br>

**--nowrite**  **-nw**  
<ul>Dry run. The repacked archive isn't saved at the end, making other options completely safe.</ul>

**--compare**  **-c**   
<ul>Does a dry run with a small sample of images, converting them to available formats using current settings, then displays a disk usage summary for each.</ul>

**--assist**  **-a**
<ul>Same as <b>--compare</b>, except it then asks you which format to use for a real run.</ul>

**--auto**  **-A**  
<ul>Same as <b>--compare</b>, except it automatically picks the best/smallest format for a real run.</ul> 

<ul>Most of the time this will be a <a href="#note-about-webp">.webp</a>. <s>If you wish to exclude this format, you can add <b>--nowebp</b></s> (TODO/Unimplemented).</ul>

**--overwrite**  **-O**  
<ul>Overwrite the original archive. Specifically, it will be converted to a valid .cbz structure, meaning that non-image files will be discarded, and the folder structure will be flattened, any images sharing a name will be lost. Make sure you understand what this means before using this.</ul>

~~**--recursive**  **-R**~~  (TODO/Unimplemented)  see [#examples](#examples) 
<ul>Search all subfolders in the current path for .cbz or .zip files to convert.</ul>

<ul><b>Exercise caution when using with --overwrite, may lead to loss of data.</b></ul>

**--verbose**  **-v**  
<ul>More progress messages. Can be repeated (-vv) for debug output.</ul>

**--silent**  **-s**   
<ul>No progress messages.</ul>

**--processes** *1 - 32*  
default: 16  
<ul>Number of processes to spawn. This will only improve performance if your CPU has cores to spare (it's not magic!). Lower this to 2 or 4 if you're experiencing high memory usage.</ul>

**--sequential**  
<ul>Disable multiprocessing altogether. Use this only if you're still experiencing memory issues, or for debugging.</ul>

**--zipext** *.cbz* or *.zip*  
default: .cbz  
<ul>Extension for the new archive, signals to the OS which mimetype to open files with (they're the same internally).</ul>

**--zipcompress** *0 - 9*  
default: 0  
<ul>Compression strength for the archive (after images have been converted). The default (0) is <i>strongly</i> recommended, setting it to higher values is nearly always counterproductive, it will barely affect archive size (if at all) as the images are already compressed, but will significantly increase the time it takes to open it.</ul>

</details>

### Image options (affect file size):
<details>
  <summary>Click to expand</summary>
<br>

**--fmt** *format*  
default: same as source  
<ul>Image format to convert images to. One of: <i>jpeg, webp, webpll,</i> or <i>png</i> — webpll stands for lossless. Try <b>-c</b> to get an idea of how they compare, this will vary. Omitting this option will preserve the original format.</ul>

**--quality** *0 - 95*  
default: 80  
<ul>Image compression quality for lossy formats, will have a large impact on file size. Smaller values will reduce file size at the cost of visual quality. This option doesn't affect lossless formats</ul>

<ul><b>Note:</b> values higher than 95 will <b>increase</b> file size without actually improving quality.</ul>

**--resize** *WidthxHeight*  
default: don't resize  

<ul>Rescale images to the specified resolution, using Lanczos interpolation. Does its best to detect and preserve landscape images.</ul> 

<ul>Add <b>--noupscale</b> to disable upscaling, so images will only be downscaled (as long as they're greater than value).</ul>

<ul>Add <b>--nodownscale</b> to disable upscaling, so images can only be upscaled (as long as they're less than value).</ul>

<ul>1440x1920 (3:4) is suitable for most 6"/7" e-Reader screens. For smaller devices, setting this to 150% of your screen's resolution is usually the best compromise between quality and file size, still allowing you to zoom-in to read the lore critical thoughts of that moe character.</ul>

<ul><b>Note:</b> this isn't magic. Please don't upscale a low quality source to upload to manga sites and claim yours is higher quality, because it isn't, and it will annoy people.</ul>

**--grayscale**  **-bw**  
<ul>Convert images to grayscale. Useful for e-Paper screens, reducing file size by another 10% to 20%. Provides no benefit to comics which only have a few coloured pages (manga).</ul>

</details>

### Examples:

Downscale pages to 1440x1920, convert to grayscale, and save as high quality JPEG:

    reCBZ.py --resize 1440x1920 --quality 90 -bw --fmt jpeg 'Our Dreams at Dusk v01.cbz' 'Our Dreams at Dusk v02.cbz'

For repacking entire directories (i.e. a series), use:

    reCBZ.py [options] ./'Our Dreams at Dusk - Yuhki Kamatani'/*.cbz`

(TODO/not implemented on Windows)

## Note about WebP

Generally speaking, the WebP format tends to compress images more efficiently than both JPEG and PNG, allowing both lossy and lossless methods. This leads to a few noticeable quirks when converting from lossy to lossless and vice versa, which are covered [here](https://developers.google.com/speed/webp/faq#can_a_webp_image_grow_larger_than_its_source_image), but overall, if you're confident your reading software supports it, this is probably the best option for saving disk space. 

It isn't perfect however: WebP adoption outside of web browsers has been glacial, and it is not universally supported yet, meaning it might not open on older devices and the vast majority of e-Readers (Kindle/Kobo) — although [Koreader](https://github.com/koreader/koreader/) allows you to get around this limitation.

**TL;DR** If you're repacking content for the purpose of sharing with others on the web, it is **strongly** advised to avoid this format, as many devices still aren't incapable of displaying them.

## Why not support .cbr and .cb7 archives? 

Both RAR (.cbr) and 7z (.cb7) are non-standard compression formats. Undoubtedly they have helped many people compress files on PC, but they are not pre-installed on most operating systems, and thus cannot be opened on most mobile devices and e-Readers without tinkering. Additionally, WinRAR is a proprietary program which limits official access to Windows, as the name suggests, which makes it annoying for future users that plan to read in other devices, and cannot be bundled with free software. 

Also, the compression algorithm used to pack images into a comic book archive has a negligible effect on the finished archive size, as the images are already compressed, so even if these programs *can* achieve higher compression ratios than zlib/zip in theory, they offer little to no advantage for image content.

**TL;DR** If distributing manga or comics over the high seas **PLEASE** stick to the standard .cbz format, as it's guaranteed to work on nearly every device. RAR is bad. Stop using RAR for this.

WIP/TODO ~~If you need to convert .cbr or .cb7 files to .cbz, use this [script](link).~~
