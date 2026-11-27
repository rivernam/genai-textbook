"""교재에 실린 실행 결과가 지금 원고의 코드로 실행한 것인지 검사한다.

예제의 실행 결과는 build.py 가 실행한 노트북(작업/N일차/실행결과/)에서 가져온다.
원고의 코드를 고치고 다시 실행하지 않으면 그 예제는 결과 없이 실린다. 이 검사가 그것을 잡는다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import learn_nb  # noqa: E402

MANUSCRIPTS = sorted(path for path in (ROOT / '원고').glob('*/*.md')
                     if not path.stem.endswith('_분석')
                     and learn_nb.has_examples(path.read_text(encoding='utf-8')))


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: f'{path.parent.name}/{path.name}')
def test_every_example_cell_has_fresh_output(path):
    day = path.parent.name
    name = learn_nb.notebook_name(day, path)
    outputs = learn_nb.load_outputs(ROOT / '작업' / day / '실행결과' / name)
    if not outputs:
        pytest.skip('실행 결과가 없습니다')
    stale = [f'예제 {example} 의 {index + 1}번째 코드'
             for kind, example, index, source in
             (part for part in learn_nb.split_cells(path.read_text(encoding='utf-8')) if part[0] == 'code')
             if learn_nb.fresh_output(outputs, example, index, source) is None]
    assert not stale, (f'원고의 코드와 실행 결과가 맞지 않습니다. python tools/run_nb.py {name} {day} 로 다시 실행하세요:\n'
                       + '\n'.join(stale))
