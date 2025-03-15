from argparse import ArgumentParser
import typing

from . import common
from .build_gcc_source import gcc_support_platform_list
from .llvm_environment import llvm_environment, build_llvm_environment, runtime_family, cmake_generator


class modifier_list:
    """针对特定平台修改llvm构建环境的回调函数"""

    @staticmethod
    def arm_linux_gnueabi(env: llvm_environment) -> None:
        env.runtime_build_options["arm-linux-gnueabi"].basic_option.append("-march=armv7-a")

    @staticmethod
    def arm_linux_gnueabihf(env: llvm_environment) -> None:
        env.runtime_build_options["arm-linux-gnueabihf"].basic_option.append("-march=armv7-a")

    @staticmethod
    def loongarch64_loongnix_linux_gnu(env: llvm_environment) -> None:
        env.runtime_build_options["loongarch64-loongnix-linux-gnu"].cmake_option.update(
            {
                "COMPILER_RT_BUILD_SANITIZERS": "OFF",
                "COMPILER_RT_BUILD_GWP_ASAN": "OFF",
                "COMPILER_RT_BUILD_XRAY": "OFF",
                "COMPILER_RT_BUILD_MEMPROF": "OFF",
                "COMPILER_RT_BUILD_CTX_PROFILE": "OFF",
            }
        )

    @staticmethod
    def armv7m_none_eabi(env: llvm_environment) -> None:
        env.sysroot_dir["armv7m-none-eabi"] = env.prefix_dir / "sysroot" / "armv7m-none-eabi"
        env.generator_list["armv7m-none-eabi"] = cmake_generator.make

    @staticmethod
    def modify(env: llvm_environment, targets: list[str]) -> None:
        for target in targets:
            target = target.replace("-", "_")
            if modifier := getattr(modifier_list, target, None):
                modifier(env)


def generate_hosted_list_from_gcc() -> list[str]:
    """从gcc目标列表中获取目标

    Returns:
        list[str]: 宿主平台列表
    """

    phony_triplet = "phony-phony-phony"
    hosted_list: list[str] = []
    unsupported_list: list[str] = ["mips64el-linux-gnuabi64"]

    for target in gcc_support_platform_list.target_list:
        toolchain_type = common.toolchain_type.classify_toolchain(phony_triplet, phony_triplet, target)
        if toolchain_type.contain(common.toolchain_type.hosted) and target not in unsupported_list:
            hosted_list.append(target)

    return hosted_list


class llvm_support_platform_list:
    """受支持的平台列表

    Attributes:
        host_list  : 支持的LLVM工具链宿主平台
        arch_list: 支持的LLVM目标平台
        project_list: 支持的子项目
        runtime_list: 支持的运行时库
        target_list: 支持的runtimes的target列表
    """

    host_list: typing.Final[list[str]] = gcc_support_platform_list.host_list
    arch_list: typing.Final[list[str]] = ["X86", "AArch64", "RISCV", "ARM", "LoongArch", "Mips"]
    project_list: typing.Final[list[str]] = ["clang", "clang-tools-extra", "lld", "lldb", "bolt", "mlir"]
    runtime_list: typing.Final[list[str]] = ["libcxx", "libcxxabi", "libunwind", "compiler-rt", "openmp"]
    target_list: typing.Final[list[str]] = [*generate_hosted_list_from_gcc(), "loongarch64-loongnix-linux-gnu", "armv7m-none-eabi"]


class configure(common.basic_build_configure):
    """llvm构建配置"""

    toolchain_type: str = "LLVM"
    default_generator: cmake_generator

    def __init__(self, default_generator: str = cmake_generator.ninja, **kwargs: typing.Any) -> None:
        """设置llvm构建配置

        Args:

        """

        super().__init__(**kwargs)
        self.default_generator = cmake_generator[default_generator]

    @classmethod
    def add_argument(cls, parser: ArgumentParser) -> None:
        super().add_argument(parser)

        default_config = configure()
        parser.add_argument(
            "--generator",
            "-g",
            type=str,
            help="The generator to use when build projects with cmake.",
            dest="default_generator",
            default=default_config.default_generator,
            choices=cmake_generator,
        )


sysroot_config = common.basic_prefix_build_configure


__all__ = [
    "modifier_list",
    "llvm_support_platform_list",
    "configure",
    "llvm_environment",
    "build_llvm_environment",
    "runtime_family",
    "cmake_generator",
    "sysroot_config",
]
