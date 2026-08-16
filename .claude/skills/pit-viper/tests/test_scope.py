#!/usr/bin/env python3
"""scope.sh 자체 테스트.

셸 스크립트라 함수 단위로 부를 수 없다. 대신 임시 디렉터리에 진짜 git 저장소를 만들고
실제로 실행해서 stdout 과 종료 코드를 본다 — 이 스크립트의 계약이 정확히 그 둘이다.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCOPE = SKILL_DIR / "scripts" / "scope.sh"

EXIT_ERROR = 2
EXIT_NO_CHANGES = 3


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo, check=True, capture_output=True, text=True,
        # 실행 환경의 git 설정(서명, 훅, 기본 브랜치)에 결과가 흔들리지 않게 못 박는다.
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(repo),
             "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    ).stdout


def write(repo, relative_path, text="class X {}\n"):
    path = Path(repo) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scope(repo, *args):
    result = subprocess.run(
        ["bash", str(SCOPE), *args], cwd=repo, capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class ScopeTestCase(unittest.TestCase):
    """main 에 클래스 하나가 커밋돼 있고, feature 브랜치로 갈라진 저장소를 만든다."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

        git(self.dir, "init", "-q", "-b", "main")
        write(self.dir, "src/main/java/com/pitviper/Base.java")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "init")
        git(self.dir, "checkout", "-q", "-b", "feature")


class 대상선별(ScopeTestCase):

    def test_브랜치가_커밋한_클래스를_FQCN으로_낸다(self):
        write(self.dir, "src/main/java/com/pitviper/order/policy/PointPolicy.java")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "add policy")

        code, out, _ = scope(self.dir)
        self.assertEqual(code, 0)
        self.assertEqual(out, "com.pitviper.order.policy.PointPolicy")

    def test_아직_커밋하지_않은_변경도_포함한다(self):
        """개발자의 로컬 루프는 커밋 전에 돈다. 커밋된 것만 보면 방금 쓴 코드가 빠진다."""
        write(self.dir, "src/main/java/com/pitviper/Base.java", "class X { int a; }\n")

        code, out, _ = scope(self.dir)
        self.assertEqual(code, 0)
        self.assertEqual(out, "com.pitviper.Base")

    def test_git이_아직_모르는_새_파일도_포함한다(self):
        write(self.dir, "src/main/java/com/pitviper/Fresh.java")

        code, out, _ = scope(self.dir)
        self.assertEqual(code, 0)
        self.assertEqual(out, "com.pitviper.Fresh")

    def test_같은_파일이_여러_갈래에_걸쳐도_한_번만_나온다(self):
        write(self.dir, "src/main/java/com/pitviper/Base.java", "class X { int a; }\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "edit")
        write(self.dir, "src/main/java/com/pitviper/Base.java", "class X { int a, b; }\n")

        code, out, _ = scope(self.dir)
        self.assertEqual(code, 0)
        self.assertEqual(out, "com.pitviper.Base")

    def test_결과는_정렬돼_있다(self):
        for name in ("Zulu", "Alpha", "Mike"):
            write(self.dir, f"src/main/java/com/pitviper/{name}.java")

        _, out, _ = scope(self.dir)
        self.assertEqual(out.splitlines(),
                         ["com.pitviper.Alpha", "com.pitviper.Mike", "com.pitviper.Zulu"])


class 제외규칙(ScopeTestCase):

    def test_src_main_java_밖은_보지_않는다(self):
        write(self.dir, "src/test/java/com/pitviper/BaseTest.java")
        write(self.dir, "build.gradle", "// x\n")
        write(self.dir, "src/main/resources/application.yml", "a: b\n")

        code, _, err = scope(self.dir)
        self.assertEqual(code, EXIT_NO_CHANGES)
        self.assertIn("변경된 src/main/java 클래스가 없다", err)

    def test_자바가_아닌_파일은_보지_않는다(self):
        write(self.dir, "src/main/java/com/pitviper/notes.md", "# x\n")

        code, _, _ = scope(self.dir)
        self.assertEqual(code, EXIT_NO_CHANGES)

    def test_삭제된_클래스는_빠진다(self):
        """사라진 클래스에는 뮤턴트를 심을 수 없다."""
        git(self.dir, "rm", "-q", "src/main/java/com/pitviper/Base.java")
        git(self.dir, "commit", "-q", "-m", "delete")
        write(self.dir, "src/main/java/com/pitviper/Kept.java")

        code, out, _ = scope(self.dir)
        self.assertEqual(code, 0)
        self.assertEqual(out, "com.pitviper.Kept")


class 출력형식과종료코드(ScopeTestCase):

    def test_pitest_형식은_콤마_한_줄이다(self):
        write(self.dir, "src/main/java/com/pitviper/Alpha.java")
        write(self.dir, "src/main/java/com/pitviper/Bravo.java")

        code, out, _ = scope(self.dir, "main", "--pitest")
        self.assertEqual(code, 0)
        self.assertEqual(out, "com.pitviper.Alpha,com.pitviper.Bravo")

    def test_변경이_없으면_종료코드_3(self):
        code, out, err = scope(self.dir)
        self.assertEqual(code, EXIT_NO_CHANGES)
        self.assertEqual(out, "")
        self.assertIn("기준: main", err)

    def test_없는_기준ref는_오류다(self):
        code, _, err = scope(self.dir, "존재하지않는브랜치")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("기준 ref 를 찾을 수 없다", err)

    def test_모르는_옵션은_오류다(self):
        code, _, err = scope(self.dir, "--없는옵션")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("모르는 옵션", err)

    def test_git_저장소가_아니면_오류다(self):
        with tempfile.TemporaryDirectory() as plain:
            code, _, err = scope(plain)
            self.assertEqual(code, EXIT_ERROR)
            self.assertIn("git 저장소가 아니다", err)

    def test_도움말은_종료코드_0이다(self):
        code, out, _ = scope(self.dir, "--help")
        self.assertEqual(code, 0)
        self.assertIn("종료 코드", out)


if __name__ == "__main__":
    unittest.main()
