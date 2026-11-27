"""tools/learn_nb.py 테스트: 원고에서 장 노트북, 풀이 노트북, 프로젝트 노트북을 만드는 규칙."""
import base64
import re
import sys
from pathlib import Path

import nbformat
import pytest
from nbformat.v4 import new_code_cell, new_notebook, new_output

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import learn_nb  # noqa: E402

SETUP = '준비 안내입니다.\n\n```python\nimport llm\n```\n'

MANUSCRIPT = '''# 1장 [[토큰]] 시험

도입 글입니다.

## 학습 목표

질문 목록입니다.

```python
not_a_cell = True
```

## 첫 [[토큰]] 절

본문입니다.

:::예제 1-1 첫 호출
같은 질문을 세 번 보내 응답을 비교합니다.

<figure>
<svg viewBox="0 0 680 100" role="img" aria-label="그림 설명">
<rect x="1" y="1" width="10" height="10" fill="var(--teal-wash)" stroke="var(--teal)"/>
</svg>
<figcaption>그림 아래 글입니다.</figcaption>
</figure>

:::탭 Anthropic
```python
print('가')
```
:::
:::탭 OpenAI 호환
```python
print('나')
```
:::
:::

## 둘째 절

:::실습 1-2 예측하고 확인하기
결과를 먼저 적어 봅니다.

```python
guess = None  # TODO
```

:::풀이
풀이 설명입니다.

```python
guess = 3
print(guess)
```
:::
:::

:::실습 P1 프로젝트 첫 단계
```python
step1 = None
```

:::풀이
```python
step1 = 'ok'
```
:::
:::

:::정답
자가점검 정답은 B입니다.
:::
'''


def test_parse_reads_boxes_sections_and_cells():
    title, boxes = learn_nb.parse(MANUSCRIPT)
    assert title == '1장 토큰 시험'
    assert [(box['kind'], box['code']) for box in boxes] == [('예제', '1-1'), ('실습', '1-2'), ('실습', 'P1')]
    example, practice, project = boxes
    assert example['section'] == '첫 토큰 절' and practice['section'] == '둘째 절'
    assert [(role, index) for role, index, _ in example['cells']] == [('예제', 0), ('예제', 1)]
    assert [(role, index, source) for role, index, source in practice['cells']] == [
        ('실습', 0, 'guess = None  # TODO'), ('풀이', 0, 'guess = 3\nprint(guess)')]
    assert '결과를 먼저 적어 봅니다' in practice['guide'] and '풀이 설명' not in practice['guide']
    assert ':::탭 Anthropic' in example['guide'] and "print('가')" not in example['guide']
    assert learn_nb.is_project(project) and not learn_nb.is_project(practice)


def test_code_cells_lists_tags_in_order():
    assert [tag for tag, _, _ in learn_nb.code_cells(MANUSCRIPT)] == [
        '예제:1-1:0', '예제:1-1:1', '실습:1-2:0', '풀이:1-2:0', '실습:P1:0', '풀이:P1:0']


def markdown_of(notebook):
    return '\n'.join(cell.source for cell in notebook.cells if cell.cell_type == 'markdown')


def code_of(notebook):
    return [cell.source for cell in notebook.cells if cell.cell_type == 'code']


def test_chapter_notebook_has_setup_examples_and_blanks():
    notebook = learn_nb.chapter_notebook(MANUSCRIPT, SETUP, html_name='01_시험.html')
    assert notebook.cells[0].source.startswith('# 1장 토큰 시험') and '01_시험.html' in notebook.cells[0].source
    assert code_of(notebook) == ['import llm', "print('가')", "print('나')", 'guess = None  # TODO']
    text = markdown_of(notebook)
    assert '## 예제 1-1. 첫 호출' in text and '교재의 절: "첫 토큰 절"' in text
    assert '같은 질문을 세 번 보내' in text and '**Anthropic**' in text
    assert '## 실습 1-2. 예측하고 확인하기' in text
    assert '도입 글' not in text and '본문입니다' not in text and '자가점검' not in text   # 개념 설명은 HTML에만 있다
    assert 'not_a_cell' not in ''.join(code_of(notebook))
    assert ':::' not in text and '[[' not in text
    tags = [cell.metadata['tags'] for cell in notebook.cells if cell.cell_type == 'code' and cell.metadata.get('tags')]
    assert tags == [['예제:1-1:0'], ['예제:1-1:1'], ['실습:1-2:0']]


def test_solution_notebook_swaps_blanks_for_solutions():
    notebook = learn_nb.chapter_notebook(MANUSCRIPT, SETUP, solution=True)
    assert code_of(notebook) == ['import llm', "print('가')", "print('나')", 'guess = 3\nprint(guess)']


def test_project_notebook_starts_from_earlier_solutions():
    _, boxes = learn_nb.parse(MANUSCRIPT)
    first = boxes[2]
    second = dict(first, code='P2', title='둘째 단계', cells=[('실습', 0, 'step2 = None'), ('풀이', 0, 'step2 = step1')])
    steps = {1: (first, '01_시험.html'), 2: (second, '02_둘째.html')}
    notebook = learn_nb.project_notebook(2, steps, SETUP)
    assert code_of(notebook) == ['import llm', "step1 = 'ok'", 'step2 = None']
    assert '02_둘째.html' in notebook.cells[0].source and '"실습 P2"' in notebook.cells[0].source
    assert code_of(learn_nb.project_notebook(2, steps, SETUP, solution=True))[-1] == 'step2 = step1'
    assert code_of(learn_nb.project_notebook(1, steps, SETUP)) == ['import llm', 'step1 = None']


def test_has_cells_ignores_project_boxes():
    assert learn_nb.has_cells(MANUSCRIPT)
    only_project = MANUSCRIPT.split(':::예제')[0] + ':::실습 P1 단계\n```python\nx = 1\n```\n:::\n'
    assert not learn_nb.has_cells(only_project)


def test_figure_in_guide_becomes_image_with_fixed_colors():
    text = markdown_of(learn_nb.chapter_notebook(MANUSCRIPT, SETUP))
    assert '<svg' not in text and '<figure>' not in text
    assert '<img alt="그림 설명" width="680" src="data:image/svg+xml;base64,' in text
    assert '*그림 아래 글입니다.*' in text
    data = re.search(r'base64,([A-Za-z0-9+/=]+)', text).group(1)
    svg = base64.b64decode(data).decode('utf-8')
    assert 'var(--' not in svg and '#0b5a66' in svg and 'xmlns="http://www.w3.org/2000/svg"' in svg


def executed_file(tmp_path, source, output):
    cell = new_code_cell(source)
    cell.metadata['tags'] = ['예제:1-1:0']
    cell.outputs = [new_output('stream', name='stdout', text=output)]
    path = tmp_path / '실행.ipynb'
    nbformat.write(new_notebook(cells=[cell]), path)
    return path


def test_fresh_example_output_is_copied_into_chapter_notebook(tmp_path):
    outputs = learn_nb.load_outputs(executed_file(tmp_path, "print('가')", '가\n'))
    notebook = learn_nb.chapter_notebook(MANUSCRIPT, SETUP, outputs)
    first = next(cell for cell in notebook.cells if cell.metadata.get('tags') == ['예제:1-1:0'])
    second = next(cell for cell in notebook.cells if cell.metadata.get('tags') == ['예제:1-1:1'])
    assert first.outputs[0].text == '가\n' and second.outputs == []


def test_stale_output_is_not_used(tmp_path):
    outputs = learn_nb.load_outputs(executed_file(tmp_path, "print('옛 코드')", '옛 출력\n'))
    assert learn_nb.fresh_output(outputs, '예제:1-1:0', "print('가')") is None
    assert learn_nb.load_outputs(tmp_path / '없는 파일.ipynb') == {}


def test_names():
    assert learn_nb.notebook_name(Path('원고/01_LLM은_어떻게_글을_만드는가.md')) == '01_LLM은_어떻게_글을_만드는가.ipynb'
    assert learn_nb.solution_name('01_제목.ipynb') == '01_제목_풀이.ipynb'
    assert learn_nb.project_name('3') == '프로젝트_3.ipynb'


def test_setup_text_joins_common_and_chapter_code(tmp_path):
    (tmp_path / '준비.md').write_text('앞\n{{장별 준비}}\n뒤\n', encoding='utf-8')
    (tmp_path / '준비_공통.py').write_text("DATA = 'data'\n", encoding='utf-8')
    assert learn_nb.setup_text(tmp_path, '03') == "앞\nDATA = 'data'\n뒤\n"
    (tmp_path / '준비_03.py').write_text('EXTRA = 1\n', encoding='utf-8')
    assert learn_nb.setup_text(tmp_path, '03') == "앞\nDATA = 'data'\n\nEXTRA = 1\n뒤\n"


def test_setup_guide_covers_the_environment_chapter():
    """노트북만 여는 사람도 환경 준비 장의 환경 변수와 오류 표를 볼 수 있어야 한다."""
    found = sorted((ROOT / '원고').glob('00_*.md'))
    if not found:
        pytest.skip('환경 준비 장(원고/00_*.md)을 아직 쓰지 않았습니다')
    chapter = found[0].read_text(encoding='utf-8')
    setup = (ROOT / '교재_템플릿' / '준비.md').read_text(encoding='utf-8')
    variables = set(re.findall(r'`((?:ANTHROPIC|OPENAI|LLM)_[A-Z_]+)`', chapter))
    errors = re.findall(r'^\| (`[^|]+`) \| ', chapter, flags=re.M)
    missing = [item for item in sorted(variables) + errors if item.strip('`') not in setup]
    assert not missing, f'준비.md에 없는 항목: {missing}'
