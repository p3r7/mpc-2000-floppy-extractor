#!/usr/bin/env python3

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO

from vfat import Vfat
from pprint import pprint


## ------------------------------------------------------------------------
## CONF

img_file = "/home/me/Documents/floppy_1.img"
out_folder= "/tmp/out_mpc_floppy/"


## ------------------------------------------------------------------------
## PARSE FLOPPY IMAGE

data = Vfat.from_file(img_file)

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

    sfn_no_ext = r.file_name[:-3].decode(u"ASCII")
    ext = r.file_name[-3:].decode(u"ASCII")

    # NB: MPC implementation od LFN uses reserved bytes of a record instead of separate record
    lfn_part = r.reserved[:-2].decode(u"ASCII").rstrip()
    lfn = sfn_no_ext + lfn_part + "." + ext

    print("- " + lfn)
    print("  start cluster:" + str(r.start_clus))
    print("  size:" + str(r.file_size))

    if start_clus_offset is None:
        start_bytes = data_start_clus * clus_size
        start_clus_offset = r.start_clus
    else:
        start_bytes = (data_start_clus - start_clus_offset + r.start_clus) * clus_size

    print("  start pos in img: " + str(start_bytes))

    parsed_files.append({
        'name': lfn,
        'start': start_bytes,
        'size': r.file_size,
    })


## ------------------------------------------------------------------------
## EXTRACT FILES

with open(img_file, 'rb') as f:
    for props in parsed_files:
        f.seek(props['start'], 0)
        file_bytes = f.read(props['size'])
        with open(out_folder + props['name'], "wb") as out_f:
            out_f.write(file_bytes)
            out_f.close()
    f.close()

print("Extraction complete!")
