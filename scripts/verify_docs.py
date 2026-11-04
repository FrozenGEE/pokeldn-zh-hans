import re
import sys
from pathlib import Path

SRC = Path(r"C:\Users\User\Desktop\Pokemon\ESP32-S3\pokeldn\_internal\docs")
DST = Path(r"D:\deepseek-harness\日常\pokeldn_zh_work\pack\community-zh-hans\docs")

FENCE = "```"


def front_matter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def levels(text: str) -> list:
    return [len(m) for m in re.findall(r"^(#{1,6}) ", text, re.M)]


def links(text: str) -> list:
    return re.findall(r"\]\(([^)]+)\)", text)


def body_without_code(text: str) -> str:
    lines = text.splitlines()
    out, fenced, indented = [], False, False
    for line in lines:
        if line.strip().startswith(FENCE):
            fenced = not fenced
            out.append("")
            continue
        if fenced:
            continue
        if line.startswith("    ") or line.startswith("\t"):
            continue
        out.append(line)
    return "\n".join(out)


def residual_english(text: str) -> list:
    body = body_without_code(text)
    bad = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|--") or stripped.startswith("---"):
            continue
        # 去掉行内代码与链接目标后再判断
        clean = re.sub(r"`[^`]*`", " ", stripped)
        clean = re.sub(r"\]\([^)]*\)", "]", clean)
        clean = re.sub(r"https?://\S+", " ", clean)
        if re.search(r"[\u4e00-\u9fff]", clean):
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'’-]{2,}", clean)
        if len(words) >= 8:
            bad.append(stripped[:120])
    return bad


def main(names):
    rows = []
    problems = 0
    for name in names:
        src = SRC / name
        dst = DST / name
        if not dst.exists():
            rows.append((name, "MISSING", "", "", "", "", ""))
            problems += 1
            continue
        s = src.read_text(encoding="utf-8")
        d = dst.read_text(encoding="utf-8")
        lv_ok = levels(s) == levels(d)
        lk_ok = links(s) == links(d)
        fn_ok = s.count(FENCE) == d.count(FENCE)
        ratio = len(d.encode("utf-8")) / max(1, len(s.encode("utf-8")))
        fm_s, fm_d = front_matter(s), front_matter(d)
        fm_ok = all(k in fm_d for k in fm_s) and (
            fm_s.get("title") == fm_d.get("title") or bool(re.search(r"[\u4e00-\u9fff]", fm_d.get("title", "")))
        )
        en = residual_english(d)
        ok = lv_ok and lk_ok and fn_ok and fm_ok and 0.55 <= ratio <= 1.35
        if not ok:
            problems += 1
        rows.append(
            (
                name,
                "OK" if ok else "FAIL",
                f"{len(s.encode('utf-8'))}->{len(d.encode('utf-8'))}",
                f"{ratio:.2f}",
                f"h{len(levels(s))}/{len(levels(d))}{'' if lv_ok else '!'}",
                f"l{len(links(s))}/{len(links(d))}{'' if lk_ok else '!'}",
                f"f{s.count(FENCE)}/{d.count(FENCE)}{'' if fn_ok else '!'}",
                f"en{len(en)}",
            )
        )
        if en:
            for line in en[:3]:
                print(f"  [{name}] 未译行: {line}")
    print(f"{'file':26s} {'status':6s} {'bytes':16s} {'ratio':5s} {'heads':10s} {'links':10s} {'fence':7s} en")
    for r in rows:
        print(f"{r[0]:26s} {r[1]:6s} {r[2]:16s} {r[3]:5s} {r[4]:10s} {r[5]:10s} {r[6]:7s} {r[7]}")
    print(f"\ntotal {len(rows)} files, problems {problems}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) > 1:
        names = sys.argv[1:]
    else:
        names = sorted(p.name for p in SRC.glob("*.md"))
    sys.exit(1 if main(names) else 0)
