#!/usr/bin/env python3

import os
import argparse
from pprint import pprint

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from vfat import Vfat


# ---------------------------------------------------------------
## CONSTANTS

floppy_size = 1536 * 1024 # REVIEW: 1536 or 1440?

# ---------------------------------------------------------------
## ARGS

parser = argparse.ArgumentParser("Extract Akai MPC 2000 floppy files")
parser.add_argument("--src", help="path to disk image file or device (/dev/sd?)", required=True)
parser.add_argument("--floppy", help="virtual floppy id", required=False)
parser.add_argument("--dest", help="folder to write to", required=True)
parser.add_argument("-v", "--verbose",  action = "store_true")
args = parser.parse_args()

if args.src.startswith("~/"):
    args.src = os.path.expanduser(args.src)
if args.dest.startswith("~/"):
    args.dest = os.path.expanduser(args.dest)

if args.src.startswith("/dev/sd") and (not args.floppy or args.floppy == "0"):
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
## FUNCTIONS: FLOPPY PARSING

def get_floppy_file_list(floppy_bytes, vfloppy_offest=0):
    data = Vfat.from_bytes(floppy_bytes)

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

        if r.file_size > floppy_size: # crapy file entry
            continue

        sfn_no_ext = bytes_to_ascii(r.file_name[:-3]).rstrip()
        ext = r.file_name[-3:].decode(u"ASCII")

        # NB: MPC implementation of LFN uses reserved bytes of a record instead of separate record
        lfn_part = parse_lfn_ext(r.reserved)
        lfn = sfn_no_ext + lfn_part + "." + ext

        if args.verbose:
            print("- " + lfn)
            print("  start cluster:       #" + str(r.start_clus))
            print("  size:                " + str(r.file_size))

        if start_clus_offset is None:
            start_bytes = data_start_clus * clus_size
            start_clus_offset = r.start_clus
        else:
            start_bytes = (data_start_clus - start_clus_offset + r.start_clus) * clus_size

        if args.verbose:
            print("  start pos in floppy: " + str(start_bytes))
            if vfloppy_offest:
                print("  start pos in img:    " + str(vfloppy_offest + start_bytes))

        parsed_files.append({
            'name': lfn,
            'start': vfloppy_offest + start_bytes,
            'size': r.file_size,
        })

    return parsed_files


def extract_parsed_files(parsed_files):
    with open(args.src, 'rb') as f:
        for props in parsed_files:
            f.seek(props['start'], 0)
            file_bytes = f.read(props['size'])
            with open(args.dest + props['name'], "wb") as out_f:
                out_f.write(file_bytes)


## ------------------------------------------------------------------------
## PARSE FLOPPY IMAGE

vfloppy_offset = 0
file_bytes = None
f = open(args.src, 'rb')

if args.floppy:
    vfloppy_offset = int(args.floppy) * 1536 * 1024
    f.seek(vfloppy_offset, 0)

file_bytes = f.read(floppy_size)
f.close()


parsed_files = get_floppy_file_list(file_bytes, vfloppy_offset)


## ------------------------------------------------------------------------
## EXTRACT FILES

extract_parsed_files(parsed_files)

print("Extraction complete!")
