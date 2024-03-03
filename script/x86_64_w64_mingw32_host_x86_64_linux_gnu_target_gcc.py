#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import shutil
import os

env = gcc.environment("14", host="x86_64-w64-mingw32", target="x86_64-linux-gnu")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--disable-multilib --enable-languages=c,c++"

    # 编译安装完整gcc
    """ env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install("install-strip")

    # 编译安装binutils
    env.enter_build_dir("binutils")
    env.configure(basic_option, "--disable-gdb")
    env.make()
    env.install()

    # 安装Linux头文件
    env.enter_build_dir("linux")
    env.make(f"ARCH=x86 INSTALL_HDR_PATH={env.lib_prefix} headers_install")

    # 安装glibc
    env.enter_build_dir("glibc")
    env.configure(f"--disable-werror --host={env.target} --prefix={env.lib_prefix} --build={env.build}")
    env.make()
    env.install("install")
    env.adjust_glibc() """

    # 打包工具链
    env.package(False)


if __name__ == "__main__":
    build()
