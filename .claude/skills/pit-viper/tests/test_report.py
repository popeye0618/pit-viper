#!/usr/bin/env python3
"""report.py 자체 테스트."""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import report  # noqa: E402
import verdict  # noqa: E402
from _fixtures import MUTATOR_PREFIX, mutant_id, mutation, write_report  # noqa: E402

FOO = mutant_id()
FIXED_TIME = datetime(2026, 8, 16, 13, 52, 30)


class ReportTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def build(self, before, after, mutants, run=2, budget=3, scope=None):
        state = {"version": 1, "budget": budget, "run": run, "mutants": mutants}
        return report.build(
            write_report(self.dir, "before.xml", *before),
            write_report(self.dir, "after.xml", *after),
            state, scope=scope, generated_at=FIXED_TIME,
        )


class 한국어설명(ReportTestCase):

    def test_뮤테이터를_한국어로_옮긴다(self):
        text = self.build(
            before=[mutation("SURVIVED")], after=[mutation("KILLED")],
            mutants={FOO: {"attempts": 1, "outcome": verdict.KILLED, "last_run": 2}},
        )
        self.assertIn("조건을 뒤집었다", text)
        # pitest 원문(영어)은 표에 나오지 않는다.
        self.assertNotIn("negated conditional", text)

    def test_클래스_경로가_섞인_원문도_깔끔한_한국어가_된다(self):
        boolean_true = f"{MUTATOR_PREFIX}.returns.BooleanTrueReturnValsMutator"
        text = self.build(
            before=[mutation("SURVIVED", mutator=boolean_true,
                             description="replaced boolean return with true for com/x/Y::isZero")],
            after=[mutation("KILLED", mutator=boolean_true,
                            description="replaced boolean return with true for com/x/Y::isZero")],
            mutants={mutant_id(mutator="BooleanTrueReturnVals"):
                     {"attempts": 0, "outcome": verdict.KILLED, "last_run": 1}},
        )
        self.assertIn("반환값을 항상 `true` 로 바꿨다", text)
        self.assertNotIn("com/x/Y::isZero", text)

    def test_모르는_뮤테이터는_영어_원문으로_떨어진다(self):
        """표시 계층이라 번역이 없다고 리포트를 못 내면 안 된다."""
        unknown = f"{MUTATOR_PREFIX}.experimental.낯선Mutator"
        text = self.build(
            before=[mutation("SURVIVED", mutator=unknown, description="did something novel")],
            after=[mutation("SURVIVED", mutator=unknown, description="did something novel")],
            mutants={mutant_id(mutator="낯선"):
                     {"attempts": 1, "outcome": verdict.SURVIVING, "last_run": 1}},
        )
        self.assertIn("did something novel", text)

    def test_번역표는_기준선의_뮤테이터_7종을_모두_덮는다(self):
        baseline_mutators = [
            "ConditionalsBoundary", "NegateConditionals", "RemoveConditional_ORDER_ELSE",
            "RemoveConditional_EQUAL_ELSE", "BooleanTrueReturnVals", "BooleanFalseReturnVals",
            "Math", "PrimitiveReturns", "NullReturnVals",
        ]
        for name in baseline_mutators:
            self.assertIn(name, report.MUTATOR_KO, f"{name} 번역이 없다")


class 머리말(ReportTestCase):

    def test_생성_시각과_범위가_들어간다(self):
        text = self.build(
            before=[mutation("SURVIVED")], after=[mutation("SURVIVED")],
            mutants={FOO: {"attempts": 1, "outcome": verdict.SURVIVING, "last_run": 1}},
            scope="com.pitviper.order.policy.PointPolicy",
        )
        self.assertIn("2026-08-16 13:52:30", text)
        self.assertIn("com.pitviper.order.policy.PointPolicy", text)

    def test_범위를_안_주면_전체로_적는다(self):
        text = self.build(
            before=[mutation("SURVIVED")], after=[mutation("SURVIVED")],
            mutants={FOO: {"attempts": 1, "outcome": verdict.SURVIVING, "last_run": 1}},
        )
        self.assertIn("| 대상 범위 | 전체 |", text)

    def test_회전_수와_예산을_적는다(self):
        text = self.build(
            before=[mutation("SURVIVED")], after=[mutation("KILLED")],
            mutants={FOO: {"attempts": 1, "outcome": verdict.KILLED, "last_run": 3}},
            run=3, budget=5,
        )
        self.assertIn("3회 · 뮤턴트당 시도 예산 5회", text)


class 내용(ReportTestCase):

    def test_요약_숫자는_리포트에서_나온다(self):
        text = self.build(
            before=[mutation("SURVIVED", line=10), mutation("SURVIVED", line=11)],
            after=[mutation("KILLED", line=10), mutation("SURVIVED", line=11)],
            mutants={
                mutant_id(line=10): {"attempts": 1, "outcome": verdict.KILLED, "last_run": 1},
                mutant_id(line=11): {"attempts": 1, "outcome": verdict.SURVIVING, "last_run": 1},
            },
        )
        self.assertIn("| 잡힌 뮤턴트 | 0/2 | **1/2** |", text)
        self.assertIn("| 구멍 (생존 + 무커버) | 2 | **1** |", text)
        self.assertIn("구멍 2개 중 **1개를 죽였다** (50%)", text)

    def test_동등_뮤턴트는_사유를_본문으로_싣는다(self):
        text = self.build(
            before=[mutation("SURVIVED")], after=[mutation("SURVIVED")],
            mutants={FOO: {"attempts": 1, "outcome": verdict.EQUIVALENT, "last_run": 1,
                           "reason": "도달 가능한 입력이 없다"}},
        )
        self.assertIn("## 동등 뮤턴트로 닫은 것 (1)", text)
        self.assertIn("동등으로 판정한 이유", text)
        self.assertIn("도달 가능한 입력이 없다", text)

    def test_비어_있는_절은_싣지_않는다(self):
        text = self.build(
            before=[mutation("SURVIVED")], after=[mutation("KILLED")],
            mutants={FOO: {"attempts": 0, "outcome": verdict.KILLED, "last_run": 1}},
        )
        self.assertIn("## 죽인 뮤턴트 (1)", text)
        self.assertNotIn("동등 뮤턴트로 닫은 것", text)
        self.assertNotIn("예산을 소진해", text)


class 낡은리포트검출(ReportTestCase):
    """state 는 죽었다는데 후 리포트에는 살아 있다 = 후 리포트가 낡았다."""

    def test_어긋나면_리포트_머리에_경고를_박는다(self):
        text = self.build(
            before=[mutation("SURVIVED")],
            after=[mutation("SURVIVED")],          # 낡아서 아직 SURVIVED
            mutants={FOO: {"attempts": 1, "outcome": verdict.KILLED, "last_run": 1}},
        )
        self.assertIn("아래 '후' 숫자를 믿지 말 것", text)

    def test_어긋나지_않으면_경고가_없다(self):
        text = self.build(
            before=[mutation("SURVIVED")],
            after=[mutation("KILLED")],
            mutants={FOO: {"attempts": 1, "outcome": verdict.KILLED, "last_run": 1}},
        )
        self.assertNotIn("믿지 말 것", text)


class 출력경로(unittest.TestCase):

    def test_파일명에_시각이_박힌다(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = report.output_path(Path(tmp) / "viper", FIXED_TIME)
            self.assertEqual(path.name, "pit-viper-20260816-135230.md")

    def test_없는_디렉터리는_만들어_준다(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "viper"
            self.assertFalse(target.exists())
            report.output_path(target, FIXED_TIME)
            self.assertTrue(target.is_dir())

    def test_같은_초가_아니면_파일이_덮이지_않는다(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = report.output_path(tmp, datetime(2026, 8, 16, 13, 52, 30))
            second = report.output_path(tmp, datetime(2026, 8, 16, 13, 52, 31))
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
