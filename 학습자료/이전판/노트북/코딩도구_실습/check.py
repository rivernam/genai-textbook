"""send_batch.py가 다섯 가지 기준을 지키는지 mock 호출로 검사한다.

사용법: python check.py [검사할 파일]      (파일을 적지 않으면 send_batch.py)
키도 요금도 필요 없다. 모두 통과하면 종료 코드 0, 아니면 1.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import checks  # noqa: E402


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'send_batch.py'
    spec = importlib.util.spec_from_file_location('target', target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = checks.run(module.ask, module.process_all)
    print(f'검사한 파일 {target.name}')
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == '__main__':
    main()
