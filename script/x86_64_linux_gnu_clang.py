#!/usr/bin/python3
# -*- coding: utf-8 -*-
import llvm_environment as llvm

env = llvm.environment("19", "x86_64-linux-gnu")


def build(stage: int = env.stage) -> None:
    env.stage = stage
    if env.stage == 1:
        env.config("llvm", env.host, **{**env.dylib_option_list, **env.llvm_option_list_1})
        env.make("llvm")
        env.install("llvm")
        env.remove_build_dir("llvm")
        for target, _ in llvm.system_list:
            if target == env.host:
                continue
            match target:
                case "x86_64-w64-mingw32":
                    option = env.llvm_option_list_w64_1
                case "i686-w64-mingw32":
                    option = env.llvm_option_list_w32_1
                case "loongarch64-linux-gnu":
                    option = env.llvm_option_list_la_1
                case _:
                    option = env.llvm_option_list_1
            env.config("runtimes", env.host, **option)
            env.make("runtimes")
            env.install("runtimes")
            env.build_sysroot(target)
            env.remove_build_dir("runtimes")

    if env.stage == 2:
        env.config("llvm", env.host, "-stdlib=libcxx -unwindlib=libunwind -rtlib=compiler-rt", **{**env.dylib_option_list, **env.llvm_option_list_2})
        env.make("llvm")
        env.install("llvm")


if __name__ == "__main__":
    build()
