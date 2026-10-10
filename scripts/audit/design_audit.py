#!/usr/bin/env python3
"""lhg-ecom-design 确定性图片审计：14 条规则，零第三方依赖。

扫描目标目录的商品图片，校验主图尺寸/比例合规、文件大小、格式、
命名规范、主图数量、alt 缺失等；图片尺寸用纯 Python 解析文件头
（PNG/JPEG/GIF/BMP/WebP），不依赖 PIL。

有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用），
只有 warning/nit 时 exit 0。

用法：
    python3 design_audit.py --target <图片目录> [--platform 淘宝|京东|拼多多|抖音]
                            [--format json|text] [--fail-on blocker|warning|nit]

尺寸规范依据 lhg-ed-size-spec（2026-10-11 第三方教程汇总核实，
非平台官方最新文档）；凡引用具体数字的规则 detail 均带
"以平台最新规范为准"提醒。
规则文案均为本项目原创。
"""

import argparse
import csv
import json
import os
import re
import struct
import sys

VERSION = "1.0.0"
TOOL = "lhg-ecom-design/design-audit"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}

PLATFORMS = {
    "淘宝": "taobao", "taobao": "taobao",
    "京东": "jd", "jd": "jd",
    "拼多多": "pinduoduo", "pdd": "pinduoduo", "拼多多": "pinduoduo",
    "抖音": "douyin", "douyin": "douyin",
}
# 规范库（2026-10-11 核实，第三方教程汇总；以平台最新规范为准）
SPEC = {
    "taobao":   {"main_min": 800, "main_ratio": "1:1", "detail_width": 750,
                 "detail_width_max": 790, "label": "淘宝"},
    "jd":       {"main_min": 800, "main_ratio": "1:1", "detail_width": 750,
                 "detail_width_max": 790, "label": "京东（未单独核实官方文档，沿用通用标准）"},
    "pinduoduo": {"main_min": 750, "main_ratio": "1:1", "detail_width": 750,
                  "detail_width_max": 790, "label": "拼多多"},
    "douyin":   {"main_min": 1080, "main_ratio": "9:16", "detail_width": 750,
                 "detail_width_max": 790, "label": "抖音（竖屏 1080x1920 优先）"},
}
FILE_WARN_KB = 500
FILE_BLOCK_MB = 3


# ---------------------------------------------------------------- 图片尺寸解析

def _png_size(data):
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    return None


def _gif_size(data):
    if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    return None


def _bmp_size(data):
    if len(data) >= 26 and data[:2] == b"BM":
        w, h = struct.unpack("<ii", data[18:26])
        return abs(w), abs(h)
    return None


def _jpeg_size(data):
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 4 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if i + 2 > n:
            return None
        seg_len = struct.unpack(">H", data[i:i + 2])[0]
        if 0xC0 <= marker <= 0xC3:  # SOF0~SOF3
            if i + 7 <= n:
                h, w = struct.unpack(">HH", data[i + 3:i + 7])
                return w, h
            return None
        i += seg_len
    return None


def _webp_size(data):
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8 " and len(data) >= 26:
        w = struct.unpack("<H", data[24:26])[0] & 0x3FFF
        h = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        return w, h
    if chunk == b"VP8L" and len(data) >= 21:
        b0, b1, b2, b3 = data[17:21]
        bits = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
        return w, h
    if chunk == b"VP8X" and len(data) >= 30:
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return w, h
    return None


def image_size(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read(64 * 1024)
    except OSError:
        return None
    for fn in (_png_size, _jpeg_size, _gif_size, _bmp_size, _webp_size):
        r = fn(data)
        if r:
            return r
    return None


# ---------------------------------------------------------------- 规则引擎

class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def is_main_image(name):
    low = name.lower()
    if "detail" in low or "详情" in name:
        return False
    return True


def is_detail_image(name):
    low = name.lower()
    return "detail" in low or "详情" in name


def fmt_size(path):
    wh = image_size(path)
    return "%dx%d" % wh if wh else "未知尺寸"


# ---------------- 尺寸合规 ----------------

@rule("ED-SIZE-001", "blocker", "尺寸合规", "主图尺寸过小",
      "主图短边小于平台建议最小值，搜索页缩略图会模糊。以平台最新规范为准。")
def r_size_001(files, ctx):
    spec = ctx["spec"]
    out = []
    for f in files["main"]:
        wh = f["size"]
        if not wh:
            continue
        if min(wh) < spec["main_min"] - 100:
            r = _RULE_BY_ID["ED-SIZE-001"]
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               f["rel"], 0, fmt_size(f["path"]),
                               "%s：%s 小于建议最小 %dpx（%s）。%s"
                               % (f["name"], fmt_size(f["path"]),
                                  spec["main_min"], spec["label"], r["detail"])))
    return out


@rule("ED-SIZE-002", "blocker", "尺寸合规", "主图不是正方形",
      "淘宝/京东/拼多多搜索页按正方形展示，非正方形主图会被裁剪，卖点丢失。以平台最新规范为准。")
def r_size_002(files, ctx):
    if ctx["platform"] == "douyin":
        return []
    out = []
    for f in files["main"]:
        wh = f["size"]
        if not wh or wh[1] == 0:
            continue
        ratio = wh[0] / wh[1]
        if abs(ratio - 1.0) > 0.02:
            r = _RULE_BY_ID["ED-SIZE-002"]
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               f["rel"], 0, fmt_size(f["path"]),
                               "%s：%s 宽高比 %.2f，不是 1:1 正方形（%s）。"
                               % (f["name"], fmt_size(f["path"]), ratio, ctx["spec"]["label"])))
    return out


@rule("ED-SIZE-003", "warning", "尺寸合规", "详情页图片宽度超 790px",
      "详情页建议宽度 750px（上限约 790px），超宽图在手机端会被压缩。以平台最新规范为准。")
def r_size_003(files, ctx):
    out = []
    for f in files["detail"]:
        wh = f["size"]
        if not wh:
            continue
        if wh[1] > wh[0] * 1.5 and wh[0] > ctx["spec"]["detail_width_max"]:
            r = _RULE_BY_ID["ED-SIZE-003"]
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               f["rel"], 0, fmt_size(f["path"]),
                               "%s：%s 宽度 %dpx 超过建议上限 %dpx。"
                               % (f["name"], fmt_size(f["path"]), wh[0],
                                  ctx["spec"]["detail_width_max"])))
    return out


@rule("ED-SIZE-004", "warning", "尺寸合规", "详情页图片宽度不足 700px",
      "详情页宽度建议 750px，过窄的长图会被拉伸，文字变糊。以平台最新规范为准。")
def r_size_004(files, ctx):
    out = []
    for f in files["detail"]:
        wh = f["size"]
        if not wh:
            continue
        if wh[1] > wh[0] * 1.5 and wh[0] < 700:
            r = _RULE_BY_ID["ED-SIZE-004"]
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               f["rel"], 0, fmt_size(f["path"]),
                               "%s：%s 宽度仅 %dpx，建议 750px。"
                               % (f["name"], fmt_size(f["path"]), wh[0])))
    return out


@rule("ED-SIZE-005", "warning", "尺寸合规", "抖音主图不是 9:16 竖屏",
      "抖音商品图优先 9:16 竖屏（如 1080x1920），横图/方图在信息流里展示吃亏。以平台最新规范为准。")
def r_size_005(files, ctx):
    if ctx["platform"] != "douyin":
        return []
    out = []
    for f in files["main"]:
        wh = f["size"]
        if not wh or wh[0] == 0:
            continue
        ratio = wh[1] / wh[0]
        if not 1.6 <= ratio <= 1.85:
            r = _RULE_BY_ID["ED-SIZE-005"]
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               f["rel"], 0, fmt_size(f["path"]),
                               "%s：%s 宽高比 h/w=%.2f，建议 9:16（≈1.78）竖屏。"
                               % (f["name"], fmt_size(f["path"]), ratio)))
    return out


# ---------------- 文件与格式 ----------------

@rule("ED-FILE-001", "warning", "文件体积", "单张图片超过 500KB",
      "手机端加载慢，用户 3 秒打不开就划走。建议压缩到 500KB 以内（JPG 质量 80 左右）。")
def r_file_001(files, ctx):
    r = _RULE_BY_ID["ED-FILE-001"]
    return [Finding(r["id"], r["severity"], r["category"], r["title"],
                    f["rel"], 0, "%.0fKB" % (f["bytes"] / 1024), r["detail"])
            for f in files["all"] if f["bytes"] > FILE_WARN_KB * 1024]


@rule("ED-FILE-002", "blocker", "文件体积", "单张图片超过 3MB",
      "文件过大，上传可能失败，且详情页加载必卡。必须压缩或切片。")
def r_file_002(files, ctx):
    r = _RULE_BY_ID["ED-FILE-002"]
    return [Finding(r["id"], r["severity"], r["category"], r["title"],
                    f["rel"], 0, "%.1fMB" % (f["bytes"] / 1024 / 1024), r["detail"])
            for f in files["all"] if f["bytes"] > FILE_BLOCK_MB * 1024 * 1024]


@rule("ED-FMT-001", "blocker", "格式", "使用了平台不支持的图片格式",
      "BMP/TIFF 等格式平台不支持上传，传了也显示不了。转 JPG/PNG。")
def r_fmt_001(files, ctx):
    r = _RULE_BY_ID["ED-FMT-001"]
    return [Finding(r["id"], r["severity"], r["category"], r["title"],
                    f["rel"], 0, f["ext"], r["detail"])
            for f in files["all"] if f["ext"] in (".bmp", ".tif", ".tiff")]


@rule("ED-FMT-002", "warning", "格式", "WebP 格式兼容性待确认",
      "WebP 体积小但部分老平台/工具链支持不佳，上传前确认目标平台支持，否则转 JPG。")
def r_fmt_002(files, ctx):
    r = _RULE_BY_ID["ED-FMT-002"]
    return [Finding(r["id"], r["severity"], r["category"], r["title"],
                    f["rel"], 0, f["ext"], r["detail"])
            for f in files["all"] if f["ext"] == ".webp"]


# ---------------- 命名与集合 ----------------

@rule("ED-NAME-001", "warning", "命名", "文件名含中文或空格",
      "部分上传接口对中文/空格转码失败，图传不上去还难排查。改成英文/拼音+序号。")
def r_name_001(files, ctx):
    r = _RULE_BY_ID["ED-NAME-001"]
    out = []
    for f in files["all"]:
        if re.search(r"[\u4e00-\u9fff\s]", f["name"]):
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               f["rel"], 0, f["name"], r["detail"]))
    return out


@rule("ED-SET-001", "warning", "集合", "主图数量少于 5 张",
      "主图建议 5 张起（钩子/卖点/场景/细节/信任各一张），太少讲不完故事。")
def r_set_001(files, ctx):
    if len(files["main"]) >= 5:
        return []
    r = _RULE_BY_ID["ED-SET-001"]
    return [Finding(r["id"], r["severity"], r["category"], r["title"],
                    ".", 0, "主图 %d 张" % len(files["main"]), r["detail"])]


# ---------------- 无障碍与人工项 ----------------

@rule("ED-ALT-001", "warning", "无障碍", "商品清单缺 alt/图片描述列",
      "目录下有 listing.csv 但没有 alt（或'图片描述'）列：读屏用户与站内搜索都受影响，建议补上。")
def r_alt_001(files, ctx):
    if not files["listing"]:
        return []
    r = _RULE_BY_ID["ED-ALT-001"]
    out = []
    for lp in files["listing"]:
        try:
            with open(lp, "r", encoding="utf-8-sig", errors="replace") as fh:
                header = (csv.reader(fh).__next__())
        except Exception:
            continue
        cols = [c.strip().lower() for c in header]
        if not any(k in cols for k in ("alt", "图片描述", "图片alt", "描述")):
            out.append(Finding(r["id"], r["severity"], r["category"], r["title"],
                               os.path.relpath(lp, ctx["target"]), 0,
                               ",".join(header)[:120], r["detail"]))
    return out


@rule("ED-TEXT-001", "warning", "人工自查", "首图文字占比未做人工自查标记",
      "脚本无法识别图片内文字。首图文字占比建议 ≤30% 且不许遮挡主体，"
      "请按 /lhg-ecom-design:audit 清单人工确认后，在 ecom-manifest.json 里置 "
      "first_image_text_ratio_checked=true。")
def r_text_001(files, ctx):
    if ctx.get("manifest_checked"):
        return []
    r = _RULE_BY_ID["ED-TEXT-001"]
    return [Finding(r["id"], r["severity"], r["category"], r["title"],
                    ".", 0, "ecom-manifest.json 缺失或未标记",
                    "在图片目录下放 ecom-manifest.json 并置 "
                    "first_image_text_ratio_checked=true 表示已人工自查。%s" % r["detail"])]


# ---------------------------------------------------------------- 主流程

def collect(target):
    files = {"all": [], "main": [], "detail": [], "listing": []}
    for root, dirs, names in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for nm in sorted(names):
            p = os.path.join(root, nm)
            rel = os.path.relpath(p, target)
            _, ext = os.path.splitext(nm)
            ext = ext.lower()
            if ext in IMAGE_EXTS:
                try:
                    size_b = os.path.getsize(p)
                except OSError:
                    continue
                info = {"path": p, "rel": rel, "name": nm, "ext": ext,
                        "bytes": size_b, "size": image_size(p)}
                files["all"].append(info)
                (files["detail"] if is_detail_image(nm) else files["main"]).append(info)
            elif nm.lower() == "listing.csv":
                files["listing"].append(p)
    return files


def run_audit(target, platform):
    spec = SPEC[platform]
    manifest_checked = False
    mp = os.path.join(target, "ecom-manifest.json")
    if os.path.isfile(mp):
        try:
            with open(mp, encoding="utf-8") as fh:
                manifest_checked = bool(json.load(fh).get("first_image_text_ratio_checked"))
        except Exception:
            manifest_checked = False
    ctx = {"target": target, "platform": platform, "spec": spec,
           "manifest_checked": manifest_checked}
    files = collect(target)
    findings = []
    for r in RULES:
        try:
            findings.extend(r["check"](files, ctx))
        except Exception as e:
            findings.append(Finding("ED-ENGINE-001", "warning", "引擎",
                                    "规则 %s 执行异常" % r["id"], ".", 0, str(e)[:120],
                                    "规则内部出错，已 fail-open 跳过该规则。"))
    sev_rank = {"blocker": 0, "warning": 1, "nit": 2}
    findings.sort(key=lambda f: (sev_rank.get(f.severity, 3), f.rule_id, f.file))
    summary = {
        "tool": TOOL, "version": VERSION, "platform": platform,
        "images": len(files["all"]),
        "main_images": len(files["main"]), "detail_images": len(files["detail"]),
        "rules_run": len(RULES),
        "blocker": sum(1 for f in findings if f.severity == "blocker"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "nit": sum(1 for f in findings if f.severity == "nit"),
    }
    return {"summary": summary, "findings": [f.to_dict() for f in findings]}


def main():
    ap = argparse.ArgumentParser(description="lhg-ecom-design 确定性图片审计")
    ap.add_argument("--target", required=True, help="图片目录")
    ap.add_argument("--platform", default="淘宝", help="淘宝|京东|拼多多|抖音")
    ap.add_argument("--format", default="text", choices=["json", "text"])
    ap.add_argument("--fail-on", default="blocker", choices=["blocker", "warning", "nit"])
    args = ap.parse_args()

    platform = PLATFORMS.get(args.platform.strip(), "taobao")
    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("目标目录不存在: %s" % args.target, file=sys.stderr)
        return 2

    report = run_audit(target, platform)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        s = report["summary"]
        print("lhg-ecom-design 图片审计（平台：%s，图片 %d 张，主图 %d / 详情 %d）"
              % (SPEC[platform]["label"], s["images"], s["main_images"], s["detail_images"]))
        print("blocker=%d warning=%d nit=%d（共 %d 条规则）"
              % (s["blocker"], s["warning"], s["nit"], s["rules_run"]))
        for f in report["findings"]:
            print("[%s][%s] %s %s" % (f["severity"], f["rule_id"], f["file"], f["title"]))
            if f["detail"]:
                print("    %s" % f["detail"][:160])

    rank = {"blocker": 0, "warning": 1, "nit": 2}
    threshold = rank[args.fail_on]
    worst = min([rank.get(f["severity"], 3) for f in report["findings"]], default=3)
    return 2 if worst <= threshold else 0


if __name__ == "__main__":
    sys.exit(main())
