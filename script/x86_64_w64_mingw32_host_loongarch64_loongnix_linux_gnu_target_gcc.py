#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
from x86_64_w64_mingw32_native_gcc import build_gdb_requirements

env = gcc.environment(host="x86_64-w64-mingw32", target="loongarch64-loongnix-linux-gnu")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--disable-multilib --enable-languages=c,c++ --disable-libsanitizer"
    binutils_option = f"--with-system-gdbinit={env.gdbinit_path} --disable-gdbserver --with-python={env.python_config_path} CXXFLAGS=-D_WIN32_WINNT=0x0600"

    # 编译安装完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install("install-strip")

    # 创建libpython.a
    env.build_libpython()
    # 编译安装libgmp, libexpat, libiconv, libmpfr
    lib_option = build_gdb_requirements()

    # 编译安装binutils和gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, *lib_option, binutils_option)
    env.make()
    env.install()

    # 复制文件
    env.copy_from_cross_toolchain()

    # 打包工具链
    env.package(need_python_embed_package=True)


if __name__ == "__main__":
    build()
