#!/usr/bin/env python3

import argparse
from pprint import pprint

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from vfat import Vfat


# ---------------------------------------------------------------
## ARGS

parser = argparse.ArgumentParser("Extract Akai MPC 2000 floppy files")
parser.add_argument("--src", help="path to disk image file or device (/dev/sd?)", required=True)
parser.add_argument("--floppy", help="virtual floppy id", required=False)
parser.add_argument("--dest", help="folder to write to", required=True)
parser.add_argument("-v", "--verbose",  action = "store_true")
args = parser.parse_args()

if args.src.startswith("/dev/db") and not args.floppy:
    parser.error("When targeting a Gotek-formated USB drive, please precise `--floppy`, i.e. which virtual floppy to extract.")


## ------------------------------------------------------------------------
## FUNCTIONS: GENERIC

def is_ascii_char(c):
    return c >= 0x00 and c <= 0x7F

def bytes_to_ascii(byte_arr):
    filtered_arr = bytearray()
    for b in byte_arr:
        if is_ascii_char(b):
            filtered_arr.append(b)
    return filtered_arr.decode(u"ASCII")


## ------------------------------------------------------------------------
## FUNCTIONS: FIELD PARSING

def parse_lfn_ext(reserved):
    if reserved[0] == 0x00:
        return ''
    else:
        return bytes_to_ascii(reserved[:-2]).replace("[Q", "").rstrip()


## ------------------------------------------------------------------------
## PARSE FLOPPY IMAGE

file_bytes = None
if args.floppy:
    offset_bytes = int(args.floppy) * 1536 * 1024
    f = open(args.src, 'rb')
    f.seek(offset_bytes, 0)
    file_bytes = f.read(1536 * 1024) # REVIEW: 1536 or 1440?
    f.close()

if file_bytes is not None:
    data = Vfat.from_bytes(file_bytes)
else:
    data = Vfat.from_file(args.src)

# those might always the same for FAT12 but whatever...
bytes_per_ls = data.boot_sector.bpb.bytes_per_ls
ls_per_clus = data.boot_sector.bpb.ls_per_clus
clus_size = bytes_per_ls * ls_per_clus

data_start_clus = 33
# cf https://www.eit.lth.se/fileadmin/eit/courses/eitn50/Literature/fat12_description.pdf

start_clus_offset = None
parsed_files = []

for r in data.root_dir.records:
    # NB: the records index is at 0x2600

    if r.attribute == 0: # not an actual file
        continue

    if r.file_size == 0: # empty file
        continue

    if r.file_size > (1440 * 1024): # crapy file entry
        continue

    sfn_no_ext = bytes_to_ascii(r.file_name[:-3]).rstrip()
    ext = r.file_name[-3:].decode(u"ASCII")

    # NB: MPC implementation of LFN uses reserved bytes of a record instead of separate record
    lfn_part = parse_lfn_ext(r.reserved)
    lfn = sfn_no_ext + lfn_part + "." + ext

    if args.verbose:
        print("- " + lfn)
        print("  start cluster:    #" + str(r.start_clus))
        print("  size:             " + str(r.file_size))

    if start_clus_offset is None:
        start_bytes = data_start_clus * clus_size
        start_clus_offset = r.start_clus
    else:
        start_bytes = (data_start_clus - start_clus_offset + r.start_clus) * clus_size

    if args.verbose:
        print("  start pos in img: " + str(start_bytes))

    parsed_files.append({
        'name': lfn,
        'start': start_bytes,
        'size': r.file_size,
    })


## ------------------------------------------------------------------------
## EXTRACT FILES

with open(args.src, 'rb') as f:
    for props in parsed_files:
        f.seek(props['start'], 0)
        file_bytes = f.read(props['size'])
        with open(args.dest + props['name'], "wb") as out_f:
            out_f.write(file_bytes)
            out_f.close()
    f.close()

print("Extraction complete!")
