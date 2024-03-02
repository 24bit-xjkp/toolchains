#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
from x86_64_linux_gnu_host_arm_none_eabi_target_gcc import copy_lib
from x86_64_w64_mingw32_native_gcc import build_gdb_requirements
import os
import shutil

env = gcc.environment("14", target="x86_64-ubuntu2004-linux-gnu")


def adjust_glibc(env: gcc.environment = env, is_32bit: bool = False) -> None:
    """调整安装好的glibc，包括剥离调试符号和替换链接器脚本"""
    lib_dir = os.path.join(env.lib_prefix, "lib")
    strip = f"{env.tool_prefix}strip"
    objcopy = f"{env.tool_prefix}objcopy"
    env.remove_unused_glibc_file()
    # 所有的动态库
    dll_list: list[str] = []
    for dll in ("libSegFault.so", "libmemusage.so", "libpcprofile.so"):
        dll_list.append(os.path.join(lib_dir, dll))
    for file in filter(lambda file: os.path.islink(os.path.join(lib_dir, file)), os.listdir(lib_dir)):
        file = os.path.join(lib_dir, file)
        while os.path.islink(file):
            file = os.path.join(lib_dir, os.readlink(file))
        if file not in dll_list:
            dll_list.append(file)
    # 剥离调试符号到独立的符号文件
    for dll in dll_list:
        debug = dll + ".debug"
        gcc.run_command(f"{objcopy} --only-keep-debug {dll} {debug}")
        gcc.run_command(f"{strip} {dll}")
        gcc.run_command(f"{objcopy} --add-gnu-debuglink={debug} {dll}")
    ldscript_list = ("libc.so",) if is_32bit else ("libc.so", "libm.a", "libm.so")
    ldscript_prefix = "i686-" if is_32bit else "x86_64-"
    # 替换链接器脚本
    for ldscript in ldscript_list:
        dst_file = os.path.join(lib_dir, ldscript)
        src_file = os.path.join(env.current_dir, f"{ldscript_prefix}{ldscript}")
        os.remove(dst_file)
        shutil.copyfile(src_file, dst_file)


def move_glibc32(env: gcc.environment = env) -> None:
    """移动32位glibc到lib32"""
    lib_dir = os.path.join(env.lib_prefix, "lib")
    lib32_dir = os.path.join(env.lib_prefix, "lib32")
    shutil.move(lib_dir, lib32_dir)
    os.mkdir(lib_dir)
    shutil.move(os.path.join(lib32_dir, "ldscripts"), lib_dir)


def move_glibc64(env: gcc.environment = env) -> None:
    """移动64位glibc到lib64"""
    lib_dir = os.path.join(env.lib_prefix, "lib")
    lib32_dir = os.path.join(env.lib_prefix, "lib32")
    lib64_dir = os.path.join(env.lib_prefix, "lib64")
    for file in os.listdir(lib_dir):
        lib_path = os.path.join(lib_dir, file)
        lib32_path = os.path.join(lib32_dir, file)
        lib64_path = os.path.join(lib64_dir, file)
        if os.path.exists(lib32_path) or file == "ld-linux-x86-64.so.2":
            shutil.move(lib_path, lib64_path)


def move_glibc32_2(env: gcc.environment = env) -> None:
    """再次移动32位glibc到lib"""
    lib_dir = os.path.join(env.lib_prefix, "lib")
    lib32_dir = os.path.join(env.lib_prefix, "lib32")
    for item in os.listdir(lib32_dir):
        shutil.move(os.path.join(lib32_dir, item), os.path.join(lib_dir, item))
    os.rmdir(lib32_dir)


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --enable-nls --target={env.target} --prefix={env.prefix}/old"
    gcc_option = "--enable-multilib --enable-languages=c,c++ --disable-bootstrap"
    glibc_options = f"--build={env.build} --prefix={env.lib_prefix} --disable-werror libc_cv_forced_unwind=yes"

    # 编译安装gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, f"--with-system-gdbinit={env.gdbinit_path} LDFLAGS={env.rpath_option} --disable-binutils")
    env.make()
    env.install()
    # 编译安装binutils
    env.enter_build_dir("binutils")
    env.configure(basic_option, "--enable-gold --disable-gdb")
    env.make()
    env.install()
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 安装linux头文件
    env.enter_build_dir("linux")
    env.make(f"ARCH=x86 INSTALL_HDR_PATH={env.lib_prefix} headers_install")

    # 安装glibc头文件
    env.enter_build_dir("glibc")
    env.configure(glibc_options)
    env.make("install-headers")
    # 创建include/gnu/stubs.h
    with open(os.path.join(env.lib_prefix, "include", "gnu", "stubs.h"), "a"):
        pass

    # 编译安装gcc和libgcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option, "--disable-shared")
    env.make("all-gcc", "all-target-libgcc")
    env.install("install-strip-gcc", "install-strip-target-libgcc")

    # 编译安装32位glibc
    env.enter_build_dir("glibc")
    env.configure(glibc_options, f'--host=i686-linux-gnu CC="{env.tool_prefix}gcc -m32" CXX="{env.tool_prefix}g++ -m32"')
    env.make()
    env.install("install")
    adjust_glibc(is_32bit=True)
    move_glibc32()
    # 编译安装64位glibc
    env.enter_build_dir("glibc")
    env.configure(glibc_options, f"--host={env.target}")
    env.make()
    env.install("install")
    adjust_glibc()
    # 为multilib建立软链接
    env.symlink_multilib()

    # 编译完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install()
    env.delete_symlink()
    env.strip_debug_symbol()

    # 重新移动glibc位置
    move_glibc64()
    move_glibc32_2()

    # 复制gdb所需运行库
    copy_lib(env)

    # 打包工具链
    env.package()


if __name__ == "__main__":
    build()
