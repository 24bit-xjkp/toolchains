#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import os
from x86_64_linux_gnu_host_arm_none_eabi_target_gcc import copy_lib

env = gcc.environment(target="riscv64-linux-gnu")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --enable-nls --target={env.target} --prefix={env.prefix}"
    glibc_option = f"--prefix={env.lib_prefix} --host={env.target} --build={env.build} --disable-werror"
    gcc_option = "--disable-bootstrap --disable-multilib --enable-languages=c,c++"

    # 编译binutils和gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, f"--enable-gdb --disable-gdbserver --with-system-gdbinit={env.gdbinit_path} LDFLAGS={env.rpath_option}")
    env.make()
    env.install()

    # 编译gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option, "--disable-shared")
    env.make("all-gcc")
    env.install("install-strip-gcc")
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 安装Linux头文件
    env.enter_build_dir("linux")
    env.make(f"ARCH=riscv INSTALL_HDR_PATH={env.lib_prefix} headers_install")

    # 安装glibc头文件
    env.enter_build_dir("glibc")
    env.configure(glibc_option, "libc_cv_forced_unwind=yes")
    env.make("install-headers")
    os.mknod(os.path.join(env.lib_prefix, "include", "gnu", "stubs.h"))

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
    env.configure(basic_option, gcc_option)
    env.make()
    env.install("install-strip")

    # 编译gdbserver
    env.solve_libgcc_limits()
    env.enter_build_dir("binutils")
    env.configure(basic_option, f"--disable-gdb --host={env.target} --enable-gdbserver --disable-binutils")
    env.make()
    env.install("install-strip-gdbserver")

    # 复制gdb所需运行库
    copy_lib(env)

    # 打包工具链
    env.package()


if __name__ == "__main__":
    build()
