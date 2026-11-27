"""1일차 노트북 검사. API를 부르지 않고 확인할 수 있는 것만 본다."""
import re
import sys
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / '노트북'
sys.path.insert(0, str(NOTEBOOKS))
import checks_d1  # noqa: E402

LEARNING = '1일차_01_LLM의_원리와_한계.ipynb'       # build.py가 원고에서 만든다
PRACTICE, SOLUTION = '1일차_실습.ipynb', '1일차_실습_풀이.ipynb'


def code_cells(name):
    return [cell for cell in nbformat.read(NOTEBOOKS / name, as_version=4).cells if cell.cell_type == 'code']


def tagged_source(name, tag):
    return next(cell.source for cell in code_cells(name) if cell.metadata.get('tags') == [tag])


@pytest.mark.parametrize('name', [LEARNING, PRACTICE, SOLUTION])
def test_valid_and_compiles(name):
    nbformat.validate(nbformat.read(NOTEBOOKS / name, as_version=4))
    for cell in code_cells(name):
        compile(cell.source, name, 'exec')
        if name != LEARNING:
            assert not cell.outputs, '실습 노트북은 출력을 비워 둔다'


def test_learning_notebook_examples_are_in_order_and_use_day1_setup():
    cells = code_cells(LEARNING)
    numbers = [int(match.group(1)) for cell in cells if (match := re.match(r'# 예제 1-(\d+)', cell.source))]
    assert numbers == sorted(numbers) and sorted(set(numbers)) == list(range(1, 8))
    setup = cells[1].source
    assert "DATA = 'data/1일차'" in setup and 'def read_material' in setup
    assert 'cost_usd' not in setup                    # 2일차의 준비 코드가 섞이지 않는다


def test_materials_exist_and_are_marked_fictional():
    data = NOTEBOOKS / 'data' / '1일차'
    for name in ['회의록_8월1주차.txt', '현장코멘트_8건.txt', '기사_가상.txt', '질문카드.txt']:
        assert (data / name).read_text(encoding='utf-8').strip()
    assert '가상 기사' in (data / '기사_가상.txt').read_text(encoding='utf-8')
    cards = (data / '질문카드.txt').read_text(encoding='utf-8')
    assert re.findall(r'^\[(.+)\]$', cards, flags=re.M) == list(checks_d1.KINDS)


def test_only_practice_has_blanks():
    practice = '\n'.join(cell.source for cell in code_cells(PRACTICE))
    solution = '\n'.join(cell.source for cell in code_cells(SOLUTION))
    assert practice.count('NotImplementedError') == 1          # cumulative_yield
    assert 'NotImplementedError' not in solution


def test_solution_passes_and_blank_table_fails(capsys):
    namespace = {}
    exec(tagged_source(SOLUTION, '실습1'), namespace)
    exec(tagged_source(SOLUTION, '실습1표'), namespace)
    results = checks_d1.check_table(namespace['table'], namespace['correct_yield'])
    assert all(ok for ok, _ in results) and '실습 1 통과' in capsys.readouterr().out

    exec(tagged_source(PRACTICE, '실습1표'), namespace)
    blank = checks_d1.check_table(namespace['table'], namespace['correct_yield'])
    assert not all(ok for ok, _ in blank) and '실습 1 통과' not in capsys.readouterr().out


def test_check_table_rejects_wrong_yield_and_wrong_criteria():
    namespace = {}
    exec(tagged_source(SOLUTION, '실습1표'), namespace)
    table = namespace['table']
    assert not checks_d1.check_table(table, 91.87)[0][0]
    table['계산']['기준'] = '검증하고 쓴다'
    assert not checks_d1.check_table(table, 91.84)[5][0]
    assert not all(ok for ok, _ in checks_d1.check_table({}, 91.84))
