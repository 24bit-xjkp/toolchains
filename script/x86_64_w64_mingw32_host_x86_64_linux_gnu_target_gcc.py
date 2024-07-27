#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
from x86_64_w64_mingw32_native_gcc import build_gdb_requirements
from x86_64_w64_mingw32_host_arm_none_eabi_target_gcc import copy_lib
import os

env = gcc.environment(host="x86_64-w64-mingw32", target="x86_64-linux-gnu")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--disable-multilib --enable-languages=c,c++"
    binutils_option = f"--with-system-gdbinit={env.gdbinit_path} --disable-gdbserver --with-python={env.python_config_path} CXXFLAGS=-D_WIN32_WINNT=0x0600"
    glibc_option = f"--prefix={env.lib_prefix} --host={env.target} --build={env.build} --disable-werror"

    # 编译安装完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install("install-strip")

    # 安装Linux头文件
    env.enter_build_dir("linux")
    env.make(f"ARCH=x86 INSTALL_HDR_PATH={env.lib_prefix} headers_install")

    # 安装glibc头文件
    env.enter_build_dir("glibc")
    env.configure(glibc_option, "libc_cv_forced_unwind=yes")
    env.make("install-headers")
    os.mknod(os.path.join(env.lib_prefix, "include", "gnu", "stubs.h"))

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

    # 打包工具链
    env.package(need_python_embed_package=True)


if __name__ == "__main__":
    build()
