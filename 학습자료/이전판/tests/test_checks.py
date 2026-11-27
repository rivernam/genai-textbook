"""checks.py 테스트: 고치기 전 send_batch.py와 풀이 파일로 검사 결과를 확인한다."""
import importlib.util
import subprocess
import sys
from pathlib import Path

NOTEBOOKS = Path(__file__).resolve().parents[1] / '노트북'
LAB = NOTEBOOKS / '코딩도구_실습'
sys.path.insert(0, str(NOTEBOOKS))
import checks  # noqa: E402


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_original_file_passes_only_what_needs_no_handling(capsys):
    module = load(LAB / 'send_batch.py')
    results = checks.run(module.ask, module.process_all)
    passed = [number for number, ok, _ in results if ok]
    assert passed == [1, 5, 6, 7]          # 재시도도 응답 검사도 없어 나머지는 실패
    output = capsys.readouterr().out
    assert '결과 4/10 통과' in output
    assert '2. 실패 429 오류는 재시도해 성공한다' in output


def test_solution_passes_all(capsys):
    module = load(LAB / '풀이' / 'send_batch_풀이.py')
    results = checks.run(module.ask, module.process_all)
    assert [ok for _, ok, _ in results] == [True] * 10
    assert '결과 10/10 통과' in capsys.readouterr().out


def test_broken_code_is_reported_not_raised(capsys):
    def ask(prompt, **kwargs):
        raise ZeroDivisionError('버그')

    def process_all(rows, ask=None):
        return [], []
    results = checks.run(ask, process_all)
    assert not any(ok for _, ok, _ in results[:8])
    assert 'ZeroDivisionError' in capsys.readouterr().out


def test_check_cli():
    done = subprocess.run([sys.executable, '-X', 'utf8', str(LAB / 'check.py'),
                           str(LAB / '풀이' / 'send_batch_풀이.py')],
                          capture_output=True, text=True, encoding='utf-8')
    assert done.returncode == 0 and '결과 10/10 통과' in done.stdout
    done = subprocess.run([sys.executable, '-X', 'utf8', str(LAB / 'check.py')],
                          capture_output=True, text=True, encoding='utf-8', cwd=LAB)
    assert done.returncode == 1 and '결과 4/10 통과' in done.stdout
