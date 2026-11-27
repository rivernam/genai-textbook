"""run_nb.py의 --changed 옵션: 코드가 바뀐 셀만 결과를 새로 넣는다."""
import sys
from pathlib import Path

from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_output

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_nb  # noqa: E402


def cell(source, tag=None, output=None):
    made = new_code_cell(source)
    if tag:
        made.metadata['tags'] = [tag]
    if output is not None:
        made.outputs = [new_output('stream', name='stdout', text=output)]
    return made


def notebooks():
    fresh = new_notebook(cells=[
        new_markdown_cell('설명'), cell('setup = 1'),
        cell('a = 1', '예제:1-1:0'), cell('b = 2  # 고침', '예제:1-2:0'),
        cell('c = 3', '예제:1-3:0'), cell('d = 4', '예제:1-4:0')])
    executed = new_notebook(cells=[
        cell('setup = 1', output='준비 옛 출력'),
        cell('a = 1', '예제:1-1:0', '1-1 옛 출력'), cell('b = 2', '예제:1-2:0', '1-2 옛 출력'),
        cell('c = 3', '예제:1-3:0', '1-3 옛 출력')])
    return fresh, executed


def test_stale_tags_are_changed_or_missing_cells():
    fresh, executed = notebooks()
    assert run_nb.stale_tags(fresh, executed) == ['예제:1-2:0', '예제:1-4:0']


def test_cells_to_run_stops_at_last_stale_cell_and_skips_examples():
    fresh, _ = notebooks()
    sources = [made.source for made in run_nb.cells_to_run(fresh, ['예제:1-2:0'])]
    assert sources == ['설명', 'setup = 1', 'a = 1', 'b = 2  # 고침']
    skipped = [made.source for made in run_nb.cells_to_run(fresh, ['예제:1-4:0'], skip={'1-3', '1-4'})]
    assert skipped == ['설명', 'setup = 1', 'a = 1', 'b = 2  # 고침', 'd = 4']      # 바뀐 셀은 skip에 있어도 실행한다


def test_merge_keeps_old_outputs_of_unchanged_cells():
    fresh, executed = notebooks()
    stale = ['예제:1-2:0']
    ran = new_notebook(cells=[cell('setup = 1', output='준비 새 출력'), cell('a = 1', '예제:1-1:0', '1-1 새 출력'),
                              cell('b = 2  # 고침', '예제:1-2:0', '1-2 새 출력')])
    merged = run_nb.merge_outputs(fresh, ran, executed, stale)
    texts = [made.outputs[0]['text'] if made.outputs else None for made in merged.cells if made.cell_type == 'code']
    assert texts == ['준비 새 출력', '1-1 옛 출력', '1-2 새 출력', '1-3 옛 출력', None]
