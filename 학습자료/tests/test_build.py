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
| 토큰 | token | | 모델이 글을 읽고 쓰는 단위 | 1장 |
| API 키 | API key | 키 | 호출한 사람을 식별하는 문자열 | 5장 |
"""

MANUSCRIPT = """# 1장 시험

## 학습 목표

질문 목록입니다.

## 첫 절

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

### 작은 절

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

:::실습 1-2 비용 추정
과제 설명입니다.

```python
answer = None  # TODO
```

:::풀이
```python
answer = 42
print(answer)
```
:::
:::

:::실습 P3 프로젝트 단계
과제 설명입니다.

```python
step3 = None  # TODO
```

:::풀이
```python
step3 = 'done'
```
:::
:::

:::정답
정답은 **B**입니다.
:::
"""


def make_project(tmp_path, manuscript=MANUSCRIPT, glossary=GLOSSARY):
    (tmp_path / '원고').mkdir(parents=True)
    (tmp_path / '원고' / '01_시험.md').write_text(manuscript, encoding='utf-8')
    (tmp_path / '원고' / '메모.md').write_text('# 메모\n\n교재에 넣지 않습니다.\n', encoding='utf-8')
    (tmp_path / '용어집.md').write_text(glossary, encoding='utf-8')
    return tmp_path


@pytest.fixture
def page(tmp_path):
    root = make_project(tmp_path)
    build.build(root)
    return (root / '교재' / '01_시험.html').read_text(encoding='utf-8')


def test_outputs_exist(tmp_path):
    root = make_project(tmp_path)
    (root / '원고' / '07_둘째.md').write_text('# 7장 둘째\n\n## 절\n\n글입니다.\n', encoding='utf-8')
    build.build(root)
    assert (root / '교재' / 'index.html').exists()
    assert (root / '교재' / '01_시험.html').exists() and (root / '교재' / '07_둘째.html').exists()
    index = (root / '교재' / 'index.html').read_text(encoding='utf-8')
    assert '01_시험.html' in index and '모델이 글을 읽고 쓰는 단위' in index
    # 차례는 부로 묶는다. 1장은 1부, 7장은 3부
    body = index.split('<article')[1]                 # 상단 메뉴의 링크는 빼고 차례 본문만 본다
    assert body.index('1부 LLM의 원리') < body.index('01_시험.html') < body.index('3부 검색과 RAG') < body.index('07_둘째.html')
    assert '>1장</a>' in index and '>7장</a>' in index          # 상단 메뉴의 장 이름


def test_file_without_chapter_number_is_excluded(page):
    assert '교재에 넣지 않습니다' not in page


def test_term_becomes_definition_link(page):
    assert re.search(r'<span class="term"[^>]*data-def="모델이 글을 읽고 쓰는 단위"[^>]*>토큰</span>', page)
    assert '<code>[[토큰]]</code>' in page          # 인라인 코드 안은 바꾸지 않는다


def test_example_box_with_notebook_pointer(page):
    assert re.search(r'<section class="box example" id="예제-1-1">', page)
    assert '예제 1-1' in page and '첫 호출' in page
    assert '<code>01_시험.ipynb</code>의 <code>예제 1-1</code>' in page


def test_practice_box_with_notebook_pointer(page):
    assert re.search(r'<section class="box practice" id="실습-1-2">', page)
    assert '<code>01_시험.ipynb</code>의 <code>실습 1-2</code>' in page
    assert '<code>프로젝트_3.ipynb</code>' in page                  # 관통 프로젝트 단계는 프로젝트 노트북
    assert re.search(r'<details class="answer">\s*<summary>풀이 보기</summary>', page)


def test_tabs_result_answer_callouts(page):
    assert page.count('<div class="tab" data-tab="Anthropic">') == 1
    assert page.count('<div class="tab" data-tab="OpenAI 호환">') == 1
    assert '<div class="result">' in page
    assert re.search(r'<details class="answer">\s*<summary>정답 보기</summary>', page)
    assert '<strong>B</strong>' in page             # 상자 안의 Markdown도 변환된다
    assert '<aside class="callout warn">' in page and '<aside class="callout more">' in page
    assert re.search(r'<div class="gist">\s*<p>요점 <strong>한 줄</strong>입니다.</p>', page)


def test_source_tag_in_heading_fails(tmp_path, capsys):
    """2판은 본문에 원본 쪽수를 두지 않는다(작성규칙 4절). 1판 습관대로 적으면 빌드가 알려 준다."""
    root = make_project(tmp_path, manuscript='# 장\n\n## 절 {원본 p.60-62}\n\n글\n')
    with pytest.raises(SystemExit):
        build.build(root)
    message = capsys.readouterr().err
    assert '01_시험.md:3' in message and '원본 쪽수' in message


def test_code_is_escaped_and_highlighted(page):
    assert '&lt;tag&gt;' in page and '<tag>' not in page
    assert '&amp;' in page
    assert '한글 주석' in page
    assert 'class="codehilite"' in page


def test_toc_lists_every_heading(page):
    toc = page.split('<nav class="toc"')[1].split('</nav>')[0]
    for title in ['1장 시험', '첫 절', '작은 절', '둘째 절']:
        assert title in toc
    assert 'href="#둘째-절"' in toc


def test_no_external_resources(page):
    without_links = re.sub(r'<a\b[^>]*>', '', page)
    assert not re.search(r'(src|href)="https?://', without_links)
    assert '<link' not in page and '<script src' not in page


def test_unknown_term_fails_with_location(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 장\n\n## 절\n\n본문\n\n[[없는용어]]를 씁니다.\n')
    with pytest.raises(SystemExit) as stopped:
        build.build(root)
    assert stopped.value.code != 0
    message = capsys.readouterr().err
    assert '01_시험.md:7' in message and '없는용어' in message


def test_solution_box_outside_practice_fails(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 장\n\n## 절\n\n:::풀이\n글\n:::\n')
    with pytest.raises(SystemExit):
        build.build(root)
    assert '01_시험.md:5' in capsys.readouterr().err


def test_setup_code_is_common_plus_chapter_file(tmp_path, monkeypatch):
    """준비 (2) 셀에는 준비_공통.py 가 들어가고, 준비_<NN>.py 가 있으면 그 장에만 이어 붙는다."""
    import nbformat
    templates = tmp_path / '템플릿'
    templates.mkdir()
    for name in ['page.html', 'style.css', 'app.js']:
        (templates / name).write_text((build.TEMPLATES / name).read_text(encoding='utf-8'), encoding='utf-8')
    (templates / '준비.md').write_text('안내\n\n```python\n{{장별 준비}}\n```\n', encoding='utf-8')
    (templates / '준비_공통.py').write_text("DATA = 'data'\n", encoding='utf-8')
    (templates / '준비_01.py').write_text("ONLY_ONE = 1\n", encoding='utf-8')
    monkeypatch.setattr(build, 'TEMPLATES', templates)
    root = make_project(tmp_path)
    second_chapter = MANUSCRIPT.replace('1장 시험', '2장 둘째').split(':::실습 P3')[0]   # 프로젝트 단계는 책에 한 번만
    (root / '원고' / '02_둘째.md').write_text(second_chapter, encoding='utf-8')
    build.build(root)
    first = nbformat.read(root / '노트북' / '01_시험.ipynb', as_version=4).cells[2].source
    second = nbformat.read(root / '노트북' / '02_둘째.ipynb', as_version=4).cells[2].source
    assert "DATA = 'data'" in first and 'ONLY_ONE' in first
    assert "DATA = 'data'" in second and 'ONLY_ONE' not in second


def test_broken_internal_link_fails(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 장\n\n## 절\n\n[없는 곳](#없는-절)\n')
    with pytest.raises(SystemExit):
        build.build(root)
    assert '없는-절' in capsys.readouterr().err


def test_unclosed_block_fails(tmp_path, capsys):
    root = make_project(tmp_path, manuscript='# 장\n\n## 절\n\n:::주의\n닫지 않았습니다.\n')
    with pytest.raises(SystemExit):
        build.build(root)
    assert '01_시험.md:5' in capsys.readouterr().err


# ---- 장 노트북, 풀이 노트북, 프로젝트 노트북과 실행 결과 ----

def write_executed(root, cells, name='01_시험_풀이.ipynb'):
    """작업/실행결과 에 실행한 풀이 노트북을 흉내 내어 둔다. cells는 (태그, 코드, 출력) 목록."""
    import nbformat
    from nbformat.v4 import new_code_cell, new_notebook, new_output
    made = []
    for tag, source, output in cells:
        cell = new_code_cell(source)
        cell.metadata['tags'] = [tag]
        cell.outputs = [new_output('stream', name='stdout', text=output)]
        made.append(cell)
    folder = root / '작업' / '실행결과'
    folder.mkdir(parents=True, exist_ok=True)
    nbformat.write(new_notebook(cells=made), folder / name)


def code_sources(path):
    import nbformat
    return [cell.source for cell in nbformat.read(path, as_version=4).cells if cell.cell_type == 'code']


def test_chapter_notebook_has_examples_and_blanks_but_no_solutions(tmp_path):
    root = make_project(tmp_path)
    build.build(root)
    code = code_sources(root / '노트북' / '01_시험.ipynb')
    assert code[0].startswith('# 준비 (1)')       # 준비 셀이 앞에 온다
    assert 'print(2)' in code                     # 예제의 코드
    assert 'answer = None  # TODO' in code        # 실습 빈칸
    assert not any('answer = 42' in source for source in code)       # 풀이는 공유하는 노트북에 넣지 않는다
    assert not any('step3' in source for source in code)             # 관통 프로젝트는 장 노트북에 넣지 않는다


def test_solution_notebook_replaces_blanks_with_solutions(tmp_path):
    root = make_project(tmp_path)
    build.build(root)
    code = code_sources(root / '작업' / '풀이' / '01_시험_풀이.ipynb')
    assert 'print(2)' in code and 'answer = 42\nprint(answer)' in code
    assert 'answer = None  # TODO' not in code


def test_project_notebook_starts_from_previous_step_solution(tmp_path):
    root = make_project(tmp_path)
    (root / '원고' / '02_둘째.md').write_text(
        '# 2장\n\n## 절\n\n:::실습 P4 다음 단계\n과제\n\n```python\nstep4 = None\n```\n\n'
        ':::풀이\n```python\nstep4 = step3\n```\n:::\n:::\n', encoding='utf-8')
    build.build(root)
    code = code_sources(root / '노트북' / '프로젝트_4.ipynb')
    assert code.index("step3 = 'done'") < code.index('step4 = None')    # 3단계 풀이 다음에 4단계 빈칸
    assert (root / '노트북' / '프로젝트_3.ipynb').exists()
    assert not (root / '노트북' / '02_둘째.ipynb').exists()            # 프로젝트 상자만 있는 장은 장 노트북이 없다


def test_fresh_results_are_inserted_after_code(tmp_path, capsys):
    root = make_project(tmp_path)
    write_executed(root, [('예제:1-1:1', 'print(2)', '2\n```json 이 들어 있어도 깨지지 않는다\n'),
                          ('풀이:1-2:0', 'answer = 42\nprint(answer)', '42\n')])
    build.build(root)
    page = (root / '교재' / '01_시험.html').read_text(encoding='utf-8')
    box = page.split('id="예제-1-1"')[1].split('</section>')[0]
    assert box.count('<div class="result">') == 1
    assert '```json 이 들어 있어도 깨지지 않는다' in box
    assert box.index('print') < box.index('<div class="result">')
    solution = page.split('id="실습-1-2"')[1].split('</section>')[0]
    assert solution.count('<div class="result">') == 1               # 풀이에도 실행 결과가 붙는다. 빈칸에는 붙지 않는다
    notebook = (root / '노트북' / '01_시험.ipynb').read_text(encoding='utf-8')
    assert '```json 이 들어 있어도' in notebook                     # 장 노트북의 예제 셀에도 결과가 들어간다
    printed = capsys.readouterr().out
    assert '예제:1-1:0' in printed and '예제:1-1:1' not in printed


def test_stale_results_are_not_shown(tmp_path, capsys):
    root = make_project(tmp_path)
    write_executed(root, [('예제:1-1:1', 'print(3)  # 예전 코드', '3\n')])
    build.build(root)
    page = (root / '교재' / '01_시험.html').read_text(encoding='utf-8')
    box = page.split('id="예제-1-1"')[1].split('</section>')[0]
    assert '<div class="result">' not in box
    assert '예제:1-1:1' in capsys.readouterr().out


def test_project_results_come_from_project_run(tmp_path):
    root = make_project(tmp_path)
    write_executed(root, [('풀이:P3:0', "step3 = 'done'", '프로젝트 출력\n')], name='프로젝트_3_풀이.ipynb')
    build.build(root)
    page = (root / '교재' / '01_시험.html').read_text(encoding='utf-8')
    assert '프로젝트 출력' in page.split('id="실습-P3"')[1].split('</section>')[0]
