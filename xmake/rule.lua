includes("option.lua")
---@type string?
local debug_strip = get_config("debug_strip")
if debug_strip == "none" then -- 不剥离符号
    debug_strip = nil
end
---@type string?
local debug_info = get_config("debug_info") == "minsizerel" and "debug" or nil
---@type boolean
local enable_lto = get_config("enable_lto")

---注册debug规则的on_load函数
---@param target table @目标实例
---@return void
local function register_debug_rule_on_load(target)
    target:set("symbols", "debug")
    target:set("optimize", "none")
    target:add("defines", "DEBUG", "_DEBUG")
    target:set("strip", debug_strip)
end

rule("debug", function()
    on_load(register_debug_rule_on_load)
end)

---注册release规则的on_load函数
---@param target table @目标实例
---@return void
local function register_release_rule_on_load(target)
    target:add("defines", "NDEBUG")
    target:set("optimize", "fastest")
    target:set("strip", "all")
    target:set("policy", "build.optimization.lto", enable_lto)
end

rule("release", function()
    on_load(register_release_rule_on_load)
end)

---注册minsizerel规则的on_load函数
---@param target table @目标实例
---@return void
local function register_minsizerel_rule_on_load(target)
    target:add("defines", "NDEBUG")
    target:set("optimize", "smallest")
    target:set("strip", "all")
    target:set("policy", "build.optimization.lto", enable_lto)
    target:set("symbols", debug_info)
end

rule("minsizerel", function()
    on_load(register_minsizerel_rule_on_load)
end)

---注册releasedbg规则的on_load函数
---@param target table @目标实例
---@return void
local function register_releasedbg_rule_on_load(target)
    target:set("optimize", "fastest")
    target:set("symbols", "debug")
    target:set("policy", "build.optimization.lto", enable_lto)
    target:set("strip", debug_strip)
end

rule("releasedbg", function()
    on_load(register_releasedbg_rule_on_load)
end)

---注册coverage规则的on_load函数
---@param target table @目标实例
---@return void
local function register_coverage_rule_on_load(target)
    local gcc_options = { "--coverage" }
    local clang_options = { "-fprofile-instr-generate", "-fcoverage-mapping", "-fcoverage-mcdc" }
    local is_gcc = import("utility.common").is_gcc()
    local options = is_gcc and gcc_options or clang_options
    target:add("cflags", table.unpack(options))
    target:add("cxxflags", table.unpack(options))
    target:add("ldflags", table.unpack(options))
    target:add("shflags", table.unpack(options))
    target:set("policy", "build.ccache", false)
    if not is_gcc then
        local profile_name = os.getenv("COVERAGE_PROFILE_NAME")
        local llvm_profile_file
        if profile_name then
            llvm_profile_file = string.format("%s_%s.profraw", target:name(), profile_name)
        else
            llvm_profile_file = target:name() .. ".profraw"
        end
        target:add("runenvs", "LLVM_PROFILE_FILE", llvm_profile_file)
    end
end

rule("coverage", function()
    add_deps("debug")
    on_load(register_coverage_rule_on_load)
end)

---注册fuzzer规则的on_load函数
---@param target table @目标实例
---@return void
local function register_fuzzer_rule_on_load(target)
    assert(import("utility.common").is_clang(), "Libfuzzer only support in clang toolchain.")
    target:set("policy", "build.sanitizer.address", true)
    target:set("policy", "build.sanitizer.undefined", true)
    target:set("policy", "build.optimization.lto", enable_lto)
    target:add("cflags", "-fsanitize=fuzzer")
    target:add("cxxflags", "-fsanitize=fuzzer")
    target:add("ldflags", "-fsanitize=fuzzer")
    target:add("shflags", "-fsanitize=fuzzer")
    target:set("symbols", "debug")
    target:set("optimize", get_config("fuzzer_optimize_level"))
    target:set("strip", debug_strip)
    if get_config("fuzzer_with_coverage") then
        register_coverage_rule_on_load(target)
    end
end

rule("fuzzer", function()
    on_load(register_fuzzer_rule_on_load)
end)

---受支持的规则表
---@type string[]
support_rules_table = { "debug", "release", "minsizerel", "releasedbg", "coverage", "fuzzer" }

---用于注册规则中on_load函数的函数表
---@type table<string, fun(target: table) : void>
register_rule_on_load_table = {
    debug = register_debug_rule_on_load,
    release = register_release_rule_on_load,
    minsizerel = register_minsizerel_rule_on_load,
    releasedbg = register_releasedbg_rule_on_load,
    coverage = register_coverage_rule_on_load,
    fuzzer = register_fuzzer_rule_on_load,
}
