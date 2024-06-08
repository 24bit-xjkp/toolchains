# GCC和LLVM工具链

该仓库提供开发版的GCC和LLVM工具链。它们具有如下特征：

- 带有Python支持的GDB
- 带有Python支持的libstdc++
- 支持pretty-printer的.gdbinit
- 使用相对路径，可重新部署
- 已配置rpath并带有必要的动态库
- 支持调试符号

支持如下工具链：
| 工具链 | Host               | Target                                           |
| :----- | :----------------- | :----------------------------------------------- |
| gcc    | x86_64-linux-gnu   | x86_64-linux-gnu                                 |
| gcc    | x86_64-linux-gnu   | i686-linux-gnu                                   |
| gcc    | x86_64-linux-gnu   | x86_64-w64-mingw32                               |
| gcc    | x86_64-linux-gnu   | i686-w64-mingw32                                 |
| gcc    | x86_64-linux-gnu   | arm-none-eabi                                    |
| gcc    | x86_64-linux-gnu   | x86_64-elf                                       |
| gcc    | x86_64-linux-gnu   | loongarch64-linux-gnu                            |
| gcc    | x86_64-linux-gnu   | riscv64-linux-gnu                                |
| gcc    | x86_64-linux-gnu   | aarch64-linux-gnu                                |
| gcc    | x86_64-w64-mingw32 | x86_64-w64-mingw32                               |
| gcc    | x86_64-w64-mingw32 | i686-w64-mingw32                                 |
| gcc    | x86_64-w64-mingw32 | x86_64-linux-gnu                                 |
| gcc    | x86_64-w64-mingw32 | i686-linux-gnu                                   |
| gcc    | x86_64-w64-mingw32 | arm-none-eabi                                    |
| gcc    | x86_64-w64-mingw32 | x86_64-elf                                       |
| gcc    | x86_64-w64-mingw32 | loongarch64-linux-gnu                            |
| gcc    | x86_64-w64-mingw32 | riscv64-linux-gnu                                |
| gcc    | x86_64-w64-mingw32 | aarch64-linux-gnu                                |
| llvm   | x86_64-linux-gnu   | X86, ARM, AArch64, LoongArch, RISCV, WebAssembly |
| llvm   | x86_64-w64-mingw32 | X86, ARM, AArch64, LoongArch, RISCV, WebAssembly |
