#!/usr/bin/python3
# -*- coding: utf-8 -*-
import llvm_environment as llvm
import os

env = llvm.environment("19", "x86_64-linux-gnu")


def build() -> None:
    env.config("llvm", env.host, **llvm.dylib_option_list)
    env.build("llvm")
    env.install("llvm")
    default_command = ("-stdlib=libstdc++", "-rtlib=libgcc", "-unwind=libgcc")
    for target in llvm.target_list:
        for lib in llvm.llvm_lib_list:
            env.config(lib, target, *default_command, **{"CMAKE_BUILD_WITH_INSTALL_RPATH": "ON"})
            env.build(lib)
            env.install(lib)
        for lib in llvm.llvm_lib_list:
            env.config(lib, target, **{"CMAKE_BUILD_WITH_INSTALL_RPATH": "ON"})
            env.build(lib)
            env.install(lib)


if __name__ == "__main__":
    build()
