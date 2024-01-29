#!/usr/bin/python3
import gcc_environment as gcc
import os

env = gcc.environment("14")
env.update()
# 编译gcc
env.enter_build_dir("gcc")
os.system(f"../configure --disable-werror --enable-multilib --enable-languages=c,c++ --disable-bootstrap --enable-nls --prefix={env.prefix}")
env.make()
env.install()
# 编译binutils
env.enter_build_dir("binutils")
os.environ["ORIGIN"] = "$$ORIGIN"
os.system(f"../configure --prefix={env.prefix} --disable-werror --enable-nls --with-system-gdbinit={env.prefix}/share/.gdbinit LDFLAGS=\"-Wl,-rpath='$ORIGIN'/../lib64\"")
env.make()
env.install()
del os.environ["ORIGIN"]
env.package()
