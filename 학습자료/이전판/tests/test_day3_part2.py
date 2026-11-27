"""3일차 파트 2: 재료, 실습 노트북, checks_d3_2를 확인한다. 임베딩 모델과 API는 부르지 않는다."""
import csv
import sys
import zipfile
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / '노트북'
DATA3 = NOTEBOOKS / 'data' / '3일차'
sys.path.insert(0, str(NOTEBOOKS))
import checks_d3_2  # noqa: E402


def files(folder, suffix):
    return sorted(path for path in (DATA3 / folder).rglob(f'*{suffix}'))


def rows(name):
    with open(DATA3 / name, encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))


def test_raw_documents_are_complete():
    assert len(files('docs_raw/pdf', '.pdf')) == 8
    assert len(files('docs_raw/docx', '.docx')) == 10
    assert len(files('docs_raw/xlsx', '.xlsx')) == 2
    assert len(files('docs_raw_m2/pdf', '.pdf')) == 4
    assert len(files('docs_raw_m2/docx', '.docx')) == 4
    assert len(files('docs_raw_m2/xlsx', '.xlsx')) == 1
    assert len(files('docs_raw_m2/md', '.md')) == 1


def test_broken_files_do_not_open():
    pdf = DATA3 / 'docs_raw_m2_ext' / 'NOTI-032.pdf'
    docx = DATA3 / 'docs_raw_m2_ext' / 'EHS-022.docx'
    assert pdf.stat().st_size == 0
    assert not zipfile.is_zipfile(docx)


def test_working_files_open():
    from docx import Document
    from pypdf import PdfReader

    for path in files('docs_raw_m2', '.pdf'):
        assert PdfReader(path).pages
    for path in files('docs_raw_m2', '.docx'):
        assert Document(path).paragraphs


def test_question_sets_point_to_existing_documents():
    corpus = {path.stem for path in (NOTEBOOKS / 'data' / '2일차' / 'corpus').glob('*.md')}
    chunk_questions = rows('청크_질문_10.csv')
    assert len(chunk_questions) == 10 and all(row['정답'] in corpus for row in chunk_questions)
    stems = {path.stem for path in files('docs_raw_m2', '')}
    mission = rows('실습2_질문_5.csv')
    assert len(mission) == 5 and all(row['정답'] in stems for row in mission)


def test_first_five_chunk_questions_match_day2_questions():
    day2 = list(csv.DictReader(open(NOTEBOOKS / 'data' / '2일차' / '검색_질문_20.csv', encoding='utf-8-sig')))
    assert [row['질문'] for row in day2[:5]] == [row['질문'] for row in rows('청크_질문_10.csv')[:5]]


def tagged_source(name, tag):
    notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
    return next(cell.source for cell in notebook.cells if tag in cell.get('metadata', {}).get('tags', []))


def cell_with(name, text):
    notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
    return next(cell.source for cell in notebook.cells if cell.cell_type == 'code' and text in cell.source)


def solution_scope():
    scope = {'DATA': str(DATA3)}
    exec(tagged_source('3일차_02_실습_풀이.ipynb', '실습준비'), scope)
    exec(cell_with('3일차_02_실습_풀이.ipynb', 'NOISE_WORDS = ['), scope)
    exec(tagged_source('3일차_02_실습_풀이.ipynb', '실습2'), scope)
    return scope


def test_solution_passes_practice_2(capsys):
    scope = solution_scope()
    assert checks_d3_2.check_pipeline(scope['find_header_row'], scope['read_xlsx'], scope['drop_noise'],
                                      scope['process'])
    assert '실습 2 통과' in capsys.readouterr().out


def test_skeleton_fails_practice_2(capsys):
    scope = {'DATA': str(DATA3)}
    exec(tagged_source('3일차_02_실습.ipynb', '실습준비'), scope)
    exec(tagged_source('3일차_02_실습.ipynb', '실습2'), scope)
    assert not checks_d3_2.check_pipeline(scope['find_header_row'], scope['read_xlsx'], scope['drop_noise'],
                                          scope['process'])
    assert '실습 2 통과' not in capsys.readouterr().out


def test_solution_processes_the_real_material():
    scope = solution_scope()
    chunks, report = scope['process'](scope['RAW2'], scope['NOISE_WORDS'], 400)
    assert report['열린 파일'] == 10 and report['실패'] == []
    assert all(len(chunk['text']) <= 400 for chunk in chunks)
    assert not any('기 밀' in chunk['text'] or '무단 반출' in chunk['text'] for chunk in chunks)
    assert any('E-102' in chunk['text'] for chunk in chunks if chunk['doc_id'] == '설비알람_코드표')
    _, ext_report = scope['process'](scope['EXT2'], scope['NOISE_WORDS'], 400)
    assert ext_report['열린 파일'] == 0
    assert sorted(name for name, _ in ext_report['실패']) == ['EHS-022.docx', 'NOTI-032.pdf']


def test_find_header_row_on_real_spreadsheets():
    scope = solution_scope()
    from openpyxl import load_workbook

    expected = {DATA3 / 'docs_raw' / 'xlsx' / '공정스펙_관리한계_일람.xlsx': 3,
                DATA3 / 'docs_raw' / 'xlsx' / '장비마스터.xlsx': 0,
                DATA3 / 'docs_raw_m2' / 'xlsx' / '설비알람_코드표.xlsx': 4}
    for path, position in expected.items():
        sheet_rows = list(load_workbook(path).active.iter_rows(values_only=True))
        assert scope['find_header_row'](sheet_rows) == position, path.name


@pytest.mark.parametrize('name', ['3일차_02_실습.ipynb', '3일차_02_실습_풀이.ipynb'])
def test_notebook_is_valid_and_has_no_outputs(name):
    notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            compile(cell.source, name, 'exec')
            assert not cell.outputs


def test_only_practice_has_blanks():
    practice = '\n'.join(cell.source for cell in nbformat.read(NOTEBOOKS / '3일차_02_실습.ipynb', as_version=4).cells
                         if cell.cell_type == 'code')
    solution = '\n'.join(cell.source for cell in nbformat.read(NOTEBOOKS / '3일차_02_실습_풀이.ipynb', as_version=4).cells
                         if cell.cell_type == 'code')
    assert practice.count('NotImplementedError') == 4
    assert 'NotImplementedError' not in solution


def test_learning_notebook_code_compiles():
    notebook = nbformat.read(NOTEBOOKS / '3일차_02_문서_처리_파이프라인.ipynb', as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            compile(cell.source, '3일차_02', 'exec')


def test_no_address_or_key_in_part2_files():
    for path in [NOTEBOOKS / 'checks_d3_2.py', ROOT / 'tools' / 'make_nb_day3_part2.py',
                 ROOT / 'tools' / 'make_data_day3_part2.py']:
        text = path.read_text(encoding='utf-8')
        assert 'http://' not in text and 'https://' not in text, path.name
