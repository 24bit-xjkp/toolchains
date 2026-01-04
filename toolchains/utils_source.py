import typing
from argparse import ArgumentParser
from pathlib import Path

from . import common


class compress_configure(common.basic_compress_configure):
    _item_list: list[Path]
    _output_dir: Path

    def __init__(
        self, item_list: list[str] | None = None, output_dir: str | None = None, base_path: Path = Path.cwd(), **kwargs: typing.Any
    ) -> None:
        super().__init__(base_path=base_path, **kwargs)
        self._item_list = [self.prefix_dir / item for item in (item_list or [])]
        self._output_dir = common.resolve_path(output_dir or self.prefix_dir, base_path)

    @classmethod
    def add_argument(cls, parser: ArgumentParser) -> None:
        super().add_argument(parser)

        default_config = compress_configure()
        parser.add_argument(
            "--output",
            "-o",
            dest="output_dir",
            type=str,
            help="The directory to store the operate result.",
            default=default_config._output_dir,
        )

    def check(self, need_dir: bool = True) -> None:
        """检查压缩环境配置是否合法"""

        super().check()
        for item_path in self._item_list:
            if need_dir:
                assert common.toolchains_dir(item_path), f'Path "{item_path}" is not a directory.'
            else:
                assert common.toolchains_package(item_path), f'Path "{item_path}" is not a tar file compressed by zstd.'

    def to_environment(self) -> common.compress_environment:
        """将配置信息转化为压缩环境

        Returns:
            common.compress_environment: 工具链压缩环境
        """

        return common.compress_environment(self.jobs, self.prefix_dir, self.compress_level, self.long_distance_match)


__all__ = ["compress_configure"]
