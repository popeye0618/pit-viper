#!/usr/bin/env python3
"""parse_jacoco.py 자체 테스트."""

import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import parse_jacoco  # noqa: E402

REPO_ROOT = SKILL_DIR.parent.parent.parent
REAL_REPORT = REPO_ROOT / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport.xml"


def line(nr, ci, mi=0, mb=0, cb=0):
    return f"<line nr='{nr}' mi='{mi}' ci='{ci}' mb='{mb}' cb='{cb}'/>"


def source_file(name, lines, line_counter=(0, 0), branch_counter=None):
    missed, covered = line_counter
    counters = f"<counter type='LINE' missed='{missed}' covered='{covered}'/>"
    if branch_counter is not None:
        missed_b, covered_b = branch_counter
        counters += f"<counter type='BRANCH' missed='{missed_b}' covered='{covered_b}'/>"
    return f"<sourcefile name='{name}'>{''.join(lines)}{counters}</sourcefile>"


def parse(packages, report_counters="<counter type='LINE' missed='0' covered='0'/>"):
    xml = f"<?xml version='1.0' encoding='UTF-8'?>\n<report name='t'>{packages}{report_counters}</report>"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "jacocoTestReport.xml"
        path.write_text(xml, encoding="utf-8")
        return parse_jacoco.parse_report(path)


def package(name, *source_files):
    return f"<package name='{name}'>{''.join(source_files)}</package>"


class 구멍판별(unittest.TestCase):

    def test_실행되지_않은_줄만_미커버로_센다(self):
        result = parse(package(
            "com/pitviper/order",
            source_file("Foo.java", [line(nr=10, ci=5), line(nr=11, ci=0, mi=3), line(nr=12, ci=0, mi=1)]),
        ))
        self.assertEqual(result["gaps"][0]["uncovered_lines"], [11, 12])

    def test_줄은_실행됐지만_안_가본_분기가_있으면_부분으로_센다(self):
        result = parse(package(
            "com/pitviper/order",
            source_file("Foo.java", [line(nr=10, ci=5, mb=1, cb=1)]),
        ))
        gap = result["gaps"][0]
        self.assertEqual(gap["uncovered_lines"], [])
        self.assertEqual(gap["partial_lines"],
                         [{"line": 10, "covered_branches": 1, "missed_branches": 1}])

    def test_빈틈_없는_파일은_목록에서_빠진다(self):
        result = parse(package(
            "com/pitviper/order",
            source_file("Clean.java", [line(nr=10, ci=5), line(nr=11, ci=3, mb=0, cb=2)]),
            source_file("Dirty.java", [line(nr=10, ci=0, mi=2)]),
        ))
        self.assertEqual([g["source_file"] for g in result["gaps"]], ["Dirty.java"])
        self.assertEqual(result["summary"]["gap_files"], 1)

    def test_미커버_줄이_없어도_분기가_비면_구멍이다(self):
        """전부 실행됐는데 한쪽 분기를 안 가본 경우 — 라인 커버리지 100% 로 보이는 자리다."""
        result = parse(package(
            "com/pitviper/order",
            source_file("Foo.java", [line(nr=10, ci=5, mb=2, cb=2)]),
        ))
        self.assertEqual(result["summary"]["gap_files"], 1)
        self.assertEqual(result["summary"]["uncovered_lines"], 0)
        self.assertEqual(result["summary"]["partial_lines"], 1)


class 이름과집계(unittest.TestCase):

    def test_패키지_경로와_파일명을_FQCN으로_합친다(self):
        result = parse(package(
            "com/pitviper/order/policy",
            source_file("PointPolicy.java", [line(nr=10, ci=0, mi=1)]),
        ))
        self.assertEqual(result["gaps"][0]["class"], "com.pitviper.order.policy.PointPolicy")
        self.assertEqual(result["gaps"][0]["path"], "com/pitviper/order/policy/PointPolicy.java")

    def test_counter를_covered_missed_total_percent로_편다(self):
        result = parse(
            package("com/pitviper", source_file("Foo.java", [line(nr=10, ci=0, mi=1)], (1, 3))),
            report_counters="<counter type='LINE' missed='58' covered='59'/>"
                            "<counter type='BRANCH' missed='16' covered='28'/>",
        )
        self.assertEqual(result["summary"]["line"],
                         {"covered": 59, "missed": 58, "total": 117, "percent": 50.43})
        self.assertEqual(result["summary"]["branch"],
                         {"covered": 28, "missed": 16, "total": 44, "percent": 63.64})

    def test_분기가_없는_클래스는_BRANCH_counter가_없어도_된다(self):
        """분기 없는 클래스에 BRANCH counter 가 빠지는 것은 Jacoco 의 정상 동작이다."""
        result = parse(package("com/pitviper", source_file("Foo.java", [line(nr=10, ci=0, mi=1)])))
        self.assertEqual(result["gaps"][0]["branch"],
                         {"covered": 0, "missed": 0, "total": 0, "percent": 0.0})

    def test_구멍_목록은_클래스_이름_순이다(self):
        result = parse(package(
            "com/pitviper",
            source_file("Zulu.java", [line(nr=10, ci=0, mi=1)]),
            source_file("Alpha.java", [line(nr=10, ci=0, mi=1)]),
        ))
        self.assertEqual([g["source_file"] for g in result["gaps"]], ["Alpha.java", "Zulu.java"])


class 입력검증(unittest.TestCase):

    def test_line의_ci가_없으면_에러로_터진다(self):
        """속성 이름이 바뀌면 모든 줄이 '커버됨'으로 분류돼 구멍이 통째로 사라진다."""
        with self.assertRaises(parse_jacoco.CoverageReportError) as caught:
            parse(package("com/pitviper",
                          "<sourcefile name='Foo.java'><line nr='10' mi='1'/></sourcefile>"))
        self.assertIn("nr/mi/ci", str(caught.exception))

    def test_리포트가_없으면_돌릴_명령을_알려준다(self):
        with self.assertRaises(parse_jacoco.CoverageReportError) as caught:
            parse_jacoco.parse_report("없는경로/jacocoTestReport.xml")
        self.assertIn("jacocoTestReport", str(caught.exception))

    def test_망가진_XML은_에러로_터진다(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jacocoTestReport.xml"
            path.write_text("<report><package>", encoding="utf-8")
            with self.assertRaises(parse_jacoco.CoverageReportError):
                parse_jacoco.parse_report(path)


@unittest.skipUnless(REAL_REPORT.is_file(), f"{REAL_REPORT} 없음 — ./gradlew test 선행 필요")
class 기준선재현(unittest.TestCase):
    """CLAUDE.md 에 고정한 커버리지 기준선을 파서가 그대로 뽑아내는지 본다."""

    @classmethod
    def setUpClass(cls):
        cls.result = parse_jacoco.parse_report(REAL_REPORT)

    def test_기준선_숫자를_재현한다(self):
        summary = self.result["summary"]
        self.assertEqual(summary["line"]["covered"], 59)
        self.assertEqual(summary["line"]["total"], 117)
        self.assertEqual(summary["branch"]["covered"], 28)
        self.assertEqual(summary["branch"]["total"], 44)

    def test_미커버_줄의_합이_리포트_집계와_맞는다(self):
        """파일별로 센 것과 리포트 최상위 counter 가 어긋나면 어느 한쪽이 틀린 것이다."""
        self.assertEqual(self.result["summary"]["uncovered_lines"],
                         self.result["summary"]["line"]["missed"])

    def test_가장_큰_구멍은_GlobalExceptionHandler다(self):
        biggest = max(self.result["gaps"], key=lambda g: len(g["uncovered_lines"]))
        self.assertEqual(biggest["class"], "com.pitviper.common.exception.GlobalExceptionHandler")
        self.assertEqual(len(biggest["uncovered_lines"]), 16)


if __name__ == "__main__":
    unittest.main()
