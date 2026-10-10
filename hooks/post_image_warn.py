#!/usr/bin/env python3
"""lhg-ecom-design 硬门②（警告级，不拦截）：写入图片文件超过 500KB 时提醒压缩。

触发：PostToolUse / Write|Edit。只做提醒，永远 exit 0、不拦截写入。

逃生方式：LHG_ED_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-ecom-design 停用整个插件。
零第三方依赖。
"""

import json
import os
import sys

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
WARN_KB = 500
SKIP_DIR_PARTS = {"node_modules", "dist", "build", ".git", "__pycache__",
                  "fixtures", ".next"}


def main() -> int:
    if os.environ.get("LHG_ED_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0

    _, ext = os.path.splitext(file_path)
    if ext.lower() not in IMAGE_EXTS:
        return 0
    if any(p in file_path.replace("\\", "/").split("/") for p in SKIP_DIR_PARTS):
        return 0
    try:
        kb = os.path.getsize(file_path) / 1024
    except OSError:
        return 0
    if kb <= WARN_KB:
        return 0

    msg = (
        "图片体积提醒（lhg-ecom-design）：%s 约 %.0fKB，超过 %dKB。\n"
        "手机端加载慢会拖点击率，建议压缩到 %dKB 以内（JPG 质量 80 左右）再上传。\n"
        "关闭本提醒：export LHG_ED_HOOKS_OFF=1（当前会话有效）。"
    ) % (file_path, kb, WARN_KB, WARN_KB)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
