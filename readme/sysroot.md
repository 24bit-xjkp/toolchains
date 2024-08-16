# LLVM和GCC的sysroot包

## 版本

- LLVM：20.0.0
- GCC: 15.0.0

## 说明

clang会尝试探测系统中已安装的gcc，并以此确定库目录，但更建议配合sysroot使用。gcc则默认会查找安装目录下的库文件，一般不需要设置sysroot。
因而在`prefix`下安装clang时还需要安装一份sysroot，建议安装到`prefix/sysroot`或`prefix/../sysroot`目录下。
本项目的xmake脚本会尝试按顺序探测上述两个路径下是否存在sysroot。若将sysroot安装到上述两个目录且使用`detect`选项，
则xmake可以自动完成sysroot的配置，而无需手动指定，这可以简化选项配置。自动探测依赖于`llvm-config`程序，因此需要保证
`llvm-config`所在路径位于`PATH`环境变量中，才能使用自动探测功能。自动探测的流程如下：

```shell
# 通过llvm-config获取prefix -> 探测sysroot目录 -> 将目录标准化得到sysroot目录
llvm-config --prefix -> prefix -> detect -> sysroot
```
