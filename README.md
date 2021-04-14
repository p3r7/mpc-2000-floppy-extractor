# MPC 2000 floppy extractor

Extract files from one or several Akai MPC 2000 (v)floppy images.

For more context, read the [accompanying blog post](https://www.eigenbahn.com/2021/04/11/mpc-2000-floppy-format).


## About

The Akai MPC 2000 has a custom scheme for supporting long file names (LFN) on FAT12 filesystems.

Its implementation is different from vFAT and uses the reserved space for each record entry in the root directory index.

As a result, `mtools` and `mount` are unable to get retrieve the long file names associated with each file.


## Usage

#### List files on Floppy

From a physically mounted floppy:

    $ sudo python main.py --src=/dev/fd0

From a floppy image file:

    $ python main.py --src=~/Documents/floppy_1.img


#### List files on Virtual Floppies

Floppies #1, #7 and #13:

    $ sudo python main.py --src=/dev/sdb --floppy 1,7,13

Floppies #1 to #99:

    $ sudo python main.py --src=/dev/sdb --floppy 1-99


#### Extract Single Floppy

From a physically mounted floppy:

    $ sudo python main.py --src=/dev/fd0 --dest=/tmp/out_mpc_floppy/ -v

From a floppy image file:

    $ python main.py --src=~/Documents/floppy_1.img --dest=/tmp/out_mpc_floppy/ -v


#### Extract Virtual Floppies

Those apply to USB drives Gotek-formated.

Floppy #1 from physically mounted USB drive:

    $ sudo python main.py --src=/dev/sdb --floppy 1 --dest=/tmp/out_mpc_floppy/ -v

Floppy #1 from a virtual floppy of an image dump of a Gotek-formated USB drive:

    $ python main.py --src=~/Documents/gotek_all.img --floppy 1 --dest=/tmp/out_mpc_floppy/ -v

Floppies #1, #7 and #13:

    $ sudo python main.py --src=/dev/sdb --floppy 1,7,13 --dest=/tmp/out_mpc_floppy/ -v

Floppies #10 to #20:

    $ sudo python main.py --src=/dev/sdb --floppy 10-20 --dest=/tmp/out_mpc_floppy/ -v


#### Bonus: Make Image File of USB Drive / Floppy

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
