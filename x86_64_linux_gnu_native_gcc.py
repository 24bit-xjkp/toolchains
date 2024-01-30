#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import os

env = gcc.environment("14")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --enable-nls --prefix={env.prefix}"
    # 编译gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, "--disable-bootstrap --enable-multilib --enable-languages=c,c++")
    env.make()
    env.install()
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 编译binutils
    env.enter_build_dir("binutils")
    os.environ["ORIGIN"] = "$$ORIGIN"
    env.configure(basic_option, f"--with-system-gdbinit={env.gdbinit_path} LDFLAGS={gcc.rpath_lib} --enable-gold")
    env.make()
    env.install()
    del os.environ["ORIGIN"]
    env.package()


if __name__ == "__main__":
    build()
