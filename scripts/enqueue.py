#!/usr/bin/env python3
"""下書きを _queue/（または articles/）へ、公開用に整えてコピーする。

.media/ 側の原本には `<!-- 【公開前チェック】 ... -->` という検証メモが
frontmatterの直後に入っている。ZennのMarkdownはHTMLを許可しないため、
これが残ったまま公開されると本文の先頭に生テキストで出る（2026-08-04に出した）。
cp で運ぶと必ず踏むので、コピーはこれを通す。

使い方:
    python3 scripts/enqueue.py <src.md> <dst.md>
    python3 scripts/enqueue.py <src.md> <dst.md> --dry-run
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from drip import parse_frontmatter, strip_leading_comments  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=pathlib.Path)
    parser.add_argument("dst", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true", help="書き込まず結果だけ表示する")
    args = parser.parse_args()

    text = args.src.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        print(f"[error] frontmatterがありません: {args.src}")
        return 1

    stripped = strip_leading_comments(body)
    if stripped != body:
        print(f"[strip] 冒頭の下書きメモを落としました（-{len(body) - len(stripped)}字）")

    if args.dst.exists():
        print(f"[error] 宛先が既にあります: {args.dst}")
        return 1

    out = "---\n" + fm + "---\n\n" + stripped.lstrip("\n")
    print(f"[copy ] {args.src} → {args.dst}")
    if args.dry_run:
        print("[dry-run] ファイルは変更していません。")
        return 0

    args.dst.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
