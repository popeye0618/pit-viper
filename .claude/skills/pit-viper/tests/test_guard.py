#!/usr/bin/env python3
"""guard.sh 자체 테스트 — 임시 git 저장소를 만들어 실제로 실행한다."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
GUARD = SKILL_DIR / "scripts" / "guard.sh"

EXIT_VIOLATION = 1
EXIT_ERROR = 2

GIT_ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          text=True, env={**GIT_ENV, "HOME": str(repo)}).stdout


def write(repo, relative_path, text="x\n"):
    path = Path(repo) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def guard(repo, *args, env=None):
    result = subprocess.run(["bash", str(GUARD), *args], cwd=repo,
                            capture_output=True, text=True, env=env)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class GuardTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

        git(self.dir, "init", "-q", "-b", "main")
        write(self.dir, "src/main/java/com/pitviper/Money.java")
        write(self.dir, "src/main/resources/application.yml", "a: b\n")
        write(self.dir, "src/test/java/com/pitviper/MoneyTest.java")
        write(self.dir, "build.gradle", "// build\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "init")


class 스냅숏기준(GuardTestCase):
    """판정 기준은 "이번 실행 중에 바뀌었는가"이지 "커밋됐는가"가 아니다."""

    def test_이미_있던_미커밋_작업은_위반이_아니다(self):
        """스킬이 도는 자리는 대개 아직 커밋하지 않은 새 기능 위다."""
        write(self.dir, "src/main/java/com/pitviper/New.java")     # 사용자가 쓰던 새 파일
        guard(self.dir, "snapshot")                                 # 루프 시작

        code, out, _ = guard(self.dir)
        self.assertEqual(code, 0)
        self.assertIn("루프 시작 이후", out)

    def test_스냅숏_이후_수정은_잡는다(self):
        write(self.dir, "src/main/java/com/pitviper/New.java")
        guard(self.dir, "snapshot")

        write(self.dir, "src/main/java/com/pitviper/New.java", "// 에이전트가 고쳤다\n")

        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("New.java", err)

    def test_스냅숏_이후_추가도_잡는다(self):
        guard(self.dir, "snapshot")
        write(self.dir, "src/main/java/com/pitviper/Sneaky.java")

        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("Sneaky.java", err)

    def test_스냅숏_이후_삭제도_잡는다(self):
        guard(self.dir, "snapshot")
        (Path(self.dir) / "src/main/java/com/pitviper/Money.java").unlink()

        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("Money.java", err)

    def test_스냅숏이_있으면_테스트_수정은_여전히_통과한다(self):
        guard(self.dir, "snapshot")
        write(self.dir, "src/test/java/com/pitviper/NewTest.java")

        self.assertEqual(guard(self.dir)[0], 0)

    def test_지문_개수를_알려준다(self):
        code, out, _ = guard(self.dir, "snapshot")
        self.assertEqual(code, 0)
        self.assertIn("지문", out)


class 허용(GuardTestCase):

    def test_아무것도_안_바꾸면_통과한다(self):
        code, out, _ = guard(self.dir)
        self.assertEqual(code, 0)
        self.assertIn("위반 없음", out)

    def test_테스트_수정은_통과한다(self):
        write(self.dir, "src/test/java/com/pitviper/MoneyTest.java", "// 새 테스트\n")
        code, _, _ = guard(self.dir)
        self.assertEqual(code, 0)

    def test_새_테스트_파일_추가도_통과한다(self):
        write(self.dir, "src/test/java/com/pitviper/NewTest.java")
        code, _, _ = guard(self.dir)
        self.assertEqual(code, 0)


class 차단(GuardTestCase):

    def test_src_main_수정은_막는다(self):
        write(self.dir, "src/main/java/com/pitviper/Money.java", "// 고쳤다\n")
        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("src/main/java/com/pitviper/Money.java", err)

    def test_src_main_에_새_파일을_넣는_것도_막는다(self):
        write(self.dir, "src/main/java/com/pitviper/Sneaky.java")
        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("Sneaky.java", err)

    def test_src_main_resources_수정도_막는다(self):
        write(self.dir, "src/main/resources/application.yml", "a: c\n")
        code, _, _ = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)

    def test_빌드_파일_수정은_막는다(self):
        """excludedClasses 한 줄이면 생존 뮤턴트가 통째로 사라진다 — 코드보다 조용한 우회로다."""
        write(self.dir, "build.gradle", "// excludedClasses 추가\n")
        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("build.gradle", err)

    def test_스테이징된_변경도_잡는다(self):
        write(self.dir, "src/main/java/com/pitviper/Money.java", "// 고쳤다\n")
        git(self.dir, "add", "-A")
        code, _, _ = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)

    def test_여러_위반을_한꺼번에_보여준다(self):
        write(self.dir, "src/main/java/com/pitviper/Money.java", "// 1\n")
        write(self.dir, "build.gradle", "// 2\n")
        code, _, err = guard(self.dir)
        self.assertEqual(code, EXIT_VIOLATION)
        self.assertIn("Money.java", err)
        self.assertIn("build.gradle", err)


class 기준ref와설정(GuardTestCase):

    def test_커밋해_숨긴_변경은_base를_줘야_잡힌다(self):
        write(self.dir, "src/main/java/com/pitviper/Money.java", "// 고쳤다\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "sneak")

        # 커밋해 버리면 워킹 트리는 깨끗해 보인다.
        self.assertEqual(guard(self.dir)[0], 0)
        # 기준을 주면 커밋된 것까지 본다.
        self.assertEqual(guard(self.dir, "--base", "HEAD~1")[0], EXIT_VIOLATION)

    def test_없는_기준ref는_오류다(self):
        code, _, err = guard(self.dir, "--base", "없는브랜치")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("기준 ref 를 찾을 수 없다", err)

    def test_보호_경로는_환경변수로_바꿀_수_있다(self):
        write(self.dir, "src/main/java/com/pitviper/Money.java", "// 고쳤다\n")
        code, _, _ = guard(self.dir, env={**GIT_ENV, "HOME": self.dir,
                                          "PIT_VIPER_GUARD_REGEX": "^src/production/"})
        self.assertEqual(code, 0)

    def test_git_저장소가_아니면_오류다(self):
        with tempfile.TemporaryDirectory() as plain:
            code, _, err = guard(plain)
            self.assertEqual(code, EXIT_ERROR)
            self.assertIn("git 저장소가 아니다", err)

    def test_모르는_인자는_오류다(self):
        code, _, err = guard(self.dir, "--없는옵션")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("모르는 인자", err)


if __name__ == "__main__":
    unittest.main()
