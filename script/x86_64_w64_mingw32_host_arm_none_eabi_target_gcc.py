#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import x86_64_linux_gnu_host_x86_64_w64_mingw32_target_gcc as native_gcc
from x86_64_linux_gnu_host_arm_none_eabi_target_gcc import copy_pretty_printer
from x86_64_w64_mingw32_native_gcc import build_gdb_requirements
import shutil
import os

env = gcc.environment(host="x86_64-w64-mingw32", target="arm-none-eabi")


def copy_lib(env: gcc.environment = env) -> None:
    """从x86_64-w64-mingw32交叉工具链中复制运行库"""
    for dll in ("libstdc++-6.dll", "libgcc_s_seh-1.dll"):
        shutil.copy(os.path.join(native_gcc.env.lib_prefix, "lib", dll), env.bin_dir)


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --disable-nls --host={env.host} --target={env.target} --prefix={env.prefix}"
    gcc_option = "--enable-multilib --enable-languages=c,c++"
    binutils_option = (
        f"--with-system-gdbinit={env.gdbinit_path} --with-python={env.python_config_path} CXXFLAGS=-D_WIN32_WINNT=0x0600 --enable-gold"
    )

    # 创建libpython.a
    env.build_libpython()

    # 编译安装libgmp, libexpat, libiconv, libmpfr
    lib_option = build_gdb_requirements(env)

    # 编译安装binutils和gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, *lib_option, binutils_option)
    env.make()
    env.install()

    # 编译安装gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option, *gcc.disable_hosted_option)
    env.make()
    env.install()

    # 复制gdb所需运行库
    copy_lib()
    # 复制pretty-printer
    copy_pretty_printer(env)

    # 打包工具链
    env.package(need_python_embed_package=True)


if __name__ == "__main__":
    build()
