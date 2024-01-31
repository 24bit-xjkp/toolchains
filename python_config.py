#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
from gcc_environment import environment

assert len(sys.argv) == 3, "Too many args." if len(sys.argv) > 3 else "Too few args"
option = sys.argv[2]
env = environment("")
python_dir = os.path.join(env.home_dir, "python-embed")

match option:
    case "--includes":
        print(f"-I{os.path.join(python_dir, 'include')}")
    case "--ldflags":
        print(f"-L{python_dir} -lpython")
    case "--exec-prefix":
        print(f"-L{python_dir}")
    case _:
        assert False, f'Invalid option "{option}"'
