"""3일차 파트 1: 재료, 실습 노트북, checks_d3를 확인한다. 임베딩 모델과 API는 부르지 않는다."""
import csv
import json
import os
import sys
from pathlib import Path

import nbformat
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / '노트북'
DATA = NOTEBOOKS / 'data' / '3일차'
sys.path.insert(0, str(NOTEBOOKS))
sys.path.insert(0, str(ROOT / 'tools'))
import checks_d3  # noqa: E402
import make_nb_day3_part1  # noqa: E402


def rows(name):
    with open(DATA / name, encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))


def corpus_names():
    return {path.stem for path in (NOTEBOOKS / 'data' / '2일차' / 'corpus').glob('*.md')}


def tagged_source(notebook_name, tag):
    notebook = nbformat.read(NOTEBOOKS / notebook_name, as_version=4)
    return next(cell.source for cell in notebook.cells if tag in cell.get('metadata', {}).get('tags', []))


def test_change_files_match_the_change_list():
    changes = rows('변경_목록.csv')
    assert len(changes) == 9
    changed_files = {path.stem for path in (DATA / '변경_문서').glob('*.md')}
    assert changed_files == {row['문서'] for row in changes if row['종류'] in ('개정', '신규')}
    existing = corpus_names()
    assert all(row['문서'] in existing for row in changes if row['종류'] in ('개정', '폐기'))
    assert all(row['문서'] not in existing for row in changes if row['종류'] == '신규')


def test_questions_point_to_documents_after_the_change():
    after = (corpus_names() | {row['문서'] for row in rows('변경_목록.csv') if row['종류'] == '신규'}) - {
        row['문서'] for row in rows('변경_목록.csv') if row['종류'] == '폐기'}
    questions = rows('변경_질문_6.csv')
    assert len(questions) == 6
    golds = [row['정답'] for row in questions]
    assert golds[-1] == '' and all(gold in after for gold in golds[:-1])


def test_solution_passes_practice_1_and_skeleton_fails(capsys):
    scope = {'np': np, 'os': os, 'json': json}
    exec(make_nb_day3_part1.vector_index_source(), scope)
    exec(tagged_source('3일차_실습_풀이.ipynb', '실습1'), scope)
    assert checks_d3.check_apply_changes(scope['apply_changes'], scope['VectorIndex'])
    skeleton = {'np': np, 'os': os, 'json': json}
    exec(make_nb_day3_part1.vector_index_source(), skeleton)
    exec(tagged_source('3일차_실습.ipynb', '실습1'), skeleton)
    assert not checks_d3.check_apply_changes(skeleton['apply_changes'], skeleton['VectorIndex'])
    assert '실습 1 통과' in capsys.readouterr().out


def test_half_applied_solution_fails_the_check(capsys):
    """검사 없이 한 건씩 반영하는 풀이는 테스트에서 걸러져야 한다."""
    scope = {'np': np, 'os': os, 'json': json}
    exec(make_nb_day3_part1.vector_index_source(), scope)
    exec('''
def apply_changes(index, revised, added, retired, folder, embed_text):
    for name in revised:
        doc = open(f'{folder}/{name}.md', encoding='utf-8').read()
        index.replace(name, doc, embed_text(doc))
    for name in added:
        doc = open(f'{folder}/{name}.md', encoding='utf-8').read()
        index.add(name, doc, embed_text(doc))
    for name in retired:
        index.remove(name)
    return {'교체': len(revised), '추가': len(added), '삭제': len(retired), '행 수': len(index)}
''', scope)
    assert not checks_d3.check_apply_changes(scope['apply_changes'], scope['VectorIndex'])
    capsys.readouterr()


def test_vector_index_keeps_everything_in_step():
    scope = {'np': np, 'json': json}
    exec(make_nb_day3_part1.vector_index_source(), scope)
    VectorIndex = scope['VectorIndex']
    index = VectorIndex(['a', 'b', 'c'], ['A', 'B', 'C'], np.eye(3), 'fake')
    index.remove('b')
    assert index.names == ['a', 'c'] and index.docs == ['A', 'C'] and index.vectors.shape == (2, 3)
    index.add('d', 'D', np.array([0.0, 0.0, 1.0]))
    assert index.search(np.array([0.0, 0.0, 1.0]), 2) == [('c', 1.0), ('d', 1.0)]
    assert index.rank_of(np.array([0.0, 0.0, 1.0]), 'a') == 3
    try:
        VectorIndex(['a'], ['A', 'B'], np.eye(2), 'fake')
    except ValueError:
        pass
    else:
        raise AssertionError('개수가 다르면 ValueError 를 내야 한다')


def test_notebook_code_compiles():
    for name in ['3일차_실습.ipynb', '3일차_실습_풀이.ipynb', '3일차_01_벡터_DB와_RAG의_구조.ipynb']:
        notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                compile(cell.source, name, 'exec')
                if '실습' in name:
                    assert not cell.outputs, '실습 노트북은 출력을 비워 둔다'


def test_practice_notebook_has_the_blank_and_solution_does_not():
    assert 'NotImplementedError' in tagged_source('3일차_실습.ipynb', '실습1')
    assert 'NotImplementedError' not in tagged_source('3일차_실습_풀이.ipynb', '실습1')


def test_class_code_is_the_manuscript_code():
    source = make_nb_day3_part1.vector_index_source()
    for name in ['3일차_실습.ipynb', '3일차_실습_풀이.ipynb']:
        assert source in tagged_source(name, '실습준비')


def test_no_address_or_key_in_part1_files():
    for path in [NOTEBOOKS / 'checks_d3.py', ROOT / 'tools' / 'make_nb_day3_part1.py', ROOT / 'tools' / 'make_data_day3.py']:
        text = path.read_text(encoding='utf-8')
        assert 'http://' not in text and 'https://' not in text, path.name
