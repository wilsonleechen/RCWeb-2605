#!/usr/bin/env python3
"""Fail a Rexpand publish if its page snapshot would restore stale content.

Run this before every OSS upload. This is a guard, not an uploader: another
process with OSS write access can bypass it, so keep one authorized publisher.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_START = "  const ARTICLES = ["
ARTICLE_END = "// @data:articles:end"
REQUIRED = {
    "40 次辅导": '<span class="num">40<small>次</small></span>',
    "五行等高": "grid-template-rows: auto repeat(5, 96px)",
    "铂金计划内推投递": (
        '<div class="pkg-cell diamond"><span class="check">✓</span></div>\n'
        '        <div class="pkg-cell"><span class="check">✓</span></div>'
    ),
    "工作经历": "背景提升项目<small>工作经历</small>",
    "六个背景提升方向": "ALL 6 TRACKS",
    "手机文章表格横向滚动": "#page-article .art-body table{",
}
FORBIDDEN = ("按合同退款", "保Offer", "保 Offer", "OUTCOME GUARANTEE")


def body(html: str) -> str:
    match = re.search(r"<body(?:\s[^>]*)?>", html, flags=re.IGNORECASE)
    if not match:
        raise ValueError("找不到 <body>，文件不是完整网页")
    return html[match.end() :]


def article_slugs(html: str) -> set[str]:
    start = html.find(ARTICLE_START)
    if start < 0:
        raise ValueError("找不到 ARTICLES 数据")
    end = html.find(ARTICLE_END, start)
    if end < 0:
        raise ValueError("找不到 ARTICLES 结束标记")
    return set(re.findall(r"\bslug:\s*'([^']+)'", html[start:end]))


def check(root: Path, live_url: str | None, pages_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    files = {name: root / name for name in ("index.html", "production-index.html", "production-offer.html")}
    for name, path in files.items():
        if not path.is_file():
            errors.append(f"缺少 {name}")
    if errors:
        return errors

    index = files["index.html"].read_text(encoding="utf-8")
    production_index = files["production-index.html"].read_text(encoding="utf-8")
    production_offer = files["production-offer.html"].read_text(encoding="utf-8")

    if index != production_index:
        errors.append("production-index.html 与 index.html 不一致；先从最新 index.html 重新生成发布快照")
    try:
        index_body = body(index)
        if index_body != body(production_offer):
            errors.append("production-offer.html 的页面主体与 index.html 不一致；不能用旧套餐页面发布")
    except ValueError as exc:
        errors.append(str(exc))
        index_body = None

    if pages_dir is not None:
        if not pages_dir.is_dir():
            errors.append(f"页面发布目录不存在：{pages_dir}")
        elif index_body is not None:
            for page in pages_dir.rglob("*.html"):
                if page.stat().st_size < 500_000:  # 404、验证页等独立小页面
                    continue
                try:
                    if body(page.read_text(encoding="utf-8")) != index_body:
                        errors.append(f"子页仍含旧版页面主体：{page}")
                except (OSError, UnicodeError, ValueError) as exc:
                    errors.append(f"无法检查子页 {page}：{exc}")

    for label, marker in REQUIRED.items():
        if marker not in index:
            errors.append(f"index.html 缺少已确认的内容：{label}")
    for marker in FORBIDDEN:
        if marker in index:
            errors.append(f"index.html 出现已删除的旧文案：{marker}")

    try:
        local_slugs = article_slugs(index)
    except ValueError as exc:
        errors.append(str(exc))
        local_slugs = set()

    if live_url:
        try:
            request = urllib.request.Request(live_url, headers={"User-Agent": "RexpandReleaseCheck/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                live_html = response.read().decode("utf-8")
            missing = article_slugs(live_html) - local_slugs
            if missing:
                preview = ", ".join(sorted(missing)[:8])
                errors.append(f"本地缺少线上已有的 {len(missing)} 篇文章：{preview}；先合并线上内容")
        except (OSError, UnicodeError, ValueError, urllib.error.URLError) as exc:
            errors.append(f"无法核对线上文章，停止发布：{exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="网站目录，默认脚本上级目录")
    parser.add_argument("--pages-dir", type=Path, help="可选：检查准备上传的全部 HTML 子页与首页主体一致")
    parser.add_argument(
        "--live",
        nargs="?",
        const="https://rexpandcareer.com/",
        help="同时核对线上已有文章；不填网址时检查官网首页",
    )
    args = parser.parse_args()
    errors = check(args.root, args.live, args.pages_dir)
    if errors:
        for error in errors:
            print("BLOCK:", error, file=sys.stderr)
        return 1
    print("发布前检查通过：页面快照、关键服务内容和文章数据一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
