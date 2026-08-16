#!/usr/bin/env python3
"""style.py 자체 테스트."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import style  # noqa: E402

CUSTOM = "# 우리 팀 규칙\n\n- 메서드 이름은 한국어로 쓴다\n"


class StyleTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "viper" / "test-style.md"

    def run_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = style.main(["--path", str(self.path)])
        return code, out.getvalue(), err.getvalue()


class 기본값깔기(StyleTestCase):

    def test_없으면_기본값을_만든다(self):
        self.assertFalse(self.path.exists())

        path, created = style.ensure(self.path)

        self.assertTrue(created)
        self.assertTrue(path.is_file())
        self.assertIn("테스트 스타일", path.read_text(encoding="utf-8"))

    def test_없는_디렉터리도_만들어_준다(self):
        style.ensure(self.path)
        self.assertTrue(self.path.parent.is_dir())

    def test_만들었을_때만_알린다(self):
        code, _, err = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("기본값으로 만들었다", err)

        _, _, err = self.run_cli()
        self.assertEqual(err, "")


class 사용자설정보존(StyleTestCase):
    """고쳐 둔 규칙을 스킬이 되돌리면 설정이라는 말이 무의미해진다."""

    def test_이미_있으면_덮어쓰지_않는다(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(CUSTOM, encoding="utf-8")

        path, created = style.ensure(self.path)

        self.assertFalse(created)
        self.assertEqual(path.read_text(encoding="utf-8"), CUSTOM)

    def test_사용자가_쓴_내용을_그대로_낸다(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(CUSTOM, encoding="utf-8")

        code, out, _ = self.run_cli()

        self.assertEqual(code, 0)
        self.assertEqual(out, CUSTOM)

    def test_빈_파일도_사용자의_선택이라_존중한다(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("", encoding="utf-8")

        _, created = style.ensure(self.path)

        self.assertFalse(created)


class 템플릿내용(unittest.TestCase):

    def test_템플릿이_스킬에_들어_있다(self):
        self.assertTrue(style.TEMPLATE.is_file(), f"{style.TEMPLATE} 가 없다")

    def test_템플릿이_생존의_주범을_금지한다(self):
        """느슨한 단언은 이 프로젝트가 관측한 생존 뮤턴트의 주된 원인이다."""
        text = style.TEMPLATE.read_text(encoding="utf-8")
        for banned in ("isPositive()", "isNotNull()"):
            self.assertIn(banned, text)

    def test_템플릿에_프로젝트별_확장_자리가_있다(self):
        text = style.TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("프로젝트별 추가 규칙", text)


if __name__ == "__main__":
    unittest.main()
