includes("option.lua")
local debug_strip = get_config("debug_strip")
if debug_strip == "no" then -- 不剥离符号
    debug_strip = nil
end

rule("debug")
    on_load(function (target)
        target:set("symbols", "debug")
        target:set("optimize", "none")
        target:add("defines", "DEBUG", "_DEBUG")
        target:set("strip", debug_strip)
    end)
rule_end()
rule("release")
    on_load(function (target)
        target:add("defines", "NDEBUG")
        target:set("optimize", "fastest")
        target:set("strip", "all")
        target:set("policy", "build.optimization.lto", true)
    end)
rule_end()
rule("minsizerel")
    on_load(function (target)
        target:add("defines", "NDEBUG")
        target:set("optimize", "smallest")
        target:set("strip", "all")
        target:set("policy", "build.optimization.lto", true)
    end)
rule_end()
rule("releasedbg")
    on_load(function (target)
        target:set("optimize", "fastest")
        target:set("symbols", "debug")
        target:set("policy", "build.optimization.lto", true)
        target:set("strip", debug_strip)
    end)
rule_end()
