"""send_batch.py를 다섯 가지 기준에 맞게 고친 예시.

기준 1  재시도할 만한 오류는 1초, 2초로 대기 시간을 늘리며 세 번까지 보낸다
기준 2  그 밖의 오류(400, 401, 404 등)는 재시도하지 않고 예외를 바로 다시 발생시킨다
기준 3  재시도 횟수는 ask() 한 곳에서만 정한다
기준 4  한 건이 실패해도 멈추지 않고, 실패한 건의 id와 사유를 남긴다
기준 5  잘린 응답, 거절된 응답, JSON으로 읽을 수 없는 응답은 실패로 처리한다
"""
import csv
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import llm  # noqa: E402

DATA = HERE.parent.parent / 'data' / '2일차'
SYSTEM = (DATA / '분류_규칙.txt').read_text(encoding='utf-8')


def ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나를 보내고 Reply를 돌려준다. 재시도할 만한 오류는 tries번까지 보낸다."""
    messages = [{'role': 'user', 'content': prompt}]
    for attempt in range(tries):
        try:
            return send(messages, system=system, max_tokens=max_tokens)
        except llm.CallError as error:
            # 기준 2: 재시도해도 결과가 같은 오류와 마지막 실패는 예외를 그대로 다시 발생시킨다
            if not error.retryable or attempt == tries - 1:
                raise
            sleep(2 ** attempt)  # 기준 1: 1초, 2초


def check_reply(reply):
    """쓸 수 없는 응답이면 사유를, 쓸 수 있으면 None을 돌려준다."""
    if reply.stop_reason != 'end':                 # 정상 종료가 아니면 쓰지 않는다
        return {'max_tokens': '잘림', 'refusal': '거절'}.get(reply.stop_reason, '비정상 종료')
    try:
        parsed = json.loads(reply.text)
    except json.JSONDecodeError:
        return '파싱 오류'
    if not isinstance(parsed, dict) or 'category' not in parsed:
        return '파싱 오류'
    return None


def process_all(rows, ask=ask):
    """문의 목록을 차례로 분류한다. (성공 목록, 실패 목록)을 돌려준다."""
    success, failed = [], []
    for row in rows:
        try:
            reply = ask(f"id: {row['id']}\n문의: {row['문의내용']}", system=SYSTEM)
        except llm.CallError as error:          # 기준 4: 멈추지 않고 사유를 남긴다
            failed.append((row['id'], error.kind))
            continue
        reason = check_reply(reply)             # 기준 5
        if reason:
            failed.append((row['id'], reason))
        else:
            success.append(json.loads(reply.text))
    return success, failed


def main():
    with open(DATA / '문의_예제.csv', encoding='utf-8-sig', newline='') as source:
        rows = [row for row in csv.DictReader(source) if row['문의내용'].strip()][:20]
    success, failed = process_all(rows)
    with open(HERE / '결과.csv', 'w', encoding='utf-8-sig', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=['id', 'category', 'urgent'],
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(success)
    print(f'성공 {len(success)}건, 실패 {len(failed)}건 {failed}')


if __name__ == '__main__':
    main()
