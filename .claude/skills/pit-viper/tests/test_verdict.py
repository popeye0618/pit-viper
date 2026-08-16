#!/usr/bin/env python3
"""verdict.py 자체 테스트.

전/후 리포트를 손으로 조작해 뮤턴트가 갈 수 있는 다섯 갈래를 각각 통과시킨다.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import verdict  # noqa: E402
from _fixtures import mutant_id, mutation, write_report  # noqa: E402

FOO = mutant_id()                                    # com.pitviper.Foo#bar:10:NegateConditionals:5
BAZ = mutant_id(cls="com.pitviper.Baz", line=20)     # 두 번째 뮤턴트


class VerdictTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.state_path = self.dir / "state.json"

    def compare(self, before, after, budget=None):
        """조각 목록 두 벌로 판정을 돌리고 (결과, 상태)를 돌려준다."""
        before_path = write_report(self.dir, "before.xml", *before)
        after_path = write_report(self.dir, "after.xml", *after)
        state = verdict.load_state(self.state_path, budget)
        result = verdict.compare(before_path, after_path, state)
        verdict.save_state(self.state_path, state)
        return result, state

    def outcome(self, mutant_id_):
        return json.loads(self.state_path.read_text(encoding="utf-8"))["mutants"][mutant_id_]


class 다섯갈래(VerdictTestCase):

    def test_생존이던_뮤턴트가_잡히면_킬이다(self):
        result, _ = self.compare(
            before=[mutation("SURVIVED")],
            after=[mutation("KILLED")],
        )
        self.assertEqual(result["killed"], [FOO])
        self.assertEqual(result["summary"]["next_targets"], 0)
        self.assertEqual(self.outcome(FOO)["outcome"], "killed")

    def test_여전히_생존이면_시도_횟수가_오른다(self):
        result, _ = self.compare(
            before=[mutation("SURVIVED")],
            after=[mutation("SURVIVED")],
        )
        self.assertEqual(result["still_surviving"], [FOO])
        self.assertEqual(self.outcome(FOO)["attempts"], 1)
        self.assertEqual(result["next_targets"][0]["attempts_left"], 2)

    def test_전에_있던_뮤턴트가_사라지면_경고한다(self):
        """src/main 이 고정이면 id 는 결정적이다. 사라졌다면 무언가 바뀐 것이다."""
        result, _ = self.compare(
            before=[mutation("SURVIVED"), mutation("SURVIVED", cls="com.pitviper.Baz", line=20)],
            after=[mutation("SURVIVED")],
        )
        self.assertEqual(result["gone"], [BAZ])
        self.assertEqual(self.outcome(BAZ)["outcome"], "gone")
        self.assertIn("src/main 이 수정됐거나", result["warnings"][0])

    def test_잡혔던_뮤턴트가_다시_살아나면_퇴행이다(self):
        result, _ = self.compare(
            before=[mutation("KILLED")],
            after=[mutation("SURVIVED")],
        )
        self.assertEqual(result["regressed"], [FOO])
        self.assertIn("다시 살아났다", result["warnings"][0])

    def test_없던_뮤턴트가_생기면_새_목표다(self):
        result, _ = self.compare(
            before=[mutation("SURVIVED")],
            after=[mutation("SURVIVED"), mutation("SURVIVED", cls="com.pitviper.Baz", line=20)],
        )
        self.assertEqual(result["new"], [BAZ])
        self.assertEqual(self.outcome(BAZ)["attempts"], 0)
        self.assertEqual(result["summary"]["next_targets"], 2)


class 예산강제(VerdictTestCase):
    """원칙 4 — 예산은 지침이 아니라 상태 파일이 강제한다."""

    def test_예산을_소진하면_다음_목표에서_기계적으로_빠진다(self):
        survived = [mutation("SURVIVED")]

        for expected_attempts in (1, 2):
            result, _ = self.compare(survived, survived, budget=3)
            self.assertEqual(self.outcome(FOO)["attempts"], expected_attempts)
            self.assertEqual(result["summary"]["next_targets"], 1)

        result, _ = self.compare(survived, survived, budget=3)
        self.assertEqual(self.outcome(FOO)["outcome"], "exhausted")
        self.assertEqual(result["summary"]["next_targets"], 0)
        self.assertEqual(result["closed"]["exhausted"], [FOO])

    def test_소진된_뮤턴트는_다시_돌려도_시도가_늘지_않는다(self):
        """닫힌 목표는 에이전트에게 준 적이 없다. 시도로 세면 기록이 거짓이 된다."""
        survived = [mutation("SURVIVED")]
        for _ in range(3):
            self.compare(survived, survived, budget=3)
        self.assertEqual(self.outcome(FOO)["attempts"], 3)

        self.compare(survived, survived)
        self.assertEqual(self.outcome(FOO)["attempts"], 3)

    def test_예산을_1로_주면_한_번에_소진된다(self):
        result, _ = self.compare([mutation("SURVIVED")], [mutation("SURVIVED")], budget=1)
        self.assertEqual(result["summary"]["next_targets"], 0)

    def test_예산은_상태_파일에_남고_다음_실행이_이어받는다(self):
        self.compare([mutation("SURVIVED")], [mutation("SURVIVED")], budget=5)
        _, state = self.compare([mutation("SURVIVED")], [mutation("SURVIVED")])
        self.assertEqual(state["budget"], 5)

    def test_소진된_뮤턴트가_나중에_잡히면_킬로_기록된다(self):
        """예산은 목표에서 빼는 장치이지, 성과를 못 본 척하는 장치가 아니다."""
        survived = [mutation("SURVIVED")]
        self.compare(survived, survived, budget=1)
        self.assertEqual(self.outcome(FOO)["outcome"], "exhausted")

        result, _ = self.compare(survived, [mutation("KILLED")])
        self.assertEqual(result["killed"], [FOO])
        self.assertEqual(self.outcome(FOO)["outcome"], "killed")


class 동등뮤턴트(VerdictTestCase):

    def report(self, *mutations):
        return write_report(self.dir, "mutations.xml", *mutations)

    def test_사유가_없으면_닫지_못한다(self):
        report = self.report(mutation("SURVIVED"))
        state = verdict.load_state(self.state_path)
        for blank in ("", "   ", None):
            with self.assertRaises(verdict.VerdictError) as caught:
                verdict.mark_equivalent(state, FOO, blank, report)
            self.assertIn("조용한 포기", str(caught.exception))

    def test_리포트에_없는_id는_닫지_못한다(self):
        """오타난 id 를 받아주면 아무것도 닫지 못한 채 닫았다고 믿게 된다."""
        report = self.report(mutation("SURVIVED"))
        state = verdict.load_state(self.state_path)
        with self.assertRaises(verdict.VerdictError) as caught:
            verdict.mark_equivalent(state, "com.pitviper.Oops#x:1:Math:1", "동등하다", report)
        self.assertIn("없는 id", str(caught.exception))

    def test_이미_잡힌_뮤턴트는_닫지_못한다(self):
        report = self.report(mutation("KILLED"))
        state = verdict.load_state(self.state_path)
        with self.assertRaises(verdict.VerdictError):
            verdict.mark_equivalent(state, FOO, "동등하다", report)

    def test_닫으면_목표에서_빠지고_사유가_남는다(self):
        report = self.report(mutation("SURVIVED"))
        state = verdict.load_state(self.state_path)
        verdict.mark_equivalent(state, FOO, "상수 경계가 의미상 동일하다", report)
        verdict.save_state(self.state_path, state)

        result, _ = self.compare([mutation("SURVIVED")], [mutation("SURVIVED")])
        self.assertEqual(result["summary"]["next_targets"], 0)
        self.assertEqual(result["closed"]["equivalent"], [FOO])
        self.assertEqual(self.outcome(FOO)["reason"], "상수 경계가 의미상 동일하다")
        # 닫힌 목표라 시도로 세지 않는다.
        self.assertEqual(self.outcome(FOO)["attempts"], 0)


class 상태파일(VerdictTestCase):

    def test_없으면_새로_시작한다(self):
        state = verdict.load_state(self.dir / "없는파일.json")
        self.assertEqual(state["run"], 0)
        self.assertEqual(state["mutants"], {})

    def test_깨졌으면_에러로_터진다(self):
        self.state_path.write_text("{어쩌구", encoding="utf-8")
        with self.assertRaises(verdict.VerdictError) as caught:
            verdict.load_state(self.state_path)
        self.assertIn("깨졌다", str(caught.exception))

    def test_버전이_다르면_에러로_터진다(self):
        self.state_path.write_text('{"version": 99, "mutants": {}}', encoding="utf-8")
        with self.assertRaises(verdict.VerdictError) as caught:
            verdict.load_state(self.state_path)
        self.assertIn("버전이 다르다", str(caught.exception))

    def test_키가_정렬돼_저장된다(self):
        """이 파일의 diff 가 곧 감사 로그다. 순서가 흔들리면 읽을 수 없다."""
        self.compare(
            [mutation("SURVIVED", cls="com.pitviper.Zulu"), mutation("SURVIVED", cls="com.pitviper.Alpha")],
            [mutation("SURVIVED", cls="com.pitviper.Zulu"), mutation("SURVIVED", cls="com.pitviper.Alpha")],
        )
        text = self.state_path.read_text(encoding="utf-8")
        self.assertLess(text.index("com.pitviper.Alpha"), text.index("com.pitviper.Zulu"))
        self.assertLess(text.index('"budget"'), text.index('"mutants"'))

    def test_실행_횟수가_쌓인다(self):
        for expected_run in (1, 2, 3):
            _, state = self.compare([mutation("SURVIVED")], [mutation("SURVIVED")])
            self.assertEqual(state["run"], expected_run)


class 종료코드(VerdictTestCase):

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = verdict.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_정상_판정은_0이다(self):
        before = write_report(self.dir, "before.xml", mutation("SURVIVED"))
        after = write_report(self.dir, "after.xml", mutation("KILLED"))
        code, out, _ = self.run_cli("--state", str(self.state_path), "compare", str(before), str(after))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["killed"], [FOO])

    def test_퇴행이_있으면_1이다(self):
        """전에 잡혔던 것이 살아난 것은 넘어가면 안 되는 실패다."""
        before = write_report(self.dir, "before.xml", mutation("KILLED"))
        after = write_report(self.dir, "after.xml", mutation("SURVIVED"))
        code, _, err = self.run_cli("--state", str(self.state_path), "compare", str(before), str(after))
        self.assertEqual(code, verdict.EXIT_REGRESSION)
        self.assertIn("다시 살아났다", err)

    def test_리포트가_없으면_2다(self):
        code, _, err = self.run_cli("--state", str(self.state_path), "compare", "없다.xml", "없다.xml")
        self.assertEqual(code, verdict.EXIT_ERROR)
        self.assertIn("리포트가 없다", err)

    def test_사유_없는_equivalent_는_argparse가_막는다(self):
        report = write_report(self.dir, "mutations.xml", mutation("SURVIVED"))
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                verdict.main(["--state", str(self.state_path), "equivalent", FOO, "--report", str(report)])


if __name__ == "__main__":
    unittest.main()
