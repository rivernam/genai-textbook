# 8일차 예제 폴더: Claude Code CLI 판

## 시작 순서

1. zip을 `내 문서` 아래 `genai` 폴더에 풉니다. `genai\day08` 폴더 안에 `day08-cc`(예제 폴더), `day08-pack`(예제 Skill, 서브에이전트 원본), `my-agent`(내 에이전트 폴더와 미션), `체크포인트`(진도가 밀렸을 때) 네 폴더가 생깁니다. 미션 안내는 강의안의 미션 장에 있습니다. 요청 글은 `my-agent\prompts`의 txt 파일에 있고, 답은 `day08\8일차_미션답안.txt`에 적습니다.
2. Python을 설치합니다(교육장 PC에는 없습니다). 브라우저에서 python.org/downloads/windows → Python 3.15.2 항목의 「Windows installer (64-bit)」(python-3.15.2-amd64.exe)를 받아 실행 → 첫 화면의 「Add python.exe to PATH」 체크 → 「Install Now」. 설치 뒤 「앱 실행 별칭 관리」에서 「앱 설치 관리자」의 python.exe, python3.exe를 끄고, PowerShell 창을 새로 엽니다. 인터넷이 안 되면 조교가 나눠 주는 같은 설치 파일을 씁니다. 자세한 순서는 `day08\Python_설치_가이드_Windows.pdf`에 있습니다.
3. Claude Code CLI를 설치합니다. Windows PowerShell(「x86」이 붙지 않은 항목)을 열고 `irm https://claude.ai/install.ps1 | iex`를 붙여 넣어 실행합니다. PowerShell 창을 새로 열어 `claude --version`으로 버전이 나오는지 확인합니다. PowerShell 창은 최대화해 두면 「/」 목록과 표가 잘리지 않습니다.
4. `cd $HOME\Documents\genai\day08\day08-cc`로 예제 폴더에 들어가 `claude`를 실행합니다. 처음이면 로그인 방식에서 「1. Claude account with subscription」을 고르고 교육 계정으로 로그인합니다.
5. 신뢰 질문(「Is this a project you created or one you trust?」)은 기본 선택이 No입니다. 아래 화살표로 「Yes, I trust this folder」를 고르고 Enter를 누릅니다.
6. 화면 맨 아래가 「⏸ manual mode on」(수동 모드)인지 확인합니다. 모델은 폴더 설정에 따라 Sonnet 5.5로 시작합니다(`/model`로 확인).
7. 첫 요청으로 「환경 점검입니다. python bench/env_check.py를 실행하고 출력을 그대로 보여 주세요.」를 보냅니다. 권한 프롬프트 없이 마지막 줄이 「환경 점검 8/8 · 모두 통과」이면 준비가 끝났습니다.

자주 쓰는 조작: 권한 프롬프트에서 한 번만 허용은 「1. Yes」, 새 세션은 `/clear`, 멈추기는 Esc, 접힌 도구 줄 펼치기는 Ctrl+O, 권한 모드 변경은 Shift+Tab(manual → accept edits → plan → auto), 나가기는 `/exit`.

## 들어 있는 것

- `CLAUDE.md`: 업무 보조 지시, 도구 설명서, DB 테이블 목록
- `.claude/settings.json`: 권한 규칙(python tools와 bench는 허용, data/의 읽기와 수정, rules/의 수정은 거부), 권한 수동 모드(defaultMode default)
- `.claude/skills/`, `.claude/agents/`: 처음에는 비어 있습니다. 예제에서 `..\day08-pack`의 원본을 복사해 장착합니다
- `tools/`: 도구 스크립트(calc, query_db, search_docs, grade_tilt, check_report, check_minutes, check_summary, check_defects(예제 1-5), check_daily(예제 3-6), scan_skill, log_tool, guard_rules)
- `bench/`: 환경 점검(env_check, 첫 메시지), 공유 묶음(pack_share), 강사 참고용 측정 스크립트(run_task, 헤드리스 실행 claude -p 로 돌림)
- `data/`: SL-FAB 전공정 DB, 사내 문서
- `rules/`, `mission_tables/`: DB 밖 기준표, 예제 카드, 안내문 틀, 예제 결정표
- `inbox/`: 밖에서 받았다고 가정한 Skill(예제 3-4 점검용 견본, 실행하지 않습니다)
- `prompts/`: 세 줄이 넘는 예제 요청문(`<예제번호>_<단계>.txt`). 메모장으로 열어 복사해 붙여 넣습니다
- `samples/`: 회의록 가상 자료(MTG-2025-W01 ~ W10)
- `out/`, `logs/`: 보고서와 로그가 쌓이는 곳(처음엔 비어 있음)

모든 데이터는 실습용 가상 자료입니다. 사내 실데이터와 API 키를 이 폴더에 넣지 마십시오.

## 필요한 것

- Claude Code CLI(최신, `claude --version`), Python 3(PowerShell에서 `python --version`)
- `python` 명령이 인식되지 않고 `py --version`만 실행되면, claude 요청에 「python 대신 py로 …」라는 말을 넣습니다(권한 프롬프트가 나오면 「1. Yes」를 고릅니다). 차단 훅은 python 명령으로 돌기 때문에 python이 잡히지 않으면 막지 못하고 지나갑니다. 꼭 python --version이 나오게 설치합니다. 설치 방법은 Python 설치 가이드(Windows)를 참고합니다
- Git, Node는 필요 없습니다
