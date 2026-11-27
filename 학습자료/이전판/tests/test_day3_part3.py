"""3일차 파트 3: 재료, 실습 노트북, checks_d3_3를 확인한다. 임베딩 모델과 API는 부르지 않는다."""
import csv
import sys
from pathlib import Path

import nbformat
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / '노트북'
DATA = NOTEBOOKS / 'data' / '3일차'
sys.path.insert(0, str(NOTEBOOKS))
sys.path.insert(0, str(ROOT / 'tools'))
import checks_d3_3  # noqa: E402
import make_nb_day3_part3  # noqa: E402


def rows(path):
    with open(path, encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))


def tagged_source(notebook_name, tag):
    notebook = nbformat.read(NOTEBOOKS / notebook_name, as_version=4)
    return next(cell.source for cell in notebook.cells if tag in cell.get('metadata', {}).get('tags', []))


def test_new_corpus_matches_its_manifest():
    manifest = rows(DATA / 'corpus_m3_manifest.csv')
    files = {path.name for path in (DATA / 'corpus_m3').glob('*.md')} | {path.name for path in (DATA / 'corpus_m3_구판').glob('*.md')}
    assert len(manifest) == 13 and {row['file'] for row in manifest} == files
    assert len(list((DATA / 'corpus_m3').glob('*.md'))) == 12 and len(list((DATA / 'corpus_m3_구판').glob('*.md'))) == 1
    old = [row for row in manifest if row['doc_id'] == 'SOP-DIFF-002']
    assert sorted(row['version'] for row in old) == ['v1.0', 'v2.0']


def test_question_files():
    diagnosis = rows(DATA / '진단_질문_6.csv')
    assert len(diagnosis) == 6 and all(int(row['k']) in (4, 6) for row in diagnosis)
    assert len(rows(DATA / '실습_질문_5.csv')) == 5


def parts_scope():
    scope = {'np': np, 'os': __import__('os'), 'embed': None}
    exec(make_nb_day3_part3.parts_source(), scope)
    return scope


def test_chunking_matches_the_original_counts():
    """원본의 청크 수(문서 253건 → 757청크, 새 문서 12건 → 39청크)와 같다. 임베딩 모델은 부르지 않는다."""
    scope = parts_scope()
    manifest = scope['read_manifest'](ROOT / '노트북' / 'data' / '2일차' / 'corpus_manifest.csv')
    assert len(scope['build_chunks'](ROOT / '노트북' / 'data' / '2일차' / 'corpus', manifest)) == 757
    manifest_m3 = scope['read_manifest'](DATA / 'corpus_m3_manifest.csv')
    assert len(scope['build_chunks'](DATA / 'corpus_m3', manifest_m3)) == 39


def test_search_excludes_types_and_orders_by_score():
    scope = parts_scope()
    Chunk, ChunkIndex = scope['Chunk'], scope['ChunkIndex']
    chunks = [Chunk('A', 'v1.0', 'SOP', 'd', '절', 'a'), Chunk('B', 'v1.0', '회의록', 'd', '절', 'b'),
              Chunk('C', 'v1.0', 'SOP', 'd', '절', 'c')]

    class FakeEmbed:
        @staticmethod
        def query(question):
            return np.array([1.0, 0.0])

    scope['embed'] = FakeEmbed
    index = ChunkIndex(chunks, np.array([[0.2, 0.9], [1.0, 0.0], [0.6, 0.8]]))
    assert [hit.doc_id for hit in scope['search'](index, '질문', 3)] == ['B', 'C', 'A']
    assert [hit.doc_id for hit in scope['search'](index, '질문', 3, exclude_types=['회의록'])] == ['C', 'A']


def test_solution_passes_practice_3_and_skeleton_fails(capsys):
    rule = "검색 결과에 없으면 '사내 문서에서 근거를 찾지 못했습니다' 라고만 답한다."
    scope = {'RULE': rule}
    exec(tagged_source('3일차_03_실습_풀이.ipynb', '실습3'), scope)
    assert checks_d3_3.check_practice_3(scope['build_prompt'], scope['latest_version_rows'], rule)
    skeleton = {'RULE': rule}
    exec(tagged_source('3일차_03_실습.ipynb', '실습3'), skeleton)
    assert not checks_d3_3.check_practice_3(skeleton['build_prompt'], skeleton['latest_version_rows'], rule)
    assert '실습 3 통과' in capsys.readouterr().out


def test_solution_rule_text_is_the_rule_in_the_practice_cell():
    rule_line = next(line for line in tagged_source('3일차_03_실습_풀이.ipynb', '실습준비').splitlines()
                     if line.startswith('RULE = '))
    assert '근거를 찾지 못했습니다' in rule_line


def test_string_comparison_of_versions_fails_the_check(capsys):
    """버전을 문자열로 비교하는 풀이는 v1.10과 v1.9의 테스트에서 실패해야 한다. 다른 항목은 모두 통과하는 풀이로 확인한다."""
    rule = "검색 결과에 없으면 '사내 문서에서 근거를 찾지 못했습니다' 라고만 답한다."
    scope = {'RULE': rule}
    exec('''
def build_prompt(hits, question, use_rule=True):
    results = '\\n\\n'.join(f'[{hit.doc_id}_{hit.version}] ({hit.section})\\n{hit.text}' for hit in hits)
    return ('너는 사내 문서를 근거로 답하는 도우미다.\\n\\n' + f'[검색 결과]\\n{results}\\n\\n'
            + '규칙: 문장마다 근거 [문서번호]를 붙인다.\\n' + (RULE + '\\n\\n' if use_rule else '\\n') + f'질문: {question}')


def latest_version_rows(chunks):
    latest = {}
    for chunk in chunks:
        latest[chunk.doc_id] = max(latest.get(chunk.doc_id, ''), chunk.version)
    return [row for row, chunk in enumerate(chunks) if chunk.version == latest[chunk.doc_id]]
''', scope)
    assert not checks_d3_3.check_practice_3(scope['build_prompt'], scope['latest_version_rows'], rule)
    failed = [line for line in capsys.readouterr().out.splitlines() if '실패 ' in line and line[0].isdigit()]
    assert failed and all('latest_version_rows' in line for line in failed), failed


def test_notebook_code_compiles():
    for name in ['3일차_03_실습.ipynb', '3일차_03_실습_풀이.ipynb', '3일차_03_첫_RAG_완성.ipynb']:
        notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                compile(cell.source, name, 'exec')
                if '실습' in name:
                    assert not cell.outputs, '실습 노트북은 출력을 비워 둔다'


def test_practice_notebook_has_the_blanks_and_solution_does_not():
    assert tagged_source('3일차_03_실습.ipynb', '실습3').count('NotImplementedError') == 2
    assert 'NotImplementedError' not in tagged_source('3일차_03_실습_풀이.ipynb', '실습3')


def test_parts_are_the_manuscript_code():
    source = make_nb_day3_part3.parts_source()
    for name in ['3일차_03_실습.ipynb', '3일차_03_실습_풀이.ipynb']:
        assert source in tagged_source(name, '실습준비')


def test_no_address_or_key_in_part3_files():
    for path in [NOTEBOOKS / 'checks_d3_3.py', ROOT / 'tools' / 'make_nb_day3_part3.py', ROOT / 'tools' / 'make_data_day3_part3.py']:
        text = path.read_text(encoding='utf-8')
        assert 'http://' not in text and 'https://' not in text, path.name
