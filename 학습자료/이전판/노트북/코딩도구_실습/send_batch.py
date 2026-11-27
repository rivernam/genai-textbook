"""문의를 한 건씩 모델에 보내 분류하고 결과를 CSV로 저장한다.

실습 4에서 AI 코딩 도구에 맡겨 고칠 파일이다.
지금은 재시도도, 응답 검사도, 실패 기록도 없다.

실행: python send_batch.py   (API를 실제로 부른다. 환경 변수는 llm.py 설명 참고)
검사: python check.py        (mock 호출로 검사한다. 키도 요금도 필요 없다)
"""
import csv
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import llm  # noqa: E402

DATA = HERE.parent / 'data' / '2일차'
SYSTEM = (DATA / '분류_규칙.txt').read_text(encoding='utf-8')


def ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나를 보내고 Reply를 돌려준다."""
    return send([{'role': 'user', 'content': prompt}], system=system, max_tokens=max_tokens)


def process_all(rows, ask=ask):
    """문의 목록을 차례로 분류한다. (성공 목록, 실패 목록)을 돌려준다."""
    success, failed = [], []
    for row in rows:
        reply = ask(f"id: {row['id']}\n문의: {row['문의내용']}", system=SYSTEM)
        success.append(json.loads(reply.text))
    return success, failed


def main():
    with open(DATA / '문의_예제.csv', encoding='utf-8-sig', newline='') as source:
        rows = list(csv.DictReader(source))[:20]
    success, failed = process_all(rows)
    with open(HERE / '결과.csv', 'w', encoding='utf-8-sig', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=['id', 'category', 'urgent'])
        writer.writeheader()
        writer.writerows(success)
    print(f'성공 {len(success)}건, 실패 {len(failed)}건')


if __name__ == '__main__':
    main()
