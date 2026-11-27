7일차 · Claude Code CLI 실습 준비
(교육장 PC: Windows PowerShell. 강의안 11~18장과 같은 순서)

[오리엔테이션 · 코랩 노트북을 연 뒤]
1. 이 zip 을 내 문서\genai 에 풉니다
   → genai\day07\my-agent 폴더가 생깁니다(안에 bench, tools, data, CLAUDE.md)
2. 시작 메뉴 → Windows PowerShell(x86 아님)을 열고 창을 최대화합니다
3. Python 확인: py --version
   → 3.8 이상이면 4로. 없으면 같은 폴더의 Python_설치_가이드_Windows.pdf 대로 설치
     (「Add python.exe to PATH」 체크, 설치 뒤 PowerShell 창을 새로 엽니다)
4. Claude Code 설치(PC에 한 번, 8일차에도 그대로 씀)
   irm https://claude.ai/install.ps1 | iex
   → PowerShell 창을 새로 열어 claude --version 에 버전 숫자가 나오면 됩니다
5. 실습 폴더에서 claude 실행
   cd $HOME\Documents\genai\day07\my-agent
   claude
   → 로그인 방식 「1. Claude account with subscription」
   → 브라우저에서 교육 계정(samsungNN@scopelabs.site) → 후이즈 메일 「로그인」
     (「Google로 계속하기」는 누르지 않습니다. 링크는 10분 뒤 만료)
   → 터미널 「Login successful」 → Enter
6. 신뢰 질문: 기본 선택이 「No, exit」 → ↓ 한 번 → 「Yes, I trust this folder」 → Enter
   (경로 끝이 day07\my-agent, ⚠ 줄 「pre-approves 8 tool permissions」)
   폴더를 한 번은 이렇게 대화 화면으로 열어 신뢰해야 설정 파일의 허용 목록이 적용됩니다
7. 입력창에 /status → Email 이 교육 계정인지 확인 → Esc
   맨 아래 「manual mode on」, 시작 줄 「Using Sonnet 5.5」 확인
   (모드가 다르면 Shift+Tab, 모델이 다르면 /model 에서 Sonnet)
8. 첫 메시지로 아래 문장을 보냅니다
   환경 점검입니다. python bench/env_check.py를 실행하고 출력을 그대로 보여 주세요.
   → 권한 프롬프트 없이 「환경 점검 8/8 · 모두 통과」가 나오면 됩니다
   PowerShell 창은 수업 끝까지 닫지 않습니다

[파트 2 · 예제 2-4 를 마친 뒤]
9. 같은 창에서 질문 「PKG-B310 제품 스트립은 모두 몇 개인가요?」(답 809)
   → 답 위 접힌 줄 「Ran 1 shell command」에서 Ctrl+O 로 펼쳐 명령과 결과를 보고, Ctrl+O 로 닫습니다
10. 「notes.md 파일을 새로 만들어 방금 질문과 답을 한 줄로 적어 주세요.」
   → 권한 프롬프트 「Do you want to create notes.md?」를 읽고 숫자 1(「1. Yes」)
   → 2번(accept edits 전환)과 「switch to auto mode」는 고르지 않습니다

[파트 3 · 미션 3 을 마친 뒤]
11. 미션 3 의 (7) 셀을 실행해 persona_for_claude.md 를 받아 둡니다
   → 8일차 첫 실습에서 CLAUDE.md 에 붙여 넣습니다

자주 쓰는 키: Esc = 멈추기, /clear = 새 세션, /exit = 나가기, Ctrl+O = 접힌 줄 펼치기/닫기
my-agent 폴더와 persona_for_claude.md 는 지우지 않습니다.
「'claude' 용어가 … 인식되지 않습니다」가 나오면 PowerShell 창을 새로 엽니다. 그래도 안 되면 조교를 부릅니다.
