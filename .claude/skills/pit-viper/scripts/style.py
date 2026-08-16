#!/usr/bin/env python3
"""프로젝트의 테스트 스타일 규칙을 읽어 온다. 없으면 기본값으로 만들어 준다.

에이전트가 테스트를 쓰기 전에 이걸 부른다. 스타일은 프로젝트마다 다르고
사람이 정하는 것이라, 스킬이 추측하는 대신 파일 하나를 계약으로 둔다.

**이미 있는 파일은 절대 덮어쓰지 않는다.** 사용자가 고쳐 둔 규칙을 스킬이
되돌리면 설정이라는 말이 무의미해진다.

사용:
    style.py [--path viper/test-style.md]
"""

import argparse
import shutil
import sys
from pathlib import Path

DEFAULT_PATH = "viper/test-style.md"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "test-style.md"


class StyleError(Exception):
    """스타일 규칙을 확보할 수 없을 때."""


def ensure(path=DEFAULT_PATH):
    """스타일 파일 경로를 돌려준다. 없으면 기본값을 깔고 (경로, True) 를 준다."""
    path = Path(path)
    if path.is_file():
        return path, False

    if not TEMPLATE.is_file():
        raise StyleError(f"기본 스타일 템플릿이 없다: {TEMPLATE}")

    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, path)
    return path, True


def main(argv=None):
    parser = argparse.ArgumentParser(description="테스트 스타일 규칙을 읽는다")
    parser.add_argument("--path", default=DEFAULT_PATH, help=f"스타일 파일 (기본: {DEFAULT_PATH})")
    args = parser.parse_args(argv)

    try:
        path, created = ensure(args.path)
    except StyleError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if created:
        print(f"스타일 파일이 없어 기본값으로 만들었다: {path}\n"
              f"       프로젝트 관례가 다르면 이 파일을 고치면 된다.", file=sys.stderr)

    print(path.read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
