# fuzzmenu

![screenshot](https://github.com/mgurga/fuzzmenu/raw/master/docs/fuzzmenu.png)

fuzzmenu is a simplified, lighter weight, distro agnostic remake of WhiskerMenu for XFCE.
Speed is a target for this project and caches application info in ```~/.config/fuzzmenu/```.
It takes many command line arguments and is highly customizable.
Written in Python 3, uses Tk for the GUI, and has only 3 dependencies.

Features:
- Search by string
- Add favorite applications
- Choose custom categories
- Minimalist user interface
- Mostly working app icons 

## Command Line Arguments
```
usage: fuzzmenu.py [-h] [-x X] [-y Y] [-g GEOMETRY] [-ww WIDTH] [-wh HEIGHT]
                   [-c CATEGORIES] [-dc DEFAULT_CATEGORY]

'lightweight' application launcher

optional arguments:
  -h, --help            show this help message and exit
  -x X                  uses mouse x if not defined
  -y Y                  uses mouse y if not defined
  -g GEOMETRY, --geometry GEOMETRY
                        window geometry in the format of 'widthxheight+x+y'
  -ww WIDTH, --width WIDTH
  -wh HEIGHT, --height HEIGHT
  -c CATEGORIES, --categories CATEGORIES
                        categories to show in list
  -dc DEFAULT_CATEGORY, --default-category DEFAULT_CATEGORY
                        category to start up to
```

## Setup
```
git clone https://github.com/mgurga/fuzzmenu
cd fuzzmenu
pip3 install -r requirements.txt
python3 fuzzmenu.py
```
