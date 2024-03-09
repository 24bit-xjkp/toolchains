#!/usr/bin/python3
# -*- coding: utf-8 -*-
import llvm_environment as llvm

env = llvm.environment("19", "x86_64-linux-gnu")


def build(stage: int = env.stage) -> None:
    env.stage = stage
    if env.stage == 1:
        env.config(**{**llvm.dylib_option_list, **llvm.llvm_option_list_1})
        env.make()
        env.install()
        env.remove_build_dir()
        env.stage += 1
    if env.stage == 2:
        env.config("-stdlib=libcxx -unwindlib=libunwind -rtlib=compiler-rt", **{**llvm.dylib_option_list, **llvm.llvm_option_list_2})
        env.make()
        env.install()


if __name__ == "__main__":
    build()
