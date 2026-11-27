# 문의를 한 건씩 Claude 에 보내 분류하고, 결과를 결과.csv 로 저장합니다.
# 실행: python send_batch.py   (환경 변수 ANTHROPIC_API_KEY 가 있어야 합니다)
import csv
import anthropic

MODEL = 'claude-haiku-4-5'
SYS_CLS = ('너는 반도체 공장 현장 문의를 분류하는 도우미다. '
           '[문서안내/절차안내/긴급/데이터요청] 네 가지 중 하나로만 분류한다. '
           '출력은 {"id":..., "category":..., "urgent":true/false} JSON 한 줄만.')


def make_client():
    return anthropic.Anthropic()


def text_of(r):
    return ''.join(b.text for b in r.content if b.type == 'text')


def ask(client, system, user, max_tokens=300):
    return client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                  messages=[{'role': 'user', 'content': user}])


def run(client, rows):
    ok, failed = [], []
    for row in rows:
        r = ask(client, SYS_CLS, f"id: {row['id']}\n문의: {row['문의내용']}")
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
