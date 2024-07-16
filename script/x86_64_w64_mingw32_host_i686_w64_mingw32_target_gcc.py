#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
from x86_64_w64_mingw32_native_gcc import build_gdb_requirements
import os
from x86_64_w64_mingw32_host_arm_none_eabi_target_gcc import copy_lib

env = gcc.environment(host="x86_64-w64-mingw32", target="i686-w64-mingw32")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--disable-multilib --enable-languages=c,c++ --disable-sjlj-exceptions --enable-threads=win32"
    binutils_option = f"--with-system-gdbinit={env.gdbinit_path} --disable-gdbserver --with-python={env.python_config_path} CXXFLAGS=-D_WIN32_WINNT=0x0600"

    # 编译安装完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install("install-strip")

    # 删除已安装的dll
    for file in filter(lambda x: x.endswith(".dll"), os.listdir(env.bin_dir)):
        gcc.remove(os.path.join(env.bin_dir, file))

    # 创建libpython.a
    env.build_libpython()
    # 编译安装libgmp, libexpat, libiconv, libmpfr
    lib_option = build_gdb_requirements()

    # 编译安装binutils和gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, *lib_option, binutils_option)
    env.make()
    env.install()

    # 复制gdb所需运行库
    copy_lib(env)
    # 复制文件
    env.copy_from_cross_toolchain()

    # 编译安装pexports
    env.enter_build_dir("pexports")
    env.configure(f"--prefix={env.prefix} --host={env.host}")
    env.make()
    env.install()
    # 添加target前缀
    os.rename(os.path.join(env.bin_dir, "pexports.exe"), os.path.join(env.bin_dir, f"{env.target}-pexports.exe"))
    # 打包工具链
    env.package(False)


if __name__ == "__main__":
    build()
