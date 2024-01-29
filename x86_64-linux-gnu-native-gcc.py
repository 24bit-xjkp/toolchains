#!/usr/bin/python3
import gcc_environment as gcc
import os

env = gcc.environment("14")


def build() -> None:
    # 更新源代码
    # env.update()

    # 编译gcc
    env.enter_build_dir("gcc")
    gcc.run_command(f"../configure --disable-werror --enable-multilib --enable-languages=c,c++ --disable-bootstrap --enable-nls --prefix={env.prefix}")
    env.make()
    env.install()
    # 第一次编译时需要注册环境变量，运行完该脚本后可以source ~/.bashrc来加载环境变量
    # env.register_in_bashrc()

    # 编译binutils
    env.enter_build_dir("binutils")
    os.environ["ORIGIN"] = "$$ORIGIN"
    gcc.run_command(f"../configure --prefix={env.prefix} --disable-werror --enable-nls --with-system-gdbinit={env.prefix}/share/.gdbinit LDFLAGS=\"-Wl,-rpath='$ORIGIN'/../lib64\"")
    env.make()
    env.install()
    del os.environ["ORIGIN"]
    env.package()


if __name__ == "__main__":
    build()
