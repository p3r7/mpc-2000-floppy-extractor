#!/usr/bin/env python3

import os
from pathlib import Path
import shutil
import argparse
import json
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
parser.add_argument("--floppy", help="virtual floppy id(s), list and ranges supported", required=False)
parser.add_argument("--dest", help="folder to write to", required=False)
parser.add_argument("--out-format", help="output format for listing files", choices=['txt', 'json'], required=False)
parser.add_argument("-v", "--verbose",  action = "store_true")
args = parser.parse_args()

sudo_user = ''
if 'SUDO_USER' in os.environ:
    sudo_user = os.environ["SUDO_USER"]

if args.src.startswith("~/"):
    args.src = args.src.replace("~/", "~"+sudo_user+"/")
    args.src = os.path.expanduser(args.src)
if args.dest and args.dest.startswith("~/"):
    args.dest = args.dest.replace("~/", "~"+sudo_user+"/")
    args.dest = os.path.expanduser(args.dest)

if not args.dest:
    args.verbose = True

if not args.out_format:
    # NB: default option doesn't seem to work / choices
    args.out_format = 'txt'

# print(args.out_format)

floppy_list = []
if args.floppy:
    floppy_ranges = args.floppy.split(',')
    for frange in floppy_ranges:
        split_frange = frange.split('-')
        if len(split_frange) == 2:
            f, t = split_frange
            floppy_list.extend(range(int(f), int(t)+1))
        else:
            floppy_list.append(int(frange))
floppy_list = list(set(floppy_list))

if args.src.startswith("/dev/sd"):
    if not floppy_list:
        parser.error("When targeting a Gotek-formated USB drive, please precise `--floppy`, i.e. which virtual floppy to extract.")


## ------------------------------------------------------------------------
## FUNCTIONS: GENERIC

def is_printable_ascii_char(c):
    return c >= 0x20 and c <= 0x7e

def bytes_to_ascii(byte_arr):
    filtered_arr = bytearray()
    for b in byte_arr:
        if is_printable_ascii_char(b):
            filtered_arr.append(b)
    return filtered_arr.decode(u"ASCII")


## ------------------------------------------------------------------------
## FUNCTIONS: FIELD PARSING

def parse_vfat_lfn(r):
    lfn_arr = bytearray()
    for i in [1, 3, 5, 7, 9]:
        lfn_arr.append(r.file_name[i])
    for i in [2, 4, 6, 8]:
        lfn_arr.append(r.reserved[i])
    r_time = r.time.to_bytes(2, 'little')
    for i in [0]:
        lfn_arr.append(r_time[i])
    r_date = r.date.to_bytes(2, 'little')
    for i in [0]:
        lfn_arr.append(r_date[i])
    r_size = r.file_size.to_bytes(4, 'little')
    for i in [0, 2]:
        lfn_arr.append(r_size[i])
    return bytes_to_ascii(lfn_arr)


def parse_mpc_lfn_ext(reserved):
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

    if data.boot_sector.is_fat32:
        floppy_name = data.boot_sector.ebpb_fat32.partition_volume_label
    else:
        floppy_name = data.boot_sector.ebpb_fat16.partition_volume_label

    current_vfat_lfn = ""
    for r in data.root_dir.records:
        # NB: the records index is at 0x2600

        if r.attribute in [8, 0]: # current dir, empty slot
            continue

        if r.attribute == 15: # vFAT LFN
            current_vfat_lfn = parse_vfat_lfn(r)
            continue

        if r.file_size == 0: # empty file
            if current_vfat_lfn:
                current_vfat_lfn = ""
            continue

        sfn_no_ext = bytes_to_ascii(r.file_name[:-3]).rstrip()
        ext = r.file_name[-3:].decode(u"ASCII")

        # NB: MPC implementation of LFN uses reserved bytes of a record instead of separate record
        mpc_lfn_part = parse_mpc_lfn_ext(r.reserved)
        mpc_fn = sfn_no_ext + mpc_lfn_part + "." + ext

        if mpc_lfn_part:
            fn = mpc_fn
        elif current_vfat_lfn:
            fn = current_vfat_lfn
        else:
            fn = mpc_fn

        if args.verbose and args.out_format == "txt":
            fn_text = mpc_fn
            if current_vfat_lfn:
                fn_text += " (" + current_vfat_lfn + ")"
            print("- " + fn_text)
            print("  start cluster:       #" + str(r.start_clus))
            print("  size:                " + str(r.file_size))

        if start_clus_offset is None:
            start_bytes = data_start_clus * clus_size
            start_clus_offset = r.start_clus
        else:
            start_bytes = (data_start_clus - start_clus_offset + r.start_clus) * clus_size

        current_vfat_lfn = ""

        if args.verbose and args.out_format == "txt":
            print("  start pos in floppy: " + str(start_bytes))
            if vfloppy_offest:
                print("  start pos in img:    " + str(vfloppy_offest + start_bytes))

        parsed_files.append({
            'name': fn,
            'start': vfloppy_offest + start_bytes,
            'size': r.file_size,
        })

    return (floppy_name, parsed_files)


def extract_parsed_files(parsed_files, floppy_id=None):
    dest_dir = args.dest
    if floppy_id:
        dest_dir = args.dest.rstrip("/") + "/" + str(floppy_id) + "/"
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        if sudo_user:
            shutil.chown(dest_dir, sudo_user, sudo_user)
    with open(args.src, 'rb') as f:
        for props in parsed_files:
            f.seek(props['start'], 0)
            file_bytes = f.read(props['size'])
            with open(dest_dir + props['name'], "wb") as out_f:
                out_f.write(file_bytes)
            if sudo_user:
                shutil.chown(dest_dir + props['name'], sudo_user, sudo_user)


## ------------------------------------------------------------------------
## PARSE FLOPPY IMAGES

vfloppy_offset = 0
file_bytes = None
f = open(args.src, 'rb')

if floppy_list:
    parsed_files = []
    for floppy in floppy_list:
        if args.verbose and args.out_format == "txt":
            print("-"*35)
            print("FLOPPY #" + str(floppy))
        vfloppy_offset = floppy * 1536 * 1024
        f.seek(vfloppy_offset, 0)
        file_bytes = f.read(floppy_size)
        (name, files) = get_floppy_file_list(file_bytes, vfloppy_offset)
        parsed_files.append({
            'name': name,
            'files': files,
        })
else:
    file_bytes = f.read(floppy_size)
    (name, parsed_files) = get_floppy_file_list(file_bytes, vfloppy_offset)
f.close()



## ------------------------------------------------------------------------
## EXTRACT FILES

if not args.dest:
    if args.out_format == "json":
        print(json.dumps(parsed_files))
    exit(0)

if floppy_list:
    for f_id, props in parsed_files.items():
        files = props['files']
        if files:
            extract_parsed_files(files, f)
else:
    extract_parsed_files(parsed_files)

print("Extraction complete!")
