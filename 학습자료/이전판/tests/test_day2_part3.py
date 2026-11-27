"""2일차 파트 3: 재료, 실습 노트북, checks3를 확인한다. 임베딩 모델과 API는 부르지 않는다."""
import csv
import sys
from pathlib import Path

import nbformat
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '노트북' / 'data' / '2일차'
sys.path.insert(0, str(ROOT / '노트북'))
import checks3  # noqa: E402


def rows(name):
    with open(DATA / name, encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))


def corpus_names():
    return {path.stem for path in (DATA / 'corpus').glob('*.md')}


def test_corpus_is_complete_and_matches_manifest():
    names = corpus_names()
    assert len(names) == 253
    assert {row['file'][:-3] for row in rows('corpus_manifest.csv')} == names


def test_question_sets_point_to_existing_documents():
    names = corpus_names()
    for name, count in [('검색_질문_20.csv', 20), ('검색_질문_실습.csv', 15), ('현장_질문_6.csv', 6)]:
        data = rows(name)
        assert len(data) == count
        assert all(row['정답'] in names for row in data), name
    example = {row['질문'] for row in rows('검색_질문_20.csv')}
    practice = {row['질문'] for row in rows('검색_질문_실습.csv')}
    assert not example & practice, '예제와 실습의 질문이 겹치면 안 된다'


def test_field_question_evidence_is_in_the_gold_document():
    for row in rows('현장_질문_6.csv'):
        text = (DATA / 'corpus' / f"{row['정답']}.md").read_text(encoding='utf-8')
        assert row['근거'] in text, row['질문']


def tagged_source(notebook_name, tag):
    notebook = nbformat.read(ROOT / '노트북' / notebook_name, as_version=4)
    return next(cell.source for cell in notebook.cells if tag in cell.get('metadata', {}).get('tags', []))


def test_solution_passes_practice_8_and_skeleton_fails(capsys):
    scope = {'np': np}
    exec(tagged_source('2일차_03_실습_풀이.ipynb', '실습8'), scope)
    assert checks3.check_search(scope['rank_of'], scope['recall_at'], scope['search'])
    skeleton = {'np': np}
    exec(tagged_source('2일차_03_실습.ipynb', '실습8'), skeleton)
    assert not checks3.check_search(skeleton['rank_of'], skeleton['recall_at'], skeleton['search'])
    assert '실습 8 통과' in capsys.readouterr().out


def test_judgement_check(capsys):
    field = rows('현장_질문_6.csv')
    questions = [field[1]['질문'], field[4]['질문']]
    tops = [field[1]['정답'], 'MTG-2026-W29']                  # 첫 질문은 1위가 정답, 둘째는 아님
    assert checks3.check_judgement(questions, tops, {1: 'O', 2: 'X'}, {2: 2})
    assert not checks3.check_judgement(questions, tops, {1: 'O', 2: 'O'}, {})
    assert not checks3.check_judgement(questions, tops, {1: 'O', 2: 'X'}, {})
    capsys.readouterr()


def test_notebook_code_compiles():
    for name in ['2일차_03_실습.ipynb', '2일차_03_실습_풀이.ipynb', '2일차_03_RAG의_원리와_임베딩_검색.ipynb']:
        notebook = nbformat.read(ROOT / '노트북' / name, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                compile(cell.source, name, 'exec')


def test_no_address_or_key_in_part3_files():
    for path in [ROOT / '노트북' / 'embed.py', ROOT / '노트북' / 'checks3.py', ROOT / 'tools' / 'make_nb_day2_part3.py']:
        text = path.read_text(encoding='utf-8')
        assert 'http://' not in text and 'https://' not in text, path.name
