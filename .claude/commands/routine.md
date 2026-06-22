---
description: 주간 큐레이션 — triage 채점 → 한글요약 → Obsidian 인덱스 재생성 (fetch는 런처가 선행)
argument-hint: [없음]
allowed-tools: Bash(.venv/Scripts/python.exe:*), Bash(echo:*), Bash(cat:*), Read, Write
---

paper-monitor 큐레이션 루틴. 신규 fetch는 런처(run-routine.ps1)가 **이미 실행**했으니 여기서는 하지 않는다.
DB에 쌓인 미평가/미요약 논문을 처리하고 인덱스를 갱신한다.

**중요(무인 실행):**
- 모든 bash 명령은 **포그라운드로 실행하고 절대 백그라운드(run_in_background)로 돌리지 말 것.** headless 단발 실행이라 백그라운드 대기 시 그대로 중단된다.
- 중간에 사용자에게 질문하지 말 것. 각 단계에서 처리할 게 0건이면 조용히 다음으로.
- 파이썬은 반드시 `.venv/Scripts/python.exe`를 쓸 것(스케줄러 환경엔 venv가 활성화돼 있지 않음).

## 1. Triage 채점 (미평가 전부)
```bash
.venv/Scripts/python.exe scripts/list_untriaged.py --limit 500
```
- 출력된 미평가 논문(status='new')의 abstract를 **`.claude/commands/triage.md` 루브릭**(small molecule generation + lead optimization 플랫폼 관점, 0~5점)으로 채점.
- 결과 JSON 배열 `[{"id","score","reason"}]`(reason 한국어 한 줄)을 stdin으로 저장:
  `echo '<json>' | .venv/Scripts/python.exe scripts/save_scores.py`
- 0건이면 스킵.

## 2. 한글 요약 (score>=threshold 미요약 전부)
```bash
.venv/Scripts/python.exe scripts/list_for_kr_summary.py --limit 500
```
- 각 논문을 **`.claude/commands/kr-summarize.md` 규칙**(문제·방법·결과 3축, 3문장 이내, 용어 한영 병기)으로 요약.
- 결과 JSON 배열 `[{"id","kr_summary"}]`을 stdin으로 저장:
  `echo '<json>' | .venv/Scripts/python.exe scripts/save_kr_summary.py`
- 0건이면 스킵.

## 3. Obsidian 인덱스 재생성 (실제 vault)
```bash
.venv/Scripts/python.exe scripts/build_keyword_indexes.py --outdir "C:/Users/230016/OneDrive/Obsidian/Yuhan/Research/by-keyword"
.venv/Scripts/python.exe scripts/build_paper_index.py --outdir "C:/Users/230016/OneDrive/Obsidian/Yuhan/Research/claude_paper"
```

## 4. 보고 (한 번만, 간결히)
- triage 점수 분포(특히 ≥4), 한글요약 처리 건수, 인덱스 그룹별 편수.
- score 5점 신규가 있으면 제목을 짚고, **본문 노트(/summarize)는 수동 대상**임을 한 줄 안내(루틴에서 자동 생성하지 않음).
