---@alias modifier_t fun(toolchain: unknown, opt: table<string, unknown>): void
---@alias modifier_table_t table<string, modifier_t>
---@class sysroot_t
---@field public ldflags string
---@field public cxflags string
---@field public shflags string
---@class opt_t
---@field public march string
---@field public sysroot sysroot_t

---占位符，无效果
---@return void
function noop_modifier(_, _) return end

---为loongnix定制部分flag
---@return void
function loongnix_modifier(toolchain, _)
    -- loongnix的glibc版本较老，使用的ld路径与新编译器默认路径不同
    toolchain:add("ldflags", "-Wl,-dynamic-linker=/lib64/ld.so.1")
    -- loongnix本机gdb仅支持dwarf4格式调试信息
    toolchain:add("cxflags", "-gdwarf-4")
end

---为独立工具链定制部分flag
---@return void
function freestanding_modifier(toolchain, _)
    -- freestanding需要禁用标准库
    toolchain:add("cxflags", "-ffreestanding")
    toolchain:add("ldflags", "-nodefaultlibs", "-lstdc++", "-lgcc")
end

local note_msg = "${color.warning}NOTE:${default} "

---根据target重设sysroot
---@param target string
---@param opt opt_t
---@return void
function _reset_sysroot(target, opt)
    import("common")
    local cache_info = common.get_cache()
    if cache_info["sysroot_set_by_user"] then
        return
    end
    local sysroot_option = opt.sysroot
    local sysroot = sysroot_option.ldflags:sub(11)
    local target_sysroot = path.join(sysroot, target)
    if path.filename(sysroot) ~= target and os.isdir(target_sysroot) then
        cprint(note_msg .. [[Reset "--sysroot" option to "%s".]], target_sysroot)
        sysroot = "--sysroot=" .. target_sysroot
        opt.sysroot.cxflags = sysroot
        opt.sysroot.ldflags = sysroot
        opt.sysroot.shflags = sysroot
    end
end

---重设march为指定值
---@param default_march string
---@param support_arch_list string[]
---@param opt opt_t
---@return void
function _reset_march(default_march, support_arch_list, opt)
    local march_option = "-march=" .. default_march
    local _, arch = opt.march:match("([^=]+)=([^=]+)")
    if not table.contains(support_arch_list, arch) then
        cprint(note_msg .. [[Reset "-march" option to %s.]], default_march)
        opt.march = march_option
    end
end

local arm32_arch_list = { "armv4", "armv4t", "armv5t", "armv5te", "armv5tej", "armv6", "armv6j", "armv6k", "armv6z",
    "armv6kz", "armv6zk", "armv6t2", "armv6-m", "armv6s-m", "armv7", "armv7-a", "armv7ve", "armv7-r", "armv7-m",
    "armv7e-m" }

---为armv7m定制部分flag
---@param opt opt_t
---@return void
function armv7m_modifier(_, opt)
    _reset_march("armv7-m", arm32_arch_list, opt)
    _reset_sysroot("armv7m-none-eabi", opt)
end

---为armv7m-fpv4定制部分flag
---@param opt opt_t
---@return void
function armv7m_fpv4_modifier(toolchain, opt)
    _reset_march("armv7-m", arm32_arch_list, opt)
    _reset_sysroot("armv7m-fpv4-none-eabi", opt)
    toolchain:add("cxflags", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard")
    toolchain:add("asflags", "-mfpu=fpv4-sp-d16")
end

---只有clang支持的目标
---@type modifier_table_t
clang_only_target_list = {
    ["x86_64-windows-msvc"] = noop_modifier,
    ["aarch64-windows-msvc"] = noop_modifier,
    ["i686-windows-msvc"] = noop_modifier,
    ["x86_64-windows-gnu"] = noop_modifier,
    ["armv7m-none-eabi"] = armv7m_modifier,
    ["armv7m-fpv4-none-eabi"] = armv7m_fpv4_modifier,
    -- TODO: add another android target
    ["aarch64-linux-android30"] = noop_modifier,
    ["aarch64-apple-darwin24"] = noop_modifier,
    -- wasm
    ["wasm32-wasip1"] = noop_modifier,
    ["wasm32-wasip1-threads"] = noop_modifier,
    ["wasm32-wasip2"] = noop_modifier,
    ["wasm32-wasip2-threads"] = noop_modifier,
    ["wasm64-wasip1"] = noop_modifier,
    ["wasm64-wasip1-threads"] = noop_modifier,
}
---只有gcc支持的目标
---@type modifier_table_t
gcc_only_target_list = {
    ["arm-none-eabi"] = noop_modifier,
    ---编译gcc时已经指定过默认选项，此处不再指定
    ["arm-fpv4-none-eabi"] = noop_modifier,
    ["arm-nonewlib-none-eabi"] = freestanding_modifier,
    ["riscv-none-elf"] = noop_modifier,
}
---gcc和clang均支持的目标
---@type modifier_table_t
general_target_list = {
    ["x86_64-linux-gnu"] = noop_modifier,
    ["i686-linux-gnu"] = noop_modifier,
    ["x86_64-w64-mingw32"] = noop_modifier,
    ["i686-w64-mingw32"] = noop_modifier,
    ["loongarch64-linux-gnu"] = noop_modifier,
    ["loongarch64-loongnix-linux-gnu"] = loongnix_modifier,
    ["riscv64-linux-gnu"] = noop_modifier,
    ["aarch64-linux-gnu"] = noop_modifier,
    ["arm-linux-gnueabi"] = noop_modifier,
    ["arm-linux-gnueabihf"] = noop_modifier,
    ["x86_64-elf"] = freestanding_modifier,
    ["native"] = noop_modifier,
    ["target"] = noop_modifier
}

---获取clang支持的目标列表
---@return modifier_table_t
function get_clang_target_list()
    return table.join(general_target_list, clang_only_target_list)
end

---获取gcc支持的目标列表
---@return modifier_table_t
function get_gcc_target_list()
    return table.join(general_target_list, gcc_only_target_list)
end

---获取所有受支持的目标列表
---@return modifier_table_t
function get_target_list()
    return table.join(general_target_list, clang_only_target_list, gcc_only_target_list)
end
