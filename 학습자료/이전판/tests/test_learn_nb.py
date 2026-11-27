"""tools/learn_nb.py 테스트: 원고에서 학습 노트북을 만드는 규칙."""
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_notebook, new_output

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import learn_nb  # noqa: E402

SETUP = '준비 안내입니다.\n\n```python\nimport llm\n```\n'

MANUSCRIPT = '''# 파트 시험

도입 글입니다. [[토큰]]을 설명합니다.

## 만드는 것 {추가}

입력과 출력의 예입니다.

```
## 코드 블록 안의 이 줄은 절 제목이 아닙니다
```

## 첫 절 {원본 p.1-2}

:::요점
요점 문장입니다.
:::

<figure>
<svg viewBox="0 0 680 100" role="img" aria-label="그림 설명">
<rect x="1" y="1" width="10" height="10" fill="var(--teal-wash)" stroke="var(--teal)"/>
</svg>
<figcaption>그림 아래 글입니다.</figcaption>
</figure>

:::예제 1-1 첫 호출
:::탭 Anthropic
```python
# 예제 1-1 (가)
print('가')
```
:::
가운데 글입니다.

```python
# 예제 1-1 (나)
print('나')
```
:::

보여 주기만 하는 코드입니다.

```python
not_a_cell = True
```

:::정답
정답은 B입니다.
:::

## 원본과 달라진 점

노트북에 넣지 않는 절입니다.
'''


def test_split_cells_makes_code_cells_only_from_example_python_blocks():
    parts = learn_nb.split_cells(MANUSCRIPT)
    code = [part for part in parts if part[0] == 'code']
    assert [(example, index) for _, example, index, _ in code] == [('1-1', 0), ('1-1', 1)]
    assert code[0][3] == "# 예제 1-1 (가)\nprint('가')"
    markdown = '\n'.join(part[1] for part in parts if part[0] == 'md')
    assert 'not_a_cell = True' in markdown             # 예제 밖의 코드는 설명 셀에 남는다
    assert '노트북에 넣지 않는 절' not in markdown


def test_notebook_structure_and_markdown_conversion():
    notebook = learn_nb.make_notebook(MANUSCRIPT, SETUP)
    kinds = [cell.cell_type for cell in notebook.cells]
    sources = [cell.source for cell in notebook.cells]
    # 도입 글과 첫 절(만드는 것) → 준비(설명, 코드) → 둘째 절부터의 본문
    assert kinds[:3] == ['markdown', 'markdown', 'code']
    assert '도입 글입니다' in sources[0] and '입력과 출력의 예입니다' in sources[0]
    assert '절 제목이 아닙니다' in sources[0] and '## 첫 절' not in sources[0]
    assert sources[1] == '준비 안내입니다.' and sources[2] == 'import llm'
    assert sources[3].startswith('## 첫 절')
    text = '\n'.join(source for kind, source in zip(kinds, sources) if kind == 'markdown')
    assert '[[' not in text and '토큰을 설명합니다' in text
    assert '## 첫 절' in text and '{원본' not in text
    assert ':::' not in text
    assert '> **요점**\n>\n> 요점 문장입니다.' in text          # 요점은 인용 블록으로 구분된다
    assert '**예제 1-1. 첫 호출**' in text and '**Anthropic**' in text
    assert '<details><summary>정답 보기</summary>' in text and '</details>' in text
    tagged = [cell.metadata['tags'] for cell in notebook.cells if cell.cell_type == 'code' and cell.metadata.get('tags')]
    assert tagged == [['예제:1-1:0'], ['예제:1-1:1']]


def test_example_in_the_first_section_is_rejected():
    """첫 절에 예제가 있으면 준비 셀을 그 앞에 둘 수 없다. 조용히 순서를 바꾸지 않고 알린다."""
    import pytest
    manuscript = MANUSCRIPT.replace('## 만드는 것 {추가}\n\n입력과 출력의 예입니다.', '입력과 출력의 예입니다.')
    with pytest.raises(ValueError, match='준비 셀보다 앞에 예제 코드'):
        learn_nb.make_notebook(manuscript, SETUP)


def test_setup_guide_covers_the_environment_chapter():
    """노트북만 여는 사람도 환경 준비 장의 환경 변수와 오류 표를 볼 수 있어야 한다."""
    import re
    chapter = (ROOT / '원고' / '2일차' / '00_환경준비.md').read_text(encoding='utf-8')
    setup = (ROOT / '교재_템플릿' / '준비.md').read_text(encoding='utf-8')
    variables = set(re.findall(r'`((?:ANTHROPIC|OPENAI|LLM)_[A-Z_]+)`', chapter))
    section = chapter.split('## 연결 확인')[1].split('\n## ')[0]      # 연결 확인 절의 오류 표만 본다
    errors = re.findall(r'^\| (`[^|]+`) \| ', section, flags=re.M)
    assert len(variables) == 8 and len(errors) == 8
    missing = [item for item in sorted(variables) + errors if item.strip('`') not in setup]
    assert not missing, f'준비.md에 없는 항목: {missing}'
    cells = learn_nb.setup_cells(setup)
    assert [cell.cell_type for cell in cells] == ['markdown', 'code', 'code', 'markdown']
    assert '코드에 적지 않습니다' in cells[0].source and '401 auth' in cells[3].source


def test_figure_becomes_image_with_fixed_colors():
    notebook = learn_nb.make_notebook(MANUSCRIPT, SETUP)
    text = '\n'.join(cell.source for cell in notebook.cells if cell.cell_type == 'markdown')
    assert '<svg' not in text and '<figure>' not in text
    assert '<img alt="그림 설명" width="680" src="data:image/svg+xml;base64,' in text
    assert '*그림 아래 글입니다.*' in text
    import base64, re
    data = re.search(r'base64,([A-Za-z0-9+/=]+)', text).group(1)
    svg = base64.b64decode(data).decode('utf-8')
    assert 'var(--' not in svg and '#0b5a66' in svg and 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert 'width="680" height="100"' in svg


def executed_file(tmp_path, source, output):
    cell = new_code_cell(source)
    cell.metadata['tags'] = ['예제:1-1:0']
    cell.outputs = [new_output('stream', name='stdout', text=output)]
    path = tmp_path / '실행.ipynb'
    nbformat.write(new_notebook(cells=[cell]), path)
    return path


def test_fresh_output_is_copied_into_notebook(tmp_path):
    outputs = learn_nb.load_outputs(executed_file(tmp_path, "# 예제 1-1 (가)\nprint('가')", '가\n'))
    notebook = learn_nb.make_notebook(MANUSCRIPT, SETUP, outputs)
    first = next(cell for cell in notebook.cells if cell.metadata.get('tags') == ['예제:1-1:0'])
    second = next(cell for cell in notebook.cells if cell.metadata.get('tags') == ['예제:1-1:1'])
    assert first.outputs[0].text == '가\n'
    assert second.outputs == []


def test_stale_output_is_not_used(tmp_path):
    outputs = learn_nb.load_outputs(executed_file(tmp_path, "print('옛 코드')", '옛 출력\n'))
    assert learn_nb.fresh_output(outputs, '1-1', 0, "# 예제 1-1 (가)\nprint('가')") is None
    assert learn_nb.load_outputs(tmp_path / '없는 파일.ipynb') == {}
