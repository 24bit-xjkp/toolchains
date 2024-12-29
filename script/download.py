#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import argparse
from typing import Any, Callable
import common
import subprocess
import enum
import packaging.version as version

PYTHON_VERSION = "3.13.1"


def _exist_echo(lib: str) -> None:
    print(f"[toolchains] Lib {lib} exists, skip download.")


def _up_to_date_echo(lib: str) -> None:
    print(f"[toolchains] Lib {lib} is up to date, skip update.")


class git_clone_type(enum.IntEnum):
    """git克隆类型"""

    partial = enum.auto()  # 部分克隆
    shallow = enum.auto()  # 浅克隆
    full = enum.auto()  # 完全克隆


class git_url:
    remote: str  # 托管平台
    path: str  # git路径

    def __init__(self, remote: str, path: str) -> None:
        self.remote = remote
        self.path = path

    def get_url(self, prefer_ssh: bool) -> str:
        """获取git仓库的url

        Args:
            prefer_ssh (bool): 是否倾向于使用ssh
        """
        use_ssh = prefer_ssh and self.remote == "github.com"
        return f"git@{self.remote}:{self.path}" if use_ssh else f"https://{self.remote}/{self.path}"


class environment:
    glibc_version: str  # glibc版本号
    home: str  # 主目录
    clone_type: git_clone_type  # 是否使用部分克隆
    shallow_clone_depth: int  # 浅克隆深度
    github_use_ssh: bool  # 使用ssh克隆托管在github上的代码
    extra_lib_list: list[str]  # 其他非git托管包
    necessary_extra_lib_list: set[str] = {"python-embed"}  # 必须的非git托管包

    def __init__(
        self,
        glibc_version: str,
        home: str,
        clone_type: git_clone_type,
        shallow_clone_depth: int,
        github_use_ssh: bool,
        extra_lib_list: list[str],
    ) -> None:
        self.glibc_version = glibc_version
        self.home = home
        self.clone_type = clone_type
        self.shallow_clone_depth = shallow_clone_depth
        self.github_use_ssh = github_use_ssh
        self.extra_lib_list = [*self.necessary_extra_lib_list, *extra_lib_list]


class extra_lib:
    url_list: dict[str, str]  # 各个资源列表，dict[下载后文件名, url]
    path_to_check: list[str]  # 检查包是否存在时使用的路径列表

    def __init__(self, url_list: dict[str, str], path_to_check: list[str]) -> None:
        self.url_list = url_list
        self.path_to_check = path_to_check

    def check_exist(self, env: environment) -> bool:
        """检查包是否存在

        Args:
            env (environment): 源代码下载环境
        """
        for path in self.path_to_check:
            if not os.path.exists(os.path.join(env.home, path)):
                return False
        else:
            return True


system_lib_list: list[str] = [
    "bison",
    "flex",
    "texinfo",
    "make",
    "automake",
    "autoconf",
    "libtool",
    "git",
    "gcc",
    "g++",
    "gcc-multilib",
    "g++-multilib",
    "python3",
    "tar",
    "xz-utils",
    "unzip",
    "libgmp-dev",
    "libmpfr-dev",
    "zlib1g-dev",
    "libexpat1-dev",
    "gawk",
    "bzip2",
    "cmake",
    "ninja-build",
    "clang",
    "lld",
    "libxml2-dev",
    "zlib1g-dev",
]
git_lib_list: dict[str, git_url] = {
    "gcc": git_url("github.com", "gcc-mirror/gcc.git"),
    "binutils": git_url("github.com", "bminor/binutils-gdb.git"),
    "mingw": git_url("github.com", "mirror/mingw-w64.git"),
    "expat": git_url("github.com", "libexpat/libexpat.git"),
    "linux": git_url("github.com", "torvalds/linux.git"),
    "glibc": git_url("github.com", "bminor/glibc.git"),
    "pexports": git_url("github.com", "bocke/pexports.git"),
    "zlib": git_url("github.com", "madler/zlib.git"),
    "libxml2": git_url("github.com", "GNOME/libxml2.git"),
    "newlib": git_url("github.com", "bminor/newlib.git"),
    "llvm": git_url("github.com", "llvm/llvm-project.git"),
}
# TODO:处理libiconv
extra_lib_list: dict[str, extra_lib] = {
    "python-embed": extra_lib(
        {
            "python-embed.zip": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",
            "python_source.tar.xz": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/Python-{PYTHON_VERSION}.tar.xz",
        },
        ["python-embed"],
    ),
    "loongnix": extra_lib(
        {
            "linux-loongnix.tar.gz": "https://pkg.loongnix.cn/loongnix/pool/main/l/linux/linux_4.19.190.8.22.orig.tar.gz",
            "glibc-loongnix.tar.gz": "https://pkg.loongnix.cn/loongnix/pool/main/g/glibc/glibc_2.28.orig.tar.gz",
        },
        ["linux-loongnix", "glibc-loongnix"],
    ),
}
optional_extra_lib_list: set[str] = {lib for lib in extra_lib_list} - environment.necessary_extra_lib_list
extra_git_options_list: dict[str, Callable[["environment"], Any]] = {}
after_download_list: dict[str, Callable[["environment"], Any]] = {}
_globals_dict = globals()


def register(fn: Callable[["environment"], Any]):
    """注册函数到指定表中，对于函数key_table，有table[key]=key_table

    Args:
        fn (Callable[["environment"], None]): 要注册的函数

    Note:
        python会替换为python-embed
    """

    name: str = fn.__name__
    name = name.replace("python", "python-embed")
    name, table_name = name.split("_", 1)
    table_name += "_list"
    _globals_dict[table_name][name] = fn
    return fn


@register
def expat_after_download(env: environment) -> None:
    os.chdir(os.path.join(env.home, "expat", "expat"))
    common.run_command("./buildconf.sh")
    os.chdir(env.home)


@register
def pexports_after_download(env: environment) -> None:
    os.chdir(os.path.join(env.home, "pexports"))
    common.run_command("autoreconf -if")
    os.chdir(env.home)


@register
def python_after_download(env: environment) -> None:
    python_embed_zip = os.path.join(env.home, "python-embed.zip")
    python_source_txz = os.path.join(env.home, "python_source.tar.xz")
    python_source = os.path.join(env.home, "python_source")
    python_embed = os.path.join(env.home, "python-embed")

    # 解压embed包
    common.run_command(f"unzip -o {python_embed_zip}  python3*.dll python3*.zip *._pth -d {python_embed} -x python3.dll")
    common.remove(python_embed_zip)
    # 解压源代码包
    common.run_command(f"tar -xaf {python_source_txz}")
    os.rename(f"Python-{PYTHON_VERSION}", python_source)
    common.remove(python_source_txz)

    # 复制头文件
    include_dir: str = os.path.join(python_embed, "include")
    common.copy(os.path.join(python_source, "Include"), include_dir)
    common.copy(os.path.join(python_source, "PC", "pyconfig.h.in"), os.path.join(include_dir, "pyconfig.h"))

    # 记录python版本号
    with open(os.path.join(python_embed, "version"), "w") as file:
        file.write(PYTHON_VERSION)
    common.remove(python_source)


@register
def loongnix_after_download(env: environment) -> None:
    for lib in extra_lib_list["loongnix"].url_list:
        top_dir_option = f"-C {os.path.join(env.home), "linux-loongnix" if lib.startswith("linux") else env.home}"
        common.run_command(f"tar -xaf {lib} {top_dir_option}")
        common.remove(lib)

    os.rename(os.path.join(env.home, "glibc-2.28"), os.path.join(env.home, "glibc-loongnix"))


@register
def glibc_extra_git_options(env: environment) -> list[str]:
    return [f"-b release/{env.glibc_version}/master"]


def copy_gmp_mpfr(env: environment, lib: str) -> None:
    """从gcc contrib中欧复制gmp或mpfr

    Args:
        lib (str): 要复制的库
    """
    common.copy(os.path.join(env.home, "gcc", lib), os.path.join(env.home, lib), follow_symlinks=True)


def download_gcc_contrib(env: environment) -> None:
    """下载gcc的依赖包

    Args:
        env (environment): 源代码下载环境
    """
    os.chdir(os.path.join(env.home, "gcc"))
    common.run_command("contrib/download_prerequisites")
    os.chdir(env.home)


def after_download(env: environment, lib_downloaded: list[str]) -> None:
    """执行下载后的回调函数

    Args:
        env (environment): 源代码下载环境
        lib_downloaded (list[str]): 已下载包列表
    """
    for lib in lib_downloaded:
        if lib in after_download_list:
            after_download_list[lib](env)


def download_specific_extra_lib(env: environment, lib: str) -> None:
    """下载指定的非git托管包

    Args:
        env (environment): 源代码下载环境
        lib (str): 要下载的包
    """
    assert lib in extra_lib_list, f"Unknown extra lib: {lib}"
    extra_lib_v = extra_lib_list[lib]
    for lib, url in extra_lib_v.url_list.items():
        common.run_command(f"wget {url} -O {os.path.join(env.home, lib)}")


def download_source(env: environment) -> list[str]:
    """下载不存在的源代码，不会更新已有源代码

    Args:
        env (environment): 源代码下载环境

    Returns:
        list[str]: 已下载的包列表
    """
    os.chdir(env.home)
    lib_downloaded: list[str] = []
    # 下载git托管的源代码
    for lib, url_fields in git_lib_list.items():
        if not os.path.exists(lib):
            url = url_fields.get_url(env.github_use_ssh)
            extra_options: list[str] = extra_git_options_list[lib](env) if lib in extra_git_options_list else []
            match (env.clone_type):
                case git_clone_type.partial:
                    extra_options.append("--filter=blob:none")
                case git_clone_type.shallow:
                    extra_options.append(f"--depth={env.shallow_clone_depth}")
            extra_option = " ".join(extra_options)
            common.run_command(f"git clone {url} {extra_option} {lib}")
            lib_downloaded.append(lib)
        else:
            _exist_echo(lib)

    # 下载非git托管代码
    for lib in env.extra_lib_list:
        assert lib in extra_lib_list, f"Unknown extra lib: {lib}"
        if not extra_lib_list[lib].check_exist(env):
            download_specific_extra_lib(env, lib)
            lib_downloaded.append(lib)
    else:
        _exist_echo(lib)
    for lib in ("gmp", "mpfr", "isl", "mpc"):
        if not os.path.exists(os.path.join("gcc", lib)):
            download_gcc_contrib(env)
            break
    else:
        _exist_echo("gcc_contrib")
    for lib in ("gmp", "mpfr"):
        if not os.path.exists(lib):
            copy_gmp_mpfr(env, lib)
        else:
            _exist_echo(lib)

    return lib_downloaded


def download(env: environment) -> None:
    """下载不存在的源代码，然后执行回调函数，不会更新已有源代码

    Args:
        env (environment): 源代码下载环境
    """
    after_download(env, download_source(env))


def update_source(env: environment) -> list[str]:
    """更新所有源代码，要求所有包均已下载

    Args:
        env (environment): 源代码下载环境

    Returns:
        list[str]: 已下载的包列表
    """
    lib_downloaded: list[str] = []
    # 更新git托管的源代码
    for lib in git_lib_list:
        lib_dir = os.path.join(env.home, lib)
        assert os.path.exists(lib_dir), f"Cannot find lib: {lib}"
        result = subprocess.run(["git", "-C", lib_dir, "fetch", "--dry-run"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout.strip():
            common.run_command(f"git -C {lib_dir} pull")
            lib_downloaded.append(lib)
        else:
            _up_to_date_echo(lib)

    # 更新Python
    lib_dir = os.path.join(env.home, "python-embed")
    try:
        with open(os.path.join(lib_dir, "version")) as file:
            current_version = version.Version(file.readline())
            target_version = version.Version(PYTHON_VERSION)
            if current_version > target_version:
                print(f"[toolchains] Note: The python-embed package is newer than the default version {PYTHON_VERSION}.")
            else:
                need_download = current_version < target_version
    except Exception:
        need_download = True
    if need_download:
        common.remove(lib_dir)
        download_specific_extra_lib(env, "python-embed")
        lib_downloaded.append("python-embed")
    else:
        _up_to_date_echo("python-embed")

    return lib_downloaded


def update(env: environment) -> None:
    """更新所有源代码，然后调用回调函数，要求所有包均已下载

    Args:
        env (environment): 源代码下载环境
    """
    after_download(env, update_source(env))


def auto_download(env: environment) -> None:
    """首先下载缺失的包，然后更新已有的包，自动调用回调函数

    Args:
        env (environment): 源代码下载环境
    """
    download(env)
    update(env)


if __name__ == "__main__":
    default_glibc_version = subprocess.getoutput("getconf GNU_LIBC_VERSION").split(" ")[1]
    parser = argparse.ArgumentParser(
        description="Download or update needy libs for building clang and gcc.", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--glibc_version", type=str, help="The version of glibc of target platform.", default=default_glibc_version)
    parser.add_argument("--home", type=str, help="The home directory to find source trees.", default=os.environ["HOME"])
    parser.add_argument(
        "--clone_type",
        type=str,
        help="How to clone the git repository.",
        default=git_clone_type.partial._name_,
        choices=git_clone_type._member_names_,
    )
    parser.add_argument("--depth", type=int, help="The depth of shallow clone.", default=1)
    parser.add_argument("--ssh", type=bool, help="Whether to use ssh when cloning git repositories from github.", default=False)
    parser.add_argument("--extra_libs", nargs="*", action="extend", help="Extra non-git libs to install.", choices=optional_extra_lib_list)
    parser.add_argument("--update", action="store_true", help="Update installed libs. All libs should be installed before update.")
    parser.add_argument("--download", action="store_true", help="Download missing libs. This would not update existing libs.")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Download missing libs, then update installed libs. This may take more time because of twice check.",
    )
    parser.add_argument("--system", action="store_true", help="Print needy system libs and exit.")
    args = parser.parse_args()

    if args.system:
        print(f"Please install following system libs: {" ".join(system_lib_list)}")
        quit()
    assert args.depth > 0, f"Invalid shallow clone depth: {args.depth}"

    env = environment(args.glibc_version, args.home, git_clone_type[args.clone_type], args.depth, args.ssh, args.extra_libs or [])
    if args.auto:
        auto_download(env)
    elif args.update:
        update(env)
    elif args.download:
        download(env)
    else:
        ValueError("Please select a task in [auto, update, download].")
