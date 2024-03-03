#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import os

env = gcc.environment("14", target="i686-linux-gnu")


def build() -> None:
    basic_option = f"--disable-werror --enable-nls --prefix={env.prefix} --target={env.target}"
    glibc_option = f"--prefix={env.lib_prefix} --host={env.target} --build={env.build} --disable-werror"

    # 编译binutils
    env.enter_build_dir("binutils")
    env.configure(basic_option, "--disable-gdb")
    env.make()
    env.install()

    # 编译gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, "--disable-bootstrap --disable-multilib --enable-languages=c,c++ --disable-shared")
    env.make("all-gcc")
    env.install("install-strip-gcc")
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 安装Linux头文件
    env.enter_build_dir("linux")
    env.make(f"ARCH=x86 INSTALL_HDR_PATH={env.lib_prefix} headers_install")

    # 安装glibc头文件
    env.enter_build_dir("glibc")
    env.configure(glibc_option, "libc_cv_forced_unwind=yes")
    env.make("install-headers")
    with open(os.path.join(env.lib_prefix, "include", "gnu", "stubs.h"), "w+"):
        pass

    # 编译安装libgcc
    env.enter_build_dir("gcc", False)
    env.make("all-target-libgcc")
    env.install("install-strip-target-libgcc")

    # 编译安装glibc
    env.enter_build_dir("glibc")
    env.configure(glibc_option)
    env.make()
    env.install("install")
    env.adjust_glibc()

    # 编译完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, "--disable-bootstrap --disable-multilib --enable-languages=c,c++")
    env.make()
    env.install("install-strip")

    # 打包工具链
    env.package(False)


if __name__ == "__main__":
    build()
