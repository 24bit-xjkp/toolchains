#!/usr/bin/python3
import gcc_environment as gcc
import os

env = gcc.environment("14", host="x86_64-w64-mingw32")


def build():
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--enable-multilib --enable-languages=c,c++ --disable-sjlj-exceptions --enable-threads=win32"
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install()


if __name__ == "__main__":
    build()
