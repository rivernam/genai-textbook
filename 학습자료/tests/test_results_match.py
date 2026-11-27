"""교재에 실린 실행 결과가 지금 원고의 코드로 실행한 것인지 검사한다.

예제와 풀이의 실행 결과는 build.py 가 풀이 노트북을 실행한 사본(작업/실행결과/)에서 가져온다.
원고의 코드를 고치고 다시 실행하지 않으면 그 셀은 결과 없이 실린다. 이 검사가 그것을 잡는다.
관통 프로젝트 상자는 프로젝트 풀이 노트북의 실행 결과와 맞춘다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import learn_nb  # noqa: E402

MANUSCRIPTS = sorted(path for path in (ROOT / '원고').glob('[0-9][0-9]_*.md')
                     if any(role != '실습' for _, role, _ in learn_nb.code_cells(path.read_text(encoding='utf-8'))))


def executed_name(tag, path):
    code = tag.split(':')[1]
    notebook = learn_nb.project_name(code[1:]) if code.startswith('P') else learn_nb.notebook_name(path)
    return learn_nb.solution_name(notebook)


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_every_example_and_solution_cell_has_fresh_output(path):
    cells = [(tag, source) for tag, role, source in learn_nb.code_cells(path.read_text(encoding='utf-8'))
             if role != '실습']
    names = {executed_name(tag, path) for tag, _ in cells}
    outputs = {}
    for name in names:
        outputs.update(learn_nb.load_outputs(ROOT / '작업' / '실행결과' / name))
    if not outputs:
        pytest.skip('실행 결과가 없습니다')
    stale = [tag for tag, source in cells if learn_nb.fresh_output(outputs, tag, source) is None]
    assert not stale, (f'원고의 코드와 실행 결과가 맞지 않습니다. python tools/run_nb.py {sorted(names)[0]} 로 '
                       '다시 실행하세요:\n' + '\n'.join(stale))
