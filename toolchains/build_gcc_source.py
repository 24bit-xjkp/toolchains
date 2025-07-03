import typing

from . import common
from .gcc_environment import build_gcc_environment


def get_freestanding_libstdcxx_option(*args: str) -> str:
    """获取独立环境下libstdcxx编译选项

    Args:
        *args (str): 额外选项

    Returns:
        str: 独立环境下libstdcxx编译选项
    """

    cxx_flags = ["-fno-exceptions", "-ffunction-sections", "-fdata-sections", "-O2", "-DNDEBUG", *args]

    return f"--enable-cxx-flags='{' '.join(cxx_flags)}'"


class modifier_list:
    """针对特定平台修改gcc构建环境的回调函数"""

    @staticmethod
    def arm_linux_gnueabi(env: build_gcc_environment) -> None:
        """针对arm-linux-gnueabi平台使用arm-sf的链接器脚本

        Args:
            env (build_gcc_environment): 当前gcc构建平台
        """

        env.adjust_glibc_arch = "arm-sf"

    @staticmethod
    def arm_linux_gnueabihf(env: build_gcc_environment) -> None:
        """针对arm-linux-gnueabihf平台使用arm-hf的链接器脚本

        Args:
            env (build_gcc_environment): 当前gcc构建平台
        """

        env.adjust_glibc_arch = "arm-hf"

    @staticmethod
    def loongarch64_loongnix_linux_gnu(env: build_gcc_environment) -> None:
        """针对loongarch64-loongnix-linux-gnu平台
        1. 使用loongarch64-loongnix的链接器脚本
        2. 使用预编译的glibc
        3. gcc添加--disable-libsanitizer选项

        Args:
            env (build_gcc_environment): 当前gcc构建平台
        """

        def build_gcc(build_env: build_gcc_environment) -> None:
            """loongarch64-loongnix-linux-gnu专业编译流程，跳过glibc编译

            Args:
                self (build_gcc_environment): gcc构建环境
            """

            env = build_env.env
            # 编译binutils，如果启用gdb则一并编译
            env.enter_build_dir("binutils")
            env.configure("binutils", *build_env.basic_option, *build_env.gdb_option)
            env.make()
            env.install()

            # 安装Linux头文件
            env.enter_build_dir("linux")
            env.make(*build_env.linux_option)

            # 复制glibc文件
            glibc_dir = env.home / "glibc-loongnix"
            for dir in ("include", "lib"):
                src_dir = glibc_dir / dir
                dst_dir = env.lib_prefix / dir
                for item in src_dir.iterdir():
                    common.copy(item, dst_dir / item.name)

            # 编译完整gcc
            env.enter_build_dir("gcc")
            env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
            build_gcc_environment.make_with_libbacktrace_patch(env)
            env.install()

            # 完成后续工作
            build_env.after_build_gcc()

        env.adjust_glibc_arch = "loongarch64-loongnix"
        # 若成功找到glibc-loongnix则直接从预编译包中复制
        if env.env.lib_dir_list["glibc"].name == "glibc-loongnix":
            env.full_build_linux = build_gcc  # type: ignore
        env.gcc_option.append("--disable-libsanitizer")

    @staticmethod
    def x86_64_w64_mingw32(env: build_gcc_environment) -> None:
        env.libc_option += ["--disable-lib32", "--enable-lib64"]

    @staticmethod
    def i686_w64_mingw32(env: build_gcc_environment) -> None:
        env.libc_option += ["--disable-lib64", "--enable-lib32"]

    @staticmethod
    def arm_none_eabi(env: build_gcc_environment) -> None:
        """arm嵌入式cpu大多使用armv7-m，只支持Thumb2

        Args:
            env (build_gcc_environment): 当前gcc构建平台
        """

        env.gcc_option += ["--with-mode=thumb", "--with-arch=armv7-m", get_freestanding_libstdcxx_option("-march=armv7-m")]

    @staticmethod
    def arm_nonewlib_none_eabi(env: build_gcc_environment) -> None:
        """arm嵌入式cpu大多使用armv7-m，只支持Thumb2

        Args:
            env (build_gcc_environment): 当前gcc构建平台
        """

        env.gcc_option += ["--with-mode=thumb", "--with-arch=armv7-m", get_freestanding_libstdcxx_option("-march=armv7-m")]

    @staticmethod
    def arm_fpv4_none_eabi(env: build_gcc_environment) -> None:
        """Thumb2+fpv4-sp-d16

        Args:
            env (build_gcc_environment): 当前gcc构建平台
        """

        env.gcc_option += [
            "--with-mode=thumb",
            "--with-arch=armv7-m",
            "--with-fpu=fpv4-sp-d16",
            "--with-float=hard",
            get_freestanding_libstdcxx_option("-march=armv7-m", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard"),
        ]
        env.libc_option += ['CFLAGS_FOR_TARGET="-march=armv7-m -mfpu=fpv4-sp-d16 -mfloat-abi=hard -O2 -ffunction-sections"']

    @staticmethod
    def modify(env: build_gcc_environment, target: str) -> None:
        target = target.replace("-", "_")
        if modifier := getattr(modifier_list, target, None):
            modifier(env)


class gcc_support_platform_list:
    """受支持的平台列表，不包含vendor字段

    Attributes:
        host_list  : 支持的GCC工具链宿主平台
        target_list: 支持的GCC工具链目标平台
    """

    host_list: typing.Final[list[str]] = ["x86_64-linux-gnu", "x86_64-w64-mingw32"]
    target_list: typing.Final[list[str]] = [
        "x86_64-linux-gnu",
        "i686-linux-gnu",
        "aarch64-linux-gnu",
        "arm-linux-gnueabi",
        "arm-linux-gnueabihf",
        "loongarch64-linux-gnu",
        "riscv64-linux-gnu",
        "riscv64-none-elf",
        "x86_64-w64-mingw32",
        "i686-w64-mingw32",
        "arm-none-eabi",
        "x86_64-elf",
        "mips64el-linux-gnuabi64",
    ]


class gcc_configure(common.basic_build_configure):
    """gcc构建配置"""

    gdb: bool
    gdbserver: bool
    newlib: bool
    nls: bool
    toolchain_type: str = "GCC"

    def __init__(self, gdb: bool = True, gdbserver: bool = True, newlib: bool = True, nls: bool = True, **kwargs: typing.Any) -> None:
        """设置gcc构建配置

        Args:
            gdb (bool, optional): 是否构建gdb. 默认为构建.
            gdbserver (bool, optional): 是否构建gdbserver. 默认为构建.
            newlib (bool, optional): 是否为独立工具链构建newlib. 默认为构建.
            nls (bool, optional): 是否启用nls. 默认为启用.
        """

        super().__init__(**kwargs)
        self.gdb = gdb
        self.gdbserver = gdbserver
        self.newlib = newlib
        self.nls = nls


def check_triplet(host: str, target: str) -> None:
    """检查输入triplet是否合法

    Args:
        host (str): 宿主平台
        target (str): 目标平台
    """

    for input_triplet, triplet_list, name in (
        (host, gcc_support_platform_list.host_list, "Host"),
        (target, gcc_support_platform_list.target_list, "Target"),
    ):
        input_triplet_field = common.triplet_field(input_triplet)
        for support_triplet in triplet_list:
            support_triplet_field = common.triplet_field(support_triplet)
            if input_triplet_field.weak_eq(support_triplet_field):
                break
        else:
            raise RuntimeError(common.toolchains_error(f'{name} "{input_triplet}" is not support.'))


__all__ = ["modifier_list", "gcc_support_platform_list", "gcc_configure", "build_gcc_environment", "check_triplet"]
