#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import x86_64_linux_gnu_native_gcc as native_gcc
import os
import shutil

env = gcc.environment("14", target="arm-none-eabi")


def copy_lib(env: gcc.environment = env) -> None:
    """从x86_64-linux-gnu本地工具链中复制运行库"""
    for dll in ("libstdc++.so.6", "libgcc_s.so.1"):
        shutil.copy(os.path.join(native_gcc.env.rpath_dir, dll), env.rpath_dir)


def copy_pretty_printer(env: gcc.environment = env) -> None:
    """从x86_64-linux-gnu本地工具链中复制pretty-printer"""
    for dir in os.listdir(native_gcc.env.share_dir):
        src_dir = os.path.join(native_gcc.env.share_dir, dir)
        dst_dir = os.path.join(env.share_dir, dir)
        if dir[0:3] == "gcc" and os.path.isdir(src_dir):
            shutil.copytree(src_dir, dst_dir)
            return


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --enable-nls --target={env.target} --prefix={env.prefix}"
    gcc_option = "--enable-multilib --enable-languages=c,c++"

    # 编译安装binutils和gdb
    env.enter_build_dir("binutils")
    os.environ["ORIGIN"] = "$$ORIGIN"
    env.configure(basic_option, f"--with-system-gdbinit={env.gdbinit_path} LDFLAGS={env.rpath_option} --enable-gold")
    env.make()
    env.install()
    del os.environ["ORIGIN"]
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 编译安装gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option, *gcc.disable_hosted_option)
    env.make()
    env.install()

    # 复制gdb所需运行库
    copy_lib()
    # 复制pretty-printer
    copy_pretty_printer()

    # 打包工具链
    env.package()


if __name__ == "__main__":
    build()
