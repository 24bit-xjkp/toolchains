#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
from x86_64_linux_gnu_host_i686_w64_mingw32_target_gcc import env as cross_env
import shutil
import os

env = gcc.environment(host="x86_64-w64-mingw32", target="i686-w64-mingw32")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--disable-multilib --enable-languages=c,c++ --disable-sjlj-exceptions --enable-threads=win32"

    # 编译安装完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install("install-strip")

    # 删除已安装的dll
    os.chdir(env.bin_dir)
    for file in os.listdir(env.bin_dir):
        if file.endswith(".dll"):
            os.remove(file)
    # 从交叉工具链复制文件
    for dir in ("include", "lib"):
        cross_dir = os.path.join(cross_env.lib_prefix, dir)
        current_dir = os.path.join(env.lib_prefix, dir)
        for item in os.listdir(cross_dir):
            dst_path = os.path.join(current_dir, item)
            src_path = os.path.join(cross_dir, item)
            if not os.path.exists(dst_path):
                shutil.copytree(src_path, dst_path) if os.path.isdir(src_path) else shutil.copyfile(src_path, dst_path)

    # 编译安装binutils
    env.enter_build_dir("binutils")
    env.configure(basic_option, "--disable-gdb")
    env.make()
    env.install()

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
