"""校验各分片译文并合并为最终 strings.toml。

用法：python build.py
输出：D:\\deepseek-harness\\日常\\pokeldn_zh_work\\out\\strings.toml
"""
import string
import sys
import tomllib
from pathlib import Path

WORK = Path(r"D:\deepseek-harness\日常\pokeldn_zh_work")
SRC = Path(
    r"C:\Users\User\Desktop\Pokemon\ESP32-S3\pokeldn\_internal\pokeldn\app\data\strings.en.toml"
)


def load(path):
    with path.open("rb") as fh:
        return tomllib.load(fh)


# 英文里紧跟名词的“复数后缀”占位符（值为 "s"/"es"）。中文不靠后缀表复数，翻译时已用「个」，
# 这里把该占位符从译文中去掉：调用方无论传 "" 还是硬编码 "s"，结果都不会出现「个插件s」。
SUFFIX_DROP = {
    "bank.file_unreadable_0fd8f4": "value1",
    "gts.open_until_offer_answered_3c9d1f": "value2",
    "plugins.source_added": "value2",
    "plugins.source_count": "value1",
    "plugins.tool_d0d814": "value2",
}


def strip_suffix(key: str, text: str) -> str:
    name = SUFFIX_DROP.get(key)
    return text.replace("{" + name + "}", "") if name else text


def fields(text):
    """(name, spec) pairs from a format string, ignoring literal braces."""
    try:
        return [(f, s) for _, f, s, _ in string.Formatter().parse(text) if f is not None]
    except ValueError as error:
        return [("__PARSE_ERROR__", str(error))]


def main():
    source = load(SRC)
    parts = {}
    for path in sorted(WORK.glob("part_*.toml")):
        try:
            parts[path.name] = load(path)
        except Exception as error:  # noqa: BLE001
            print(f"[FAIL] {path.name}: TOML 解析失败 -> {error}")
            parts[path.name] = {}

    merged = {}
    dupes = []
    for name, table in parts.items():
        for key, value in table.items():
            if key in merged:
                dupes.append((key, name))
            merged[key] = value
            if not isinstance(value, str):
                print(f"[FAIL] {name}: {key} 的值不是字符串")

    missing = [k for k in source if k not in merged]
    extra = [k for k in merged if k not in source]
    print(f"源条目 {len(source)}，译文条目 {len(merged)}")
    if dupes:
        print(f"[WARN] 重复键 {len(dupes)} 个：{dupes[:10]}")
    if missing:
        print(f"[FAIL] 缺少 {len(missing)} 个键：{missing[:20]}")
    if extra:
        print(f"[FAIL] 多出 {len(extra)} 个键：{extra[:20]}")

    bad_fields = []
    untranslated = []
    for key, english in source.items():
        chinese = merged.get(key)
        if chinese is None:
            continue
        ef, cf = fields(strip_suffix(key, english)), fields(strip_suffix(key, chinese))
        if sorted(ef) != sorted(cf):
            bad_fields.append((key, english, chinese, ef, cf))
        elif chinese.strip() == english.strip() and any(ch.isalpha() for ch in english):
            untranslated.append((key, english))

    if bad_fields:
        print(f"[FAIL] 占位符不一致 {len(bad_fields)} 个：")
        for key, english, chinese, ef, cf in bad_fields[:25]:
            print(f"  {key}\n    EN: {english}\n    ZH: {chinese}\n    {ef} != {cf}")
    if untranslated:
        print(f"[WARN] 译文与英文完全相同 {len(untranslated)} 个：")
        for key, english in untranslated[:25]:
            print(f"  {key} = {english}")

    if not missing and not extra and not bad_fields:
        out = WORK / "out"
        out.mkdir(exist_ok=True)
        lines = ["# 简体中文语言包。生成自 strings.en.toml，key 与英文模板一致。"]
        for key, english in source.items():
            value = strip_suffix(key, merged[key])
            lines.append(f'"{key}" = {escape(value)}')
        target = out / "strings.toml"
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[OK] 已写出 {target}，共 {len(source)} 条")
        return 0
    print("[FAIL] 校验未通过，未生成最终文件")
    return 1


def escape(value: str) -> str:
    text = (value.replace("\\", "\\\\").replace('"', '\\"')
                 .replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t"))
    return '"' + text + '"'


if __name__ == "__main__":
    sys.exit(main())
