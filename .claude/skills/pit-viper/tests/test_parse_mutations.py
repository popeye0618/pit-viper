#!/usr/bin/env python3
"""parse_mutations.py 자체 테스트.

실행:
    python3 -m unittest discover -s .claude/skills/pit-viper/tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

# 스킬은 패키지가 아니라 '복사하면 도는 디렉터리'다. 그래서 설치 대신 경로를 직접 얹는다.
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import parse_mutations  # noqa: E402  (경로를 얹은 뒤여야 import 된다)
from _fixtures import MUTATOR_PREFIX, mutation, mutations_xml  # noqa: E402

# 기준선 리포트를 픽스처로 박아 둔다.
# build/reports 를 직접 읽으면 루프가 테스트를 강화한 뒤 이 검증이 깨진다 —
# 실제로 S5 에서 깨졌다. 픽스처로 두면 clone 직후 빌드 없이도 돈다.
REAL_REPORT = SKILL_DIR / "tests" / "fixtures" / "baseline-mutations.xml"


def parse(*mutations):
    """<mutation> 조각들을 임시 파일에 담아 파싱한다."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mutations.xml"
        path.write_text(mutations_xml(*mutations), encoding="utf-8")
        return parse_mutations.parse_report(path)


class 식별자(unittest.TestCase):

    def test_한_줄에_같은_뮤테이터가_두_번_적용돼도_id가_갈린다(self):
        """실제 Customer.isVip() 케이스 — `member && grade == Grade.VIP`.

        같은 클래스·메서드·라인·뮤테이터인데 하나는 살고 하나는 죽는다.
        indexes 가 빠지면 두 뮤턴트가 한 id 로 뭉개져 죽일 수 있는 쪽까지 잃는다.
        """
        result = parse(
            mutation(status="SURVIVED", cls="com.pitviper.customer.entity.Customer",
                     method="isVip", line=26, indexes=(5,)),
            mutation(status="KILLED", cls="com.pitviper.customer.entity.Customer",
                     method="isVip", line=26, indexes=(9,)),
        )

        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["summary"]["gaps"], 1)
        self.assertEqual(
            result["survivors"][0]["id"],
            "com.pitviper.customer.entity.Customer#isVip:26:NegateConditionals:5",
        )

    def test_id가_겹치면_에러로_터진다(self):
        duplicate = mutation(status="SURVIVED", indexes=(5,))
        with self.assertRaises(parse_mutations.MutationReportError) as caught:
            parse(duplicate, duplicate)
        self.assertIn("겹친다", str(caught.exception))

    def test_뮤테이터_이름은_가운데_Mutator까지_지운다(self):
        self.assertEqual(
            parse_mutations.short_mutator(f"{MUTATOR_PREFIX}.RemoveConditionalMutator_EQUAL_ELSE"),
            "RemoveConditional_EQUAL_ELSE",
        )
        self.assertEqual(
            parse_mutations.short_mutator(f"{MUTATOR_PREFIX}.returns.NullReturnValsMutator"),
            "NullReturnVals",
        )

    def test_축약_이름이_겹치면_에러로_터진다(self):
        with self.assertRaises(parse_mutations.MutationReportError) as caught:
            parse(
                mutation(status="SURVIVED", mutator=f"{MUTATOR_PREFIX}.MathMutator"),
                mutation(status="SURVIVED", line=11, mutator=f"{MUTATOR_PREFIX}.other.MathMutator"),
            )
        self.assertIn("축약", str(caught.exception))


class 상태분류(unittest.TestCase):

    def test_생존_목록에는_SURVIVED와_NO_COVERAGE만_담긴다(self):
        result = parse(
            mutation(status="SURVIVED", line=10),
            mutation(status="NO_COVERAGE", line=11, tests_run=0),
            mutation(status="KILLED", line=12),
        )
        self.assertEqual([m["status"] for m in result["survivors"]], ["SURVIVED", "NO_COVERAGE"])
        self.assertEqual(result["summary"]["gaps"], 2)

    def test_타임아웃과_메모리에러도_잡힌_것으로_센다(self):
        result = parse(
            mutation(status="KILLED", line=10),
            mutation(status="TIMED_OUT", line=11),
            mutation(status="MEMORY_ERROR", line=12),
        )
        self.assertEqual(result["summary"]["killed"], 3)
        self.assertEqual(result["summary"]["gaps"], 0)
        self.assertEqual(result["summary"]["mutation_score"], 100.0)

    def test_실행불가_뮤턴트는_분모에서_빠진다(self):
        result = parse(
            mutation(status="KILLED", line=10),
            mutation(status="SURVIVED", line=11),
            mutation(status="NON_VIABLE", line=12),
            mutation(status="RUN_ERROR", line=13),
        )
        self.assertEqual(result["summary"]["total"], 4)
        self.assertEqual(result["summary"]["excluded"], 2)
        # 성과도 목표도 아니므로 1/2 이지 1/4 가 아니다.
        self.assertEqual(result["summary"]["mutation_score"], 50.0)

    def test_모르는_상태값은_조용히_무시하지_않는다(self):
        with self.assertRaises(parse_mutations.MutationReportError) as caught:
            parse(mutation(status="TELEPORTED"))
        self.assertIn("TELEPORTED", str(caught.exception))


class 입력검증(unittest.TestCase):

    def test_리포트가_없으면_돌릴_명령을_알려준다(self):
        with self.assertRaises(parse_mutations.MutationReportError) as caught:
            parse_mutations.parse_report("없는경로/mutations.xml")
        self.assertIn("gradlew pitest", str(caught.exception))

    def test_망가진_XML은_에러로_터진다(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutations.xml"
            path.write_text("<mutations><mutation>", encoding="utf-8")
            with self.assertRaises(parse_mutations.MutationReportError):
                parse_mutations.parse_report(path)

    def test_필수_필드가_빠지면_에러로_터진다(self):
        broken = (
            "<mutation status='SURVIVED'><sourceFile>Foo.java</sourceFile>"
            f"<mutator>{MUTATOR_PREFIX}.MathMutator</mutator></mutation>"
        )
        with self.assertRaises(parse_mutations.MutationReportError) as caught:
            parse(broken)
        self.assertIn("mutatedClass", str(caught.exception))


class 출력계약(unittest.TestCase):

    def test_생존_목록은_클래스_라인_순으로_정렬된다(self):
        result = parse(
            mutation(status="SURVIVED", cls="com.pitviper.Zulu", line=5),
            mutation(status="SURVIVED", cls="com.pitviper.Alpha", line=99),
            mutation(status="SURVIVED", cls="com.pitviper.Alpha", line=3),
        )
        self.assertEqual(
            [(m["class"], m["line"]) for m in result["survivors"]],
            [("com.pitviper.Alpha", 3), ("com.pitviper.Alpha", 99), ("com.pitviper.Zulu", 5)],
        )

    def test_뮤턴트마다_테스트를_쓰는데_필요한_좌표가_들어있다(self):
        survivor = parse(mutation(status="SURVIVED"))["survivors"][0]
        self.assertEqual(
            set(survivor),
            {"id", "class", "source_file", "method", "line", "mutator",
             "indexes", "status", "description", "tests_run"},
        )


class 기준선재현(unittest.TestCase):
    # 픽스처는 저장소에 커밋돼 있다. 없으면 조용히 건너뛰지 말고 터져야 한다.
    """CLAUDE.md 에 고정한 기준선을 파서가 그대로 뽑아내는지 본다."""

    @classmethod
    def setUpClass(cls):
        cls.result = parse_mutations.parse_report(REAL_REPORT)

    def test_기준선_숫자를_재현한다(self):
        self.assertEqual(
            self.result["summary"] | {"by_status": None},
            {
                "total": 77,
                "killed": 51,
                "survived": 24,
                "no_coverage": 2,
                "excluded": 0,
                "gaps": 26,
                "mutation_score": 66.23,
                "by_status": None,
            },
        )

    def test_실제_리포트에서도_id가_전부_유일하다(self):
        ids = [m["id"] for m in self.result["survivors"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_Customer_isVip의_두_뮤턴트가_실제로_갈린다(self):
        """indexes 함정이 이 프로젝트에 실재하는지 확인한다."""
        negated = [
            m for m in self.result["survivors"]
            if m["class"].endswith("Customer") and m["mutator"] == "NegateConditionals"
        ]
        # 같은 줄에 조건이 둘인데 하나만 살아남았다 = id 가 갈리지 않으면 이 하나를 잃는다.
        self.assertEqual(len(negated), 1)
        self.assertEqual(negated[0]["line"], 26)


if __name__ == "__main__":
    unittest.main()
