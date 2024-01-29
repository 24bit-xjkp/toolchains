#!/usr/bin/python3
import gcc_environment as gcc
import os

env = gcc.environment("14", target="x86_64-w64-mingw32")


def build() -> None:
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --enable-nls --target={env.target} --prefix={env.prefix}"
    gcc_option = "--enable-multilib --enable-languages=c,c++ --disable-sjlj-exceptions --enable-threads=win32"
    mingw_option = f"--host={env.target} --prefix={os.path.join(env.prefix, env.target)} --with-default-msvcrt=ucrt"
    # 编译binutils
    env.enter_build_dir("binutils")
    env.configure(basic_option, "--disable-gdb")
    env.make()
    env.install()
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 安装mingw-w64头文件
    env.enter_build_dir("mingw")
    env.configure(mingw_option, "--without-crt")
    env.install()

    # 编译gcc和libgcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option, "--disable-shared")
    env.make("all-gcc all-target-libgcc")
    env.install("install-strip-gcc install-strip-target-libgcc")

    # 编译完整mingw-w64
    env.enter_build_dir("mingw")
    env.configure(mingw_option)
    env.make()
    env.install()
    env.symlink_multilib()

    # 编译完整的gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install()
    env.delete_symlink()
    env.package(False)


if __name__ == "__main__":
    build()
