import typing

from . import common
from .build_gcc_source import gcc_support_platform_list
from .llvm_environment import llvm_environment, build_llvm_environment, runtime_family


class modifier_list:
    """针对特定平台修改llvm构建环境的回调函数"""

    @staticmethod
    def arm_linux_gnueabi(env: llvm_environment) -> None:
        env.runtime_build_options["arm-linux-gnueabi"].basic_option += "-match=armv7-a"

    @staticmethod
    def arm_linux_gnueabihf(env: llvm_environment) -> None:
        env.runtime_build_options["arm-linux-gnueabihf"].basic_option += "-match=armv7-a"

    @staticmethod
    def loongarch64_loongnix_linux_gnu(env: llvm_environment) -> None:
        env.runtime_build_options["loongarch64-loongnix-linux-gnu"].cmake_option.update(
            {"COMPILER_RT_BUILD_SANITIZERS": "OFF", "COMPILER_RT_BUILD_GWP_ASAN": "OFF"}
        )

    @staticmethod
    def modify(env: llvm_environment, targets: list[str]) -> None:
        for target in targets:
            target = target.replace("-", "_")
            if modifier := getattr(modifier_list, target, None):
                modifier(env)


def generate_target_list_from_gcc() -> tuple[list[str], list[str]]:
    """从gcc目标列表中获取目标

    Returns:
        tuple[list[str], list[str]]: (宿主平台列表, 独立平台列表)
    """

    phony_triplet = "phony-phony-phony"
    hosted_list: list[str] = []
    freestanding_list: list[str] = []

    for target in gcc_support_platform_list.target_list:
        toolchain_type = common.toolchain_type.classify_toolchain(phony_triplet, phony_triplet, target)
        if toolchain_type.contain(common.toolchain_type.freestanding):
            freestanding_list.append(target)
        else:
            hosted_list.append(target)

    return hosted_list, freestanding_list


class llvm_support_platform_list:
    """受支持的平台列表

    Attributes:
        host_list  : 支持的LLVM工具链宿主平台
        arch_list: 支持的LLVM目标平台
        project_list: 支持的子项目
        runtime_list: 支持的运行时库
        hosted_list: gcc支持的宿主平台
        freestanding_list: gcc支持的独立平台
        target_list: 支持的runtimes的target列表
    """

    host_list: typing.Final[list[str]] = gcc_support_platform_list.host_list
    arch_list: typing.Final[list[str]] = ["X86", "AArch64", "RISCV", "ARM", "LoongArch", "Mips"]
    project_list: typing.Final[list[str]] = ["clang", "clang-tools-extra", "lld", "lldb", "bolt"]
    runtime_list: typing.Final[list[str]] = ["libcxx", "libcxxabi", "libunwind", "compiler-rt", "openmp"]
    hosted_list, freestanding_list = generate_target_list_from_gcc()
    target_list: typing.Final[list[str]] = [*hosted_list, "armv6m-none-eabi"]


class configure(common.basic_build_configure):
    """llvm构建配置"""

    toolchain_type: str = "LLVM"

    def __init__(self, **kwargs: typing.Any) -> None:
        """设置llvm构建配置

        Args:

        """

        super().__init__(**kwargs)


sysroot_config = common.basic_prefix_build_configure


__all__ = [
    "modifier_list",
    "llvm_support_platform_list",
    "configure",
    "llvm_environment",
    "build_llvm_environment",
    "runtime_family",
    "sysroot_config",
]
