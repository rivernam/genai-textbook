# 예시 · 예제 1-3 (4)(6)(8) 을 Claude Code 로 진행해 고친 결과입니다. 예제 1-3 (7) 에서 이 파일을 검사합니다.
# 문의를 한 건씩 Claude 에 보내 분류하고, 결과를 결과.csv 로 저장합니다.
# 실행: python send_batch.py   (환경 변수 ANTHROPIC_API_KEY 가 있어야 합니다)
import csv
import time
import anthropic

MODEL = 'claude-haiku-4-5'
SYS_CLS = ('너는 반도체 공장 현장 문의를 분류하는 도우미다. '
           '[문서안내/절차안내/긴급/데이터요청] 네 가지 중 하나로만 분류한다. '
           '출력은 {"id":..., "category":..., "urgent":true/false} JSON 한 줄만.')


def make_client():
    return anthropic.Anthropic()


def text_of(r):
    return ''.join(b.text for b in r.content if b.type == 'text')


def retryable(e):
    # 429 · 5xx · 연결 오류 · 시간 초과(APITimeoutError 는 APIConnectionError 의 하위 클래스)만 다시 보냅니다
    if isinstance(e, anthropic.APIConnectionError):
        return True
    return isinstance(e, anthropic.APIStatusError) and (e.status_code == 429 or e.status_code >= 500)


def ask(client, system, user, max_tokens=300, attempts=3):
    # SDK 자동 재시도는 끄고 여기서만 다시 보냅니다. 한 번 보낼 때 30초까지만 기다립니다
    client = client.with_options(max_retries=0, timeout=30)
    for i in range(attempts):
        try:
            return client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                          messages=[{'role': 'user', 'content': user}])
        except anthropic.APIError as e:
            if not retryable(e) or i == attempts - 1:
                raise
            time.sleep(2 ** i)                     # 1초, 2초


def run(client, rows):
    ok, failed = [], []
    for row in rows:
        try:
            r = ask(client, SYS_CLS, f"id: {row['id']}\n문의: {row['문의내용']}")
        except anthropic.APIError as e:
            failed.append({'id': row['id'], 'reason': f'{type(e).__name__}: {e}'})
            continue
        if r.stop_reason in ('max_tokens', 'refusal'):
            failed.append({'id': row['id'], 'reason': f'stop_reason={r.stop_reason}'})
            continue
        ok.append({'id': row['id'], 'answer': text_of(r)})
    return ok, failed


def main():
    with open('문의_20.csv', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    ok, failed = run(make_client(), rows)
    with open('결과.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'answer'])
        w.writeheader()
        w.writerows(ok)
    print('성공', len(ok), '· 실패', len(failed))


if __name__ == '__main__':
    main()
