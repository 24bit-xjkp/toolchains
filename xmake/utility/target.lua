---@alias modifier_t fun(toolchain:unknown, opt:table<string, unknown>):nil
---@alias modifier_table_t table<string, modifier_t>

---占位符，无效果
---@return nil
function noop_modifier(_, _) return end

---为loongnix定制部分flag
---@return nil
function loongnix_modifier(toolchain, _)
    -- loongnix的glibc版本较老，使用的ld路径与新编译器默认路径不同
    toolchain:add("ldflags", "-Wl,-dynamic-linker=/lib64/ld.so.1")
    -- loongnix本机gdb仅支持dwarf4格式调试信息
    toolchain:add("cxflags", "-gdwarf-4")
end

---为独立工具链定制部分flag
---@return nil
function freestanding_modifier(toolchain, _)
    -- freestanding需要禁用标准库
    toolchain:add("cxflags", "-ffreestanding")
    toolchain:add("ldflags", "-nodefaultlibs", "-lstdc++", "-lgcc")
end

---为armv7m定制部分flag
---@param opt table<string, unknown>
---@return nil
function armv7m_modifier(_, opt)
    if opt.march ~= "-march=armv7-m" then
        print([[Note: Reset "-march" option to armv7-m.]])
        opt.march = "-march=armv7-m"
    end
    local sysroot_option = opt.sysroot
    local sysroot = sysroot_option.ldflags:sub(11)
    local libcxx_option = #sysroot_option.cxflags == 2 and sysroot_option.cxflags[2] or nil
    ---@type string
    local armv7m_sysroot = path.join(sysroot, "armv7m-none-eabi")
    if path.filename(sysroot) ~= "armv7m-none-eabi" and os.isdir(armv7m_sysroot) then
        print([[Note: Reset "--sysroot" option to ]] .. armv7m_sysroot)
        sysroot = "--sysroot=" .. armv7m_sysroot
        opt.sysroot.cxflags = { sysroot, libcxx_option }
        opt.sysroot.ldflags = sysroot
        opt.sysroot.shflags = sysroot
    end
end

---只有clang支持的目标
---@type modifier_table_t
clang_only_target_list = { ["x86_64-windows-msvc"] = noop_modifier, ["armv7m-none-eabi"] = armv7m_modifier }
---只有gcc支持的目标
---@type modifier_table_t
gcc_only_target_list = {
    ["arm-none-eabi"] = noop_modifier,
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
