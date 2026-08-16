"""테스트가 공유하는 mutations.xml 조각 생성기.

파일명이 `test` 로 시작하지 않아 `unittest discover` 가 테스트로 수집하지 않는다.
"""

from pathlib import Path

MUTATOR_PREFIX = "org.pitest.mutationtest.engine.gregor.mutators"
NEGATE = f"{MUTATOR_PREFIX}.NegateConditionalsMutator"


def mutation(status, cls="com.pitviper.Foo", method="bar", line=10,
             mutator=NEGATE, indexes=(5,), description="negated conditional", tests_run=1):
    index_xml = "".join(f"<index>{i}</index>" for i in indexes)
    return (
        f"<mutation detected='false' status='{status}' numberOfTestsRun='{tests_run}'>"
        f"<sourceFile>Foo.java</sourceFile>"
        f"<mutatedClass>{cls}</mutatedClass>"
        f"<mutatedMethod>{method}</mutatedMethod>"
        f"<lineNumber>{line}</lineNumber>"
        f"<mutator>{mutator}</mutator>"
        f"<indexes>{index_xml}</indexes>"
        f"<description>{description}</description>"
        f"</mutation>"
    )


def mutations_xml(*mutations):
    return "<?xml version='1.0' encoding='UTF-8'?>\n<mutations>" + "".join(mutations) + "</mutations>"


def write_report(directory, name, *mutations):
    """임시 디렉터리에 mutations.xml 을 쓰고 경로를 돌려준다."""
    path = Path(directory) / name
    path.write_text(mutations_xml(*mutations), encoding="utf-8")
    return path


def mutant_id(cls="com.pitviper.Foo", method="bar", line=10, mutator="NegateConditionals", indexes=(5,)):
    """테스트가 기대하는 안정 id 를 손으로 조립한다 (스크립트와 독립적으로)."""
    return f"{cls}#{method}:{line}:{mutator}:{'-'.join(str(i) for i in indexes)}"
