#!/usr/bin/python3
# -*- coding: utf-8 -*-
import llvm_environment as llvm
from sysroot import auto_build_sysroot

# 确保sysroot存在
auto_build_sysroot()
env = llvm.environment()


def build(stage: int = env.stage) -> None:
    env.stage = stage
    if env.stage == 1:
        env.config("llvm", env.host, **{**env.dylib_option_list, **env.llvm_option_list_1})
        env.make("llvm")
        env.install("llvm")
        env.remove_build_dir("llvm")
        for target in env.system_list.keys():
            match target:
                case "x86_64-w64-mingw32":
                    option = env.llvm_option_list_w64_1
                case "i686-w64-mingw32":
                    option = env.llvm_option_list_w32_1
                case _:
                    option = env.llvm_option_list_1
            env.config("runtimes", target, **option)
            env.make("runtimes")
            env.install("runtimes")
            env.build_sysroot(target)
            env.remove_build_dir("runtimes")
        env.stage += 1

    basic_command = ("-stdlib=libc++", "-unwindlib=libunwind", "-rtlib=compiler-rt")
    if env.stage == 2:
        env.config("llvm", env.host, *basic_command, **{**env.dylib_option_list, **env.llvm_option_list_2})
        env.make("llvm")
        env.install("llvm")
        env.copy_llvm_libs()
        env.stage += 1

    if env.stage == 3:
        for target in env.system_list.keys():
            command = basic_command
            match target:
                case "x86_64-w64-mingw32":
                    option = env.llvm_option_list_w64_3
                    command = (*basic_command, "-lgcc", "-lunwind,", "-lsupc++")
                case "i686-w64-mingw32":
                    option = env.llvm_option_list_w32_3
                    command = (*basic_command, "-lgcc", "-lunwind,", "-lsupc++")
                case _:
                    option = env.llvm_option_list_3
            env.config("runtimes", target, *command, **option)
            env.make("runtimes")
            env.install("runtimes")
            env.build_sysroot(target)
            env.remove_build_dir("runtimes")
        env.stage += 1

    if env.stage == 4:
        env.change_name()
        env.package()


if __name__ == "__main__":
    build()
