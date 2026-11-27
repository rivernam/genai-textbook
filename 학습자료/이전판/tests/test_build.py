"""build.py 테스트. 임시 폴더의 작은 원고로 빌드한다."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build  # noqa: E402

GLOSSARY = """# 용어집

| 용어 | 영문 | 원본의 다른 표기 | 정의 | 첫 등장 |
| --- | --- | --- | --- | --- |
| 토큰 | token | | 모델이 글을 읽고 쓰는 단위 | 2일차 |
| API 키 | API key | 키 | 호출한 사람을 식별하는 문자열 | 2일차 |
"""

MANUSCRIPT = """# 파트 1 시험

## 만드는 것 {추가}

입력과 출력의 예입니다.

## 첫 절 {원본 p.60-62}

[[토큰]]은 단위입니다. `[[토큰]]`은 코드라 그대로 둡니다. [둘째 절로](#둘째-절)

:::예제 1-1 첫 호출
:::탭 Anthropic
```python
if a < b and c & d:  # 한글 주석
    print("<tag>")
```
:::
:::탭 OpenAI 호환
```python
print(2)
```
:::
:::

:::결과
```
출력 12
```
:::

### 작은 절 {추가}

:::주의
조심합니다.
:::

:::보충
더 알아봅니다.
:::

:::요점
요점 **한 줄**입니다.
:::

## 둘째 절

:::실습 2 비용 추정
과제 설명입니다.
:::

:::정답
정답은 **B**입니다.
:::
"""


def make_project(tmp_path, manuscript=MANUSCRIPT, glossary=GLOSSARY):
    (tmp_path / '원고' / '2일차').mkdir(parents=True)
    (tmp_path / '원고' / '2일차' / '01_시험.md').write_text(manuscript, encoding='utf-8')
    (tmp_path / '원고' / '2일차' / '01_분석.md').write_text('# 분석\n\n교재에 넣지 않습니다.\n',
                                                         encoding='utf-8')
    (tmp_path / '용어집.md').write_text(glossary, encoding='utf-8')
    return tmp_path


@pytest.fixture
def page(tmp_path):
    root = make_project(tmp_path)
    build.build(root)
    return (root / '교재' / '2일차.html').read_text(encoding='utf-8')


def test_outputs_exist(tmp_path):
    root = make_project(tmp_path)
    build.build(root)
    assert (root / '교재' / 'index.html').exists()
    assert (root / '교재' / '2일차.html').exists()
    index = (root / '교재' / 'index.html').read_text(encoding='utf-8')
    assert '2일차.html' in index and '모델이 글을 읽고 쓰는 단위' in index


def test_analysis_file_is_excluded(page):
    assert '교재에 넣지 않습니다' not in page


def test_term_becomes_definition_link(page):
    assert re.search(r'<span class="term"[^>]*data-def="모델이 글을 읽고 쓰는 단위"[^>]*>토큰</span>', page)
    assert '<code>[[토큰]]</code>' in page          # 인라인 코드 안은 바꾸지 않는다


def test_example_box_with_notebook_pointer(page):
    assert re.search(r'<section class="box example" id="예제-1-1">', page)
    assert '예제 1-1' in page and '첫 호출' in page
    assert '2일차_01_시험.ipynb' in page and '# 예제 1-1' in page


def test_practice_box_with_notebook_pointer(page):
    assert re.search(r'<section class="box practice" id="실습-2">', page)
    assert '2일차_실습.ipynb' in page and '# 실습 2' in page


def test_tabs_result_answer_callouts(page):
    assert page.count('<div class="tab" data-tab="Anthropic">') == 1
    assert page.count('<div class="tab" data-tab="OpenAI 호환">') == 1
    assert '<div class="result">' in page
    assert re.search(r'<details class="answer">\s*<summary>정답 보기</summary>', page)
    assert '<strong>B</strong>' in page             # 상자 안의 Markdown도 변환된다
    assert '<aside class="callout warn">' in page and '<aside class="callout more">' in page
    assert re.search(r'<div class="gist">\s*<p>요점 <strong>한 줄</strong>입니다.</p>', page)


def test_source_tags(page):
    assert '<span class="source">원본 p.60–62</span>' in page
    assert '<span class="source added">추가</span>' in page
    assert '{원본' not in page and '{추가}' not in page


def test_code_is_escaped_and_highlighted(page):
    assert '&lt;tag&gt;' in page and '<tag>' not in page
    assert '&amp;' in page
    assert '한글 주석' in page
    assert 'class="codehilite"' in page


def test_toc_lists_every_heading(page):
    toc = page.split('<nav class="toc"')[1].split('</nav>')[0]
    for title in ['파트 1 시험', '첫 절', '작은 절', '둘째 절']:
        assert title in toc
    assert 'href="#둘째-절"' in toc


def test_no_external_resources(page):
    without_links = re.sub(r'<a\b[^>]*>', '', page)
    assert not re.search(r'(src|href)="https?://', without_links)
    assert '<link' not in page and '<script src' not in page


def test_unknown_term_fails_with_location(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 파트\n\n## 절\n\n본문\n\n[[없는용어]]를 씁니다.\n')
    with pytest.raises(SystemExit) as stopped:
        build.build(root)
    assert stopped.value.code != 0
    message = capsys.readouterr().err
    assert '01_시험.md:7' in message and '없는용어' in message


def test_example_in_first_section_fails_with_file_name(tmp_path, capsys):
    """학습 노트북의 준비 셀은 첫 절 뒤에 들어간다. 첫 절에 예제가 있으면 빌드가 알려 준다."""
    root = make_project(tmp_path, manuscript='# 파트\n\n## 절\n\n:::예제 1-1 첫 호출\n```python\nprint(1)\n```\n:::\n')
    with pytest.raises(SystemExit):
        build.build(root)
    message = capsys.readouterr().err
    assert '01_시험.md' in message and '준비 셀보다 앞에 예제 코드' in message


def test_day_without_setup_code_fails_with_file_name(tmp_path, capsys):
    """예제가 있는 일자에는 교재_템플릿/준비_<일자>.py가 있어야 한다. 없으면 무엇을 만들지 알려 준다."""
    root = make_project(tmp_path)
    (root / '원고' / '2일차').rename(root / '원고' / '9일차')
    with pytest.raises(SystemExit):
        build.build(root)
    assert '준비_9일차.py' in capsys.readouterr().err


def test_broken_internal_link_fails(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 파트\n\n## 절\n\n[없는 곳](#없는-절)\n')
    with pytest.raises(SystemExit):
        build.build(root)
    assert '없는-절' in capsys.readouterr().err


def test_unclosed_block_fails(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 파트\n\n## 절\n\n:::주의\n닫지 않았습니다.\n')
    with pytest.raises(SystemExit):
        build.build(root)
    assert '01_시험.md:5' in capsys.readouterr().err


# ---- 학습 노트북과 실행 결과 ----

def write_executed(root, cells):
    """작업/2일차/실행결과 에 실행한 노트북을 흉내 내어 둔다. cells는 (태그, 코드, 출력) 목록."""
    import nbformat
    from nbformat.v4 import new_code_cell, new_notebook, new_output
    made = []
    for tag, source, output in cells:
        cell = new_code_cell(source)
        cell.metadata['tags'] = [tag]
        cell.outputs = [new_output('stream', name='stdout', text=output)]
        made.append(cell)
    folder = root / '작업' / '2일차' / '실행결과'
    folder.mkdir(parents=True)
    nbformat.write(new_notebook(cells=made), folder / '2일차_01_시험.ipynb')


def test_build_writes_learning_notebook(tmp_path):
    import nbformat
    root = make_project(tmp_path)
    build.build(root)
    notebook = nbformat.read(root / '노트북' / '2일차_01_시험.ipynb', as_version=4)
    code = [cell.source for cell in notebook.cells if cell.cell_type == 'code']
    assert 'print(2)' in code                     # 예제의 코드가 코드 셀이 된다
    assert code[0].startswith('# 준비 (1)')       # 준비 셀이 앞에 온다


def test_fresh_results_are_inserted_after_code(tmp_path, capsys):
    root = make_project(tmp_path)
    write_executed(root, [('예제:1-1:1', 'print(2)', '2\n```json 이 들어 있어도 깨지지 않는다\n')])
    build.build(root)
    page = (root / '교재' / '2일차.html').read_text(encoding='utf-8')
    box = page.split('id="예제-1-1"')[1].split('</section>')[0]
    assert box.count('<div class="result">') == 1
    assert '```json 이 들어 있어도 깨지지 않는다' in box
    assert box.index('print') < box.index('<div class="result">')
    printed = capsys.readouterr().out
    assert '실행 결과가 없거나 코드가 바뀐 예제 셀 1개: 1-1:0' in printed


def test_stale_results_are_not_shown(tmp_path, capsys):
    root = make_project(tmp_path)
    write_executed(root, [('예제:1-1:1', 'print(3)  # 예전 코드', '3\n')])
    build.build(root)
    page = (root / '교재' / '2일차.html').read_text(encoding='utf-8')
    box = page.split('id="예제-1-1"')[1].split('</section>')[0]
    assert '<div class="result">' not in box
    assert '예제 셀 2개' in capsys.readouterr().out


def test_repeated_headings_in_later_parts_get_numbered_ids(tmp_path):
    """파트마다 되풀이되는 제목("실습", "자가점검")은 뒤 파트의 id에 파일 번호를 붙인다."""
    root = make_project(tmp_path)
    (root / '원고' / '2일차' / '02_둘째.md').write_text(
        '# 파트 둘\n\n## 첫 절\n\n글입니다.\n\n:::실습 9 과제\n해 봅니다.\n:::\n', encoding='utf-8')
    build.build(root)
    page = (root / '교재' / '2일차.html').read_text(encoding='utf-8')
    assert 'id="첫-절"' in page and 'id="첫-절-02"' in page     # 두 파일에 같은 제목 "첫 절"
    assert '2일차_02_실습.ipynb' in page          # 뒤 파트의 실습 노트북 이름
