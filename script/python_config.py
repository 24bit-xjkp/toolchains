#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from gcc_environment import environment


def get_config() -> None:
    assert len(sys.argv) >= 3, "Too few args"
    env = environment()
    python_dir = env.lib_dir_list["python-embed"]
    result_list = {
        "--includes": f"-I{os.path.join(python_dir, 'include')}",
        "--ldflags": f"-L{python_dir} -lpython",
        "--exec-prefix": f"-L{python_dir}",
    }
    option_list = sys.argv[2:]
    for option in option_list:
        if option in result_list:
            print(result_list[option])
            return
    assert False, f'Invalid option list: {" ".join(option_list)}'


if __name__ == "__main__":
    get_config()
