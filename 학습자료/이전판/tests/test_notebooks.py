"""2일차 노트북 검사. API를 부르지 않고 확인할 수 있는 것만 본다."""
import json
import re
import sys
import time
from pathlib import Path

import nbformat
import pytest

NOTEBOOKS = Path(__file__).resolve().parents[1] / '노트북'
sys.path.insert(0, str(NOTEBOOKS))
import llm  # noqa: E402

LEARNING = '2일차_01_LLM_API_기초.ipynb'       # build.py가 원고에서 만든다
LEARNING2 = '2일차_02_구조화_출력과_시스템_연동.ipynb'
PART2 = ['2일차_02_실습.ipynb', '2일차_02_실습_풀이.ipynb']
NAMES = [LEARNING, LEARNING2, '2일차_실습.ipynb', '2일차_실습_풀이.ipynb'] + PART2


def read(name):
    return nbformat.read(NOTEBOOKS / name, as_version=4)


def code_cells(name):
    return [cell for cell in read(name).cells if cell.cell_type == 'code']


@pytest.mark.parametrize('name', NAMES)
def test_valid_and_compiles(name):
    notebook = read(name)
    nbformat.validate(notebook)
    for cell in code_cells(name):
        compile(cell.source, name, 'exec')
        if name not in (LEARNING, LEARNING2):      # 학습 노트북에는 읽기만 해도 되도록 실행 결과를 넣어 둔다
            assert not cell.outputs, '실습 노트북은 출력을 비워 둔다'


def test_example_markers_cover_1_to_12_in_order():
    numbers = [int(match.group(1)) for cell in code_cells(LEARNING)
               if (match := re.match(r'# 예제 1-(\d+)', cell.source))]
    assert numbers == sorted(numbers)
    assert sorted(set(numbers)) == list(range(1, 13))


@pytest.mark.parametrize('name', ['2일차_실습.ipynb', '2일차_실습_풀이.ipynb'])
def test_practice_markers(name):
    numbers = [int(match.group(1)) for cell in code_cells(name)
               if (match := re.match(r'# 실습 (\d+)', cell.source))]
    assert numbers == sorted(numbers)
    assert sorted(set(numbers)) == [1, 2, 3, 4]


def test_only_practice_has_blanks():
    practice = '\n'.join(cell.source for cell in code_cells('2일차_실습.ipynb'))
    solution = '\n'.join(cell.source for cell in code_cells('2일차_실습_풀이.ipynb'))
    assert practice.count('NotImplementedError') == 7     # chat, 추정, 비교, 실습 3의 네 함수
    assert 'NotImplementedError' not in solution


def no_secrets(name):
    text = (NOTEBOOKS / name).read_text(encoding='utf-8')
    assert not re.search(r'sk-ant-|https?://(?!localhost)', text)


@pytest.mark.parametrize('name', NAMES)
def test_no_keys_or_addresses(name):
    no_secrets(name)


def run_tagged(name, tag, capsys):
    """tag가 붙은 셀과 바로 다음 테스트 셀을 실행하고 출력과 이름 공간을 돌려준다."""
    cells = code_cells(name)
    index = next(i for i, cell in enumerate(cells) if tag in cell.metadata.get('tags', []))
    namespace = {'llm': llm, 'json': json, 'time': time, 'SYSTEM': '규칙'}
    exec(cells[index].source, namespace)
    exec(cells[index + 1].source, namespace)
    return capsys.readouterr().out


def test_solution_passes_practice_1_check(capsys):
    assert '실습 1 통과' in run_tagged('2일차_실습_풀이.ipynb', '실습1', capsys)


def test_solution_passes_practice_3_check(capsys):
    output = run_tagged('2일차_실습_풀이.ipynb', '실습3', capsys)
    assert '결과 10/10 통과' in output and '입력 검사 통과' in output


def test_blank_practice_fails_checks_without_crashing_checker(capsys):
    cells = code_cells('2일차_실습.ipynb')
    index = next(i for i, cell in enumerate(cells) if '실습3' in cell.metadata.get('tags', []))
    namespace = {'llm': llm, 'json': json, 'time': time, 'SYSTEM': '규칙'}
    exec(cells[index].source, namespace)
    with pytest.raises(NotImplementedError):      # 테스트 셀의 is_valid 단언에서 멈춘다
        exec(cells[index + 1].source, namespace)
    assert '결과 0/10 통과' in capsys.readouterr().out


# ---- 파트 2 ----

def test_part2_example_markers_cover_1_to_11_in_order():
    numbers = [int(match.group(1)) for cell in code_cells(LEARNING2)
               if (match := re.match(r'# 예제 2-(\d+)', cell.source))]
    assert numbers == sorted(numbers)
    assert sorted(set(numbers)) == list(range(1, 12))


@pytest.mark.parametrize('name', PART2)
def test_part2_practice_markers(name):
    numbers = [int(match.group(1)) for cell in code_cells(name)
               if (match := re.match(r'# 실습 (\d+)', cell.source))]
    assert numbers == sorted(numbers)
    assert sorted(set(numbers)) == [5, 6, 7]


def test_part2_only_practice_has_blanks():
    practice = '\n'.join(cell.source for cell in code_cells(PART2[0]))
    solution = '\n'.join(cell.source for cell in code_cells(PART2[1]))
    assert practice.count('NotImplementedError') == 6     # Ticket, classify, save, run, validate, status_of
    assert 'NotImplementedError' not in solution


def part2_namespace(monkeypatch):
    """노트북의 준비 셀이 만들어 주는 이름들. 재료를 읽으므로 노트북 폴더에서 실행한다."""
    import os
    from concurrent.futures import ThreadPoolExecutor

    import pandas as pd
    monkeypatch.chdir(NOTEBOOKS)
    return {'llm': llm, 'json': json, 'time': time, 'os': os, 'pd': pd, 'DATA': 'data/2일차',
            'ThreadPoolExecutor': ThreadPoolExecutor}


def tagged(cells, tag):
    return next(index for index, cell in enumerate(cells) if tag in cell.metadata.get('tags', []))


def test_part2_solution_passes_all_checks(monkeypatch, capsys):
    cells = code_cells(PART2[1])
    namespace = part2_namespace(monkeypatch)
    exec(cells[tagged(cells, '실습준비')].source, namespace)
    for tag in ['실습5', '실습6', '실습7']:
        index = tagged(cells, tag)
        exec(cells[index].source, namespace)
        exec(cells[index + 1].source, namespace)          # 바로 다음이 테스트 셀이다
    output = capsys.readouterr().out
    assert '실습 5 통과' in output and '실습 6 통과' in output and '실습 7 통과' in output


def test_part2_blank_practice_stops_at_first_blank(monkeypatch):
    cells = code_cells(PART2[0])
    namespace = part2_namespace(monkeypatch)
    exec(cells[tagged(cells, '실습준비')].source, namespace)
    with pytest.raises(NotImplementedError):
        exec(cells[tagged(cells, '실습5')].source, namespace)


def test_part2_checks_fail_wrong_answers_without_crashing(monkeypatch, capsys):
    """틀린 풀이를 넣어도 검사는 끝까지 가고 통과로 판정하지 않는다."""
    import checks2
    cells = code_cells(PART2[1])
    namespace = part2_namespace(monkeypatch)
    for tag in ['실습준비', '실습5', '실습6', '실습7']:
        exec(cells[tagged(cells, tag)].source, namespace)
    capsys.readouterr()

    def broken(*args, **kwargs):
        raise KeyError('틀린 코드')

    assert not checks2.check_batch(broken, broken, broken, namespace['open_db'])
    assert '실습 6: 0/8 통과' in capsys.readouterr().out
    assert not checks2.check_validate(lambda record, text: None, lambda record, text: 'auto')
    assert '실습 7: 2/6 통과' in capsys.readouterr().out

    # INSERT OR REPLACE로 저장하면 사람이 적은 값이 지워져 마지막 검사에서 걸린다
    replace_sql = ('INSERT OR REPLACE INTO requests (id, team, location, urgent, model, run_at) '
                   'VALUES (?, ?, ?, ?, ?, ?)')

    def save_with_replace(db, records, model, run_at):
        rows = [(record['id'], record['team'], record['location'], int(record['urgent']), model, run_at)
                for record in records if not record['error']]
        db.executemany(replace_sql, rows)
        db.commit()
        return len(rows)

    namespace['save'] = save_with_replace
    assert not checks2.check_batch(namespace['classify'], save_with_replace, namespace['run'],
                                   namespace['open_db'])
    assert '실습 6: 7/8 통과' in capsys.readouterr().out
