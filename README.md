# cropall

VIBE-CODED FORK WITH A FEW ADDITIONAL FEATURES: USE AT YOUR OWN RISK.

A small cross-platform python script to interactively crop and resize lots of
images images quickly. Image editors like gimp take way too long to start, open
an image, crop it, export it. A batch job/script can automate it but everything
gets cropped at the same positions. This app sits in the middle, automating
loading/clicking crop/save/next so your amazing human vision can be used to
quickly select what needs to be cropped and not wasted on navigating clunky GUI
hierarchies.

For images this is a minimal GUI and preview for the following ImageMagick
command:

    convert in.jpg -crop <region> -resize <fit> out.jpg

ImageMagick provides the high-quality image resampling; FFmpeg handles video
frame previews and crop/resize output. The GUI uses quick, low-quality previews.

## Controls

Select the source directory to process. By default results are written to a
`crops` subdirectory.

- space - crop and advance to the next image
- left/right - previous/next image
- click - move the selection, or drag to box-select depending on the mode (hold
  shift to move the box-select)
- scroll - adjust crop size when using scroll mode (hold shift for small
  adjustments)
- Select **Lock ratio** and enter an aspect such as `1 : 1` to constrain the
  selection; uncheck it for a free-form click-drag crop. Free-form cropping uses
  click-drag mode automatically.
- Enter a positive integer in **Divisible by** to make both crop dimensions a
  multiple of that value. Leave it blank to disable the constraint.
- Videos open on their first frame. **+10 frames** advances the preview by ten
  frames; Crop applies the selected rectangle to the whole video.

![gui preview](doc/preview.jpg "GUI preview")

Buttons:

- Copy - copy the source media file to the output directory (no crop/resize)
- Resize - shrink an image or video to the smaller of the given width or height,
  keeping its aspect ratio
- Crop - crop the image or every frame of the video to match the region shown
  in the preview, also resizing if the option is selected

## Install

Download a pre-built from the
[releases](https://github.com/pknowles/cropall/releases) section on github.
These are self contained packages created with pyinstaller.

For a Linux source install, Python 3.12, Tk, ImageMagick's Wand library, and
FFmpeg are required. On Ubuntu/Debian, install the system packages first:

```bash
sudo apt-get install python3.12-venv python3-tk libmagickwand-dev ffmpeg
```

Then run the included helper script from the project directory:

```bash
./run_cropall.sh
```

The script creates `.venv`, installs `requirements.txt` on its first run,
activates the environment, and starts `cropall.py`. If `.venv` already exists,
it skips installation and starts the app using that environment. To pass an
input directory, for example:

```bash
./run_cropall.sh /path/to/photos-and-videos
```

You can also set up and run the environment manually:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python cropall.py
```

FFmpeg handles video previews and encoding; cropped videos are re-encoded
(H.264/AAC for common MP4/MOV/MKV files). Install FFmpeg separately if it is
not available through your Linux package manager. ImageMagick is used for
high-quality image resampling; see the
[Wand installation guide](https://docs.wand-py.org/en/latest/guide/install.html)
for other distributions.

Optional: create the standalone binary distribution with `pyinstaller cropall.spec`.

Feel free to report issues and post ideas. Pull requests are most welcome, thank
you! I can't promise I'll get to them immediately but I'm grateful for your time
to improve the app 😊.

## Forks and alternatives

- [@rystraum](https://github.com/rystraum/cropall) has added a number of
  features such as rotation and keyboard shortcuts. See
  [#2](https://github.com/pknowles/cropall/issues/2).
- There's a great list of alternatives here:
  https://askubuntu.com/questions/97695/is-there-a-lightweight-tool-to-crop-images-quickly
- E.g.: https://github.com/weclaw1/inbac

## License

The python source code here is under GPL v3.

```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```

### Third party code

Pre-built binaries of ImageMagick are included with the distribution. See:
https://imagemagick.org/script/license.php

The release distribution includes various scripts and binaries collected by
`pyinstaller`. Licenses found in the venv directory are included by
`cropall.spec`.
