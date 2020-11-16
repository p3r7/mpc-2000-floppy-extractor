# MPC 2000 floppy extractor

Extract files from an Akai MPC 2000 floppy image.


## About

The Akai MPC 2000 has a custom scheme for supporting long file names (LFN) on FAT12 filesystems.

Its implementation is different from vFAT and uses the reserved space for each record entry in the root directory index.

As a result, `mtools` and `mount` are unable to get retrieve the long file names associated with each file.


## Usage

#### Extract Single Floppy

From a physically mounted floppy:

    $ sudo python main.py --src=/dev/fd0 --dest=/tmp/out_mpc_floppy/ -v

From a floppy image file:

    $ python main.py --src=~/Documents/floppy_1.img --dest=/tmp/out_mpc_floppy/ -v


#### Extract Virtual Floppy on USB Drive

Those apply to USB drives Gotek-formated.

From physically mounted USB drive:

    $ sudo python main.py --src=/dev/sdb --floppy 1 --dest=/tmp/out_mpc_floppy/ -v

From a virtual floppy of an image dump of a Gotek-formated USB drive:

    $ python main.py --src=~/Documents/gotek_all.img --floppy 1 --dest=/tmp/out_mpc_floppy/ -v


#### Make Image File of USB Drive / Floppy

Floppy:

    $ sudo dd if=/dev/fd0 of=~/Documents/floppy_1.img

Virtual floppy on Gotek-formated USB drive:

    $ FLOPPY_OFFSET=1
    $ sudo dd if=/dev/sdb of=~/Documents/floppy_$FLOPPY_OFFSET.img skip=$((FLOPPY_OFFSET*1536*1024)) bs=512c count=$((1440*1024)) iflag=skip_bytes,count_bytes conv=noerror

Whole Gotek-formated USB drive:

    $ sudo dd if=/dev/sdb of=~/Documents/gotek_all.img


## Installation

The script requires [kaitai](https://kaitai.io/) python module to be installed.

    $ sudo -H pip install kaitaistruct


## Implementation details

This script uses the excellent [kaitai](https://kaitai.io/) binary parser to extract the fylesystem metadata (file names and position in binary image) and then uses native python file operation to extract each file.
