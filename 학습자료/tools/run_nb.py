"""노트북을 실행해 결과가 든 사본을 작업 폴더에 저장한다.

사용법: python tools/run_nb.py <노트북 이름> [--changed] [--skip 예제번호,예제번호] [--also 예제번호]
예:     python tools/run_nb.py 01_LLM은_어떻게_글을_만드는가_풀이.ipynb
        python tools/run_nb.py 05_LLM_API_풀이.ipynb --changed --skip 5-3
교재에 싣는 결과는 풀이 노트북(작업/풀이/)을 실행해 얻는다. 풀이 노트북에는 예제와 풀이가 모두 들어 있다.
노트북은 작업/풀이/ 에서 먼저 찾고, 없으면 노트북/ 에서 찾는다. 실행은 노트북/ 폴더에서 한다.
결과는 작업/실행결과/<노트북 이름> 에 저장한다. 원래 노트북은 건드리지 않는다.
환경 변수의 키로 실제 API 를 부르므로 비용이 든다. 실행 전에 사용자 동의를 받는다.

옵션 없이 실행하면 처음부터 끝까지 실행한다.
--changed 는 코드가 바뀐 예제 셀의 결과만 새로 만든다. 처음부터 마지막으로 바뀐 셀까지 실행하고,
바뀐 셀의 출력만 사본에 넣는다. 나머지 셀은 사본에 있던 출력을 그대로 둔다. 문구만 고친 셀 때문에
모든 예제의 숫자가 바뀌는 일을 피하려고 쓴다. --skip 은 그 과정에서 실행하지 않을 예제 번호다.
바뀐 셀이 쓰지 않는 예제(요금이 큰 모델 비교 등)를 건너뛴다. 건너뛴 예제의 변수는 만들어지지 않는다.
--also 는 코드가 바뀌지 않았어도 결과를 새로 넣을 예제 번호다. 같은 대화를 이어 가는 예제에서 셀 하나를
고치거나 더했을 때, 그 예제의 모든 셀을 한 번의 실행 결과로 맞추려고 쓴다.
"""
import copy
import shutil
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def tag_of(cell):
    """예제 코드 셀의 태그('예제:1-7:2'). 준비 셀과 설명 셀은 None."""
    tags = cell.get('metadata', {}).get('tags', [])
    return tags[0] if cell.cell_type == 'code' and tags else None


def stale_tags(fresh, executed):
    """다시 실행해야 하는 셀의 태그. 실행한 사본에 없거나 코드가 다른 셀이다."""
    done = {tag_of(cell): cell.source.strip() for cell in executed.cells if tag_of(cell)}
    return [tag_of(cell) for cell in fresh.cells
            if tag_of(cell) and done.get(tag_of(cell)) != cell.source.strip()]


def cells_to_run(fresh, stale, skip=()):
    """처음부터 마지막으로 바뀐 셀까지의 셀. 바뀌지 않은 셀 가운데 skip에 든 예제는 뺀다."""
    last = max(index for index, cell in enumerate(fresh.cells) if tag_of(cell) in stale)
    return [cell for cell in fresh.cells[:last + 1]
            if tag_of(cell) in stale or not tag_of(cell) or tag_of(cell).split(':')[1] not in skip]


def merge_outputs(fresh, ran, executed, stale):
    """바뀐 셀과 준비 셀은 이번 실행의 출력을, 나머지 셀은 사본에 있던 출력을 넣는다."""
    new = {tag_of(cell): cell.outputs for cell in ran.cells if tag_of(cell)}
    old = {tag_of(cell): cell.outputs for cell in executed.cells if tag_of(cell)}
    setup = iter([cell.outputs for cell in ran.cells if cell.cell_type == 'code' and not tag_of(cell)])
    for cell in fresh.cells:
        if cell.cell_type != 'code':
            continue
        tag = tag_of(cell)
        cell.outputs = next(setup, []) if tag is None else (new if tag in stale else old).get(tag, [])
    return fresh


def execute(notebook):
    client = NotebookClient(notebook, timeout=600, kernel_name='python3', allow_errors=True,
                            resources={'metadata': {'path': str(ROOT / '노트북')}})
    client.execute()
    # 예제가 만든 결과 파일(엑셀, DB)은 공유 폴더에 남기지 않는다
    shutil.rmtree(ROOT / '노트북' / 'out', ignore_errors=True)
    return notebook


def main():
    args = sys.argv[1:]
    skip = set(args[args.index('--skip') + 1].split(',')) if '--skip' in args else set()
    name = args[0]
    source = ROOT / '작업' / '풀이' / name
    notebook = nbformat.read(source if source.exists() else ROOT / '노트북' / name, as_version=4)
    out_dir = ROOT / '작업' / '실행결과'
    out_dir.mkdir(parents=True, exist_ok=True)

    ran = notebook
    if '--changed' in args and (out_dir / name).exists():
        executed = nbformat.read(out_dir / name, as_version=4)
        stale = stale_tags(notebook, executed)
        if '--also' in args:
            # 한 예제 안에서 대화가 이어지면 셀 하나만 새로 실행한 결과를 넣을 수 없다. 그 예제의 셀을 모두 다시 넣는다
            also = set(args[args.index('--also') + 1].split(','))
            stale = [tag_of(cell) for cell in notebook.cells
                     if tag_of(cell) and (tag_of(cell) in stale or tag_of(cell).split(':')[1] in also)]
        if not stale:
            print(f'{name}: 코드가 바뀐 셀이 없습니다')
            return
        ran = copy.deepcopy(notebook)
        ran.cells = cells_to_run(ran, stale, skip)
        execute(ran)
        notebook = merge_outputs(notebook, ran, executed, stale)
        print(f'{name}: 바뀐 셀 {len(stale)}개의 결과를 새로 넣음 {stale}')
    else:
        execute(notebook)
    nbformat.write(notebook, out_dir / name)
    errors = [(index, output.get('ename'), output.get('evalue', '')[:200])
              for index, cell in enumerate(ran.cells) if cell.cell_type == 'code'
              for output in cell.outputs if output.output_type == 'error']
    print(f'{name}: 셀 {len(ran.cells)}개 실행, 오류 {len(errors)}개')
    for error in errors:
        print('  오류', error)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
