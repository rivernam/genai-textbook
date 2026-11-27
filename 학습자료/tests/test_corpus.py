"""노트북/data의 문서 코퍼스와 평가셋(evalset.json)의 일관성을 확인한다. 검사 함수는 tools/check_corpus.py에 있다."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_corpus  # noqa: E402


@pytest.fixture(scope='module')
def manifest():
    return check_corpus.load_manifest()


@pytest.fixture(scope='module')
def evalset():
    return check_corpus.load_evalset()


def by_id(evalset, qid):
    return next(item for item in evalset if item['id'] == qid)


def test_corpus_has_no_problems(manifest):
    assert check_corpus.corpus_problems(manifest) == []


def test_evalset_has_no_problems(manifest, evalset):
    """정답 문서가 있고, 근거 문장과 핵심어가 그 문서에서 뽑은 글에 들어 있다."""
    assert check_corpus.evalset_problems(manifest, evalset) == []


def test_corpus_covers_what_the_chapters_need(manifest):
    rows = list(manifest.values())
    assert 110 <= len(rows) <= 130
    assert {row['type'] for row in rows} == check_corpus.TYPES
    assert sum(row['status'] == '폐기' for row in rows) >= 3, '8장: 같은 문서의 구판과 신판'
    assert sum(row['format'] == 'pdf' for row in rows) >= 3 and sum(row['format'] == 'html' for row in rows) >= 3
    assert len(check_corpus.POISONED) >= 3, '15장: 지시문이 숨은 문서'
    with_table = [row for row in rows if row['format'] == 'md' and '\n| --- |' in (check_corpus.CORPUS / row['file']).read_text(encoding='utf-8')]
    assert len(with_table) >= 10


def test_every_converted_document_has_a_source(manifest):
    for row in manifest.values():
        if row['format'] != 'md':
            assert (check_corpus.SOURCE / f"{row['id']}.md").exists(), row['id']


def test_evalset_size_and_types(evalset):
    assert 55 <= len(evalset) <= 70
    types = [item['type'] for item in evalset]
    assert types.count('답 없음') >= 5
    assert set(types) == check_corpus.QUESTION_TYPES


def test_old_versions_hold_a_different_value(manifest, evalset):
    """개정 질문의 근거 문장은 신판에만 있고 구판에는 없다. 구판이 검색되면 틀린 값을 답하게 된다."""
    for item in evalset:
        if item['type'] != '개정':
            continue
        old = [doc for doc in item['distractors'] if manifest[doc]['status'] == '폐기']
        assert old, item['id']
        first = check_corpus.squeeze(item['evidence'][0]['text'])
        for doc in old:
            assert first not in check_corpus.squeeze(check_corpus.document_text(doc, manifest)), (item['id'], doc)


def test_aggregate_answers_match_the_corpus(manifest, evalset):
    manuals = sorted(row['id'] for row in manifest.values()
                     if row['type'] == '설비 매뉴얼' and row['dept'] == '조립기술팀' and row['status'] == '유효')
    assert manuals == sorted(by_id(evalset, 'E45')['docs'])
    open_reports = sorted(row['id'] for row in manifest.values() if row['id'].startswith('QIR-2026')
                          and '진행상태진행중' in check_corpus.squeeze(check_corpus.document_text(row['id'], manifest)))
    assert open_reports == sorted(by_id(evalset, 'E46')['docs'])
    for qid in ('E45', 'E46'):
        assert f"{len(by_id(evalset, qid)['docs'])}건" in by_id(evalset, qid)['answer']


@pytest.mark.parametrize('qid, absent', [('E56', '구입'), ('E57', 'nm'), ('E58', '청정도 등급'), ('E61', '2027년 2월')])
def test_unanswerable_questions_have_no_answer_in_corpus(manifest, qid, absent):
    for row in manifest.values():
        assert absent not in check_corpus.document_text(row['id'], manifest), (qid, row['id'])


def test_scanned_pdf_answers_are_nowhere_else(manifest, evalset):
    """스캔 질문의 답은 스캔 PDF에만 있어야 한다. 다른 문서에 있으면 글자를 못 뽑아도 답할 수 있다."""
    for item in evalset:
        if item['type'] != '스캔':
            continue
        for row in manifest.values():
            if row['id'] in check_corpus.SCANNED:
                continue
            text = check_corpus.squeeze(check_corpus.document_text(row['id'], manifest))
            assert not all(check_corpus.squeeze(key) in text for key in item['key']), (item['id'], row['id'])


def test_no_real_addresses_or_keys(manifest):
    pattern = re.compile(r'(sk-[A-Za-z0-9]{8,}|https?://(?![\w.-]*example\.com))')
    for row in manifest.values():
        assert not pattern.search(check_corpus.extract_text(check_corpus.CORPUS / row['file'])), row['id']
