#!/usr/bin/sh
current_file="$(readlink -f $0)"
current_dir="$(dirname $current_file)"
/usr/bin/env python3 "$current_dir/python_config.py" $@
