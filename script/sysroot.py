import os
from common import *
from llvm_environment import *
from importlib import import_module

env = environment(has_sysroot=False)

def need_build() -> bool:
    """是否需要创建原始sysroot

    Returns:
        bool: 是否需要调用build_origin_sysroot
    """
    return not os.path.exists(env.sysroot_dir)


def build_origin_sysroot() -> None:
    """创建原始sysroot，即只包含gnu相关库的sysroot，该函数会删除已存在的sysroot"""
    mkdir(env.sysroot_dir)
    # 只包含宿主工具链，因为libc++不支持独立目标
    script_list = [x[0] for x in filter(lambda x: x not in scripts.freestanding_script_list and x[1], scripts.cross_script_list)]
    # 原生工具链不具有linux header和glibc，转而从交叉工具链复制
    cross_target = "x86_64_w64_mingw32_host_x86_64_linux_gnu_target_gcc"
    if cross_target in scripts.canadian_cross_script_list:
        script_list.append(cross_target)
    for script in script_list:
        gcc = import_module(script).env
        if not os.path.exists(gcc.prefix):
            print(f"Cannot find gcc in {gcc.prefix}")
            continue
        # 不复制binutils和multilib
        for dir in filter(lambda x: x not in ("bin", "lib32"), os.listdir(gcc.lib_prefix)):
            copy(os.path.join(gcc.lib_prefix, dir), os.path.join(env.sysroot_dir, gcc.target, dir))
        libgcc_prefix = os.path.join("lib", "gcc", gcc.target, gcc.version)
        src_dir = os.path.join(gcc.prefix, libgcc_prefix)
        dst_dir = os.path.join(env.sysroot_dir, libgcc_prefix)
        mkdir(dst_dir)
        # 复制libgcc对应的.o .a文件和include文件夹
        for item in filter(lambda x: x.endswith((".o", ".a", "include")), os.listdir(src_dir)):
            copy(os.path.join(src_dir, item), os.path.join(dst_dir, item))


def auto_build_sysroot() -> None:
    """sysroot不存在则自动创建原始sysroot"""
    if need_build():
        build_origin_sysroot()


if __name__ == "__main__":
    build_origin_sysroot()
