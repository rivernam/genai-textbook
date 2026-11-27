"""1일차 파트 2 노트북 검사. API를 부르지 않고 확인할 수 있는 것만 본다."""
import re
import sys
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / '노트북'
sys.path.insert(0, str(NOTEBOOKS))
import checks_d1_2  # noqa: E402

LEARNING = '1일차_02_프롬프트_설계.ipynb'          # build.py가 원고에서 만든다
PRACTICE, SOLUTION = '1일차_02_실습.ipynb', '1일차_02_실습_풀이.ipynb'

PERFECT = '\n'.join(f'{number} | {label}' for number, label in checks_d1_2.load_answer().items())
PERFECT_TABLE = '\n'.join(
    ['| 로그 번호 | 설비 | 알람 | 발생 시각 |', '| --- | --- | --- | --- |']
    + [f'| {number} | 설비 | 알람 | 시각 |' for number, label in checks_d1_2.load_answer().items() if label == '조치 필요'])


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
    numbers = [int(match.group(1)) for cell in cells if (match := re.match(r'# 예제 2-(\d+)', cell.source))]
    assert numbers == sorted(numbers) and sorted(set(numbers)) == list(range(1, 10))
    assert "DATA = 'data/1일차'" in cells[1].source and 'def read_material' in cells[1].source


def test_only_practice_has_blanks():
    practice = '\n'.join(cell.source for cell in code_cells(PRACTICE))
    solution = '\n'.join(cell.source for cell in code_cells(SOLUTION))
    assert practice.count('NotImplementedError') == 2          # build_classify_prompt, count_table_rows
    assert "STEP2_PROMPT = ''" in practice
    assert 'NotImplementedError' not in solution


def run_solution_prompts():
    """풀이의 프롬프트 함수를 실행해 문자열을 얻는다(API를 부르지 않는다)."""
    namespace = {}
    exec(tagged_source(SOLUTION, '실습2'), namespace)
    exec(tagged_source(SOLUTION, '실습3표'), namespace)
    exec(tagged_source(SOLUTION, '실습3프롬프트'), namespace)
    return namespace


def test_solution_prompt_contains_rule_log_and_format(capsys):
    namespace = run_solution_prompts()
    data = NOTEBOOKS / 'data' / '1일차'
    log = (data / '알람로그_10건.txt').read_text(encoding='utf-8')
    rule = (data / '알람_분류기준.txt').read_text(encoding='utf-8')
    prompt = namespace['build_classify_prompt'](log, rule)
    assert rule in prompt and log in prompt and '번호 | 분류' in prompt
    assert namespace['MERGE_BAN'] in namespace['STEP2_PROMPT']


def test_check_classify_accepts_perfect_and_rejects_bad(capsys):
    assert all(ok for ok, _ in checks_d1_2.check_classify([PERFECT] * 3))
    assert '실습 2 통과' in capsys.readouterr().out
    assert not checks_d1_2.check_classify([PERFECT] * 2)[0][0]                       # 세 번이 아님
    assert not checks_d1_2.check_classify(['분류 결과입니다\n' + PERFECT] * 3)[1][0]   # 형식 외의 말
    flipped = PERFECT.replace('1 | 조치 필요', '1 | 모니터링')
    assert not checks_d1_2.check_classify([PERFECT, PERFECT, flipped])[2][0]          # 세 번이 같지 않음
    many_wrong = PERFECT.replace('조치 필요', '모니터링')
    assert not checks_d1_2.check_classify([many_wrong] * 3)[3][0]                     # 정답과 7건 다름
    assert not all(ok for ok, _ in checks_d1_2.check_classify(None))


def test_count_table_rows_solution_and_check_chain(capsys):
    namespace = run_solution_prompts()
    count_rows = namespace['count_table_rows']
    assert count_rows(checks_d1_2.SAMPLE_TABLE) == 3 and count_rows('표가 없습니다') == 0
    assert all(ok for ok, _ in checks_d1_2.check_chain(PERFECT_TABLE, count_rows, PERFECT))
    assert '실습 3 통과' in capsys.readouterr().out
    merged = '\n'.join(line for line in PERFECT_TABLE.splitlines() if not line.startswith('| 4 |'))
    results = checks_d1_2.check_chain(merged, count_rows, PERFECT)                    # 같은 설비의 두 줄을 합친 표
    assert not results[1][0] and not results[2][0]


def test_blank_count_function_fails_the_check():
    namespace = {}
    exec(tagged_source(PRACTICE, '실습3표'), namespace)
    results = checks_d1_2.check_chain(PERFECT_TABLE, namespace['count_table_rows'], PERFECT)
    assert not all(ok for ok, _ in results)


def test_practice_material_files_exist():
    data = NOTEBOOKS / 'data' / '1일차'
    for name in ['알람로그_10건.txt', '알람_분류기준.txt', '알람로그_정답.txt', '교대일지_4주.txt',
                 '교대일지_안전항목.txt', '회의_받아쓰기_8월2주차.txt', '현장코멘트_추가_3건.txt']:
        assert (data / name).read_text(encoding='utf-8').strip()
