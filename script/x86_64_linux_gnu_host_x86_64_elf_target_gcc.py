#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
from x86_64_linux_gnu_host_arm_none_eabi_target_gcc import copy_lib
from x86_64_linux_gnu_host_arm_none_eabi_target_gcc import copy_pretty_printer

env = gcc.environment("14", target="x86_64-elf")


def build() -> None:
    # 更新源代码
    # env.update()
    
    basic_option = f"--disable-werror --enable-nls --target={env.target} --prefix={env.prefix}"
    gcc_option = "--disable-multilib --enable-languages=c,c++"

    # 编译安装binutils和gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, f"--with-system-gdbinit={env.gdbinit_path} LDFLAGS={env.rpath_option} --enable-gold")
    env.make()
    env.install()
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    env.register_in_bashrc()

    # 编译安装gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option, *gcc.disable_hosted_option)
    env.make()
    env.install()

    # 复制gdb所需运行库
    copy_lib(env)
    # 复制pretty-printer
    copy_pretty_printer(env)

    # 打包工具链
    env.package()


if __name__ == "__main__":
    build()
