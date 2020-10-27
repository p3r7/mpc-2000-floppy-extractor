# MPC 2000 floppy extractor

Extract files from an Akai MPC 2000 floppy image.


## About

The Akai MPC 2000 has a custom scheme for supporting long file names (LFN) on FAT12 filesystems.

Its implementation is different from vFAT and uses the reserved space for each record entry in the root directory index.

As a result, `mtools` and `mount` are unable to get retrieve the long file names associated with each file.


## Implementation details

This script uses the excellent [kaitai](https://kaitai.io/) binary parser to extract the fylesystem metadata (file names and position in binary image) and then uses native python file operation to extract each file.
