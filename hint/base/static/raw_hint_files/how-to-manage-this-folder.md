This directory contains the raw HINT files by year and month. For the GUI to
correctly display and link to these files, there are some rules that need to be
followed when moving/copying files into this directory.

# Directory names

All directories must follow the following naming convention: `<year>-<month>`.
For example `2024-03` or `2023-12`. Directories with `month` outside the
`01-12` range, or with the `year`, `month` pair above the current date will be
IGNORED by the GUI, and files will NOT be listed.

# File names

ONLY files with a species name included in the database will be displayed. The
matching is done using `Organisms.get_filename_prefix` from the `models.py` 
script, if no organism matches a files, it will not be displayed in the GUI.
Also, only files with names ending in the following terminations will be used:
* `binary_all.txt`
* `binary_hq.txt`
* `both_all.txt`
* `both_hq.txt`
* `cocomp_all.txt`
* `cocomp_hq.txt`

Any other file will NOT be displayed and won't be accessible to users of
HINT-web. 
