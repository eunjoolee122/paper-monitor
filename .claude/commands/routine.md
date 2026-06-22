---
description: 주간 자동 파이프라인 — 신규 fetch → triage 채점 → 한글요약 → Obsidian 인덱스 재생성
argument-hint: [없음]
allowed-tools: Bash(python:*), Bash(echo:*), Bash(cat:*), Read, Write
---

paper-monitor 주간 무인 루틴. 아래 단계를 **순서대로** 수행하고, 마지막에 한 번만 요약 보고하라.
중간에 사용자에게 질문하지 말 것(무인 실행). 각 단계에서 처리할 게 0건이면 조용히 다음으로 넘어가라.

## 1. 신규 논문 fetch
```bash
python scripts/fetch_new.py
```
- 마지막 fetch 이후 신규만 들어온다(arXiv/chemRxiv/Europe PMC). 신규 0건이면 2~3단계는 사실상 빈 작업이 되니 그대로 진행해도 됨.

## 2. Triage 채점 (미평가 전부)
```bash
python scripts/list_untriaged.py --limit 500
```
- 출력된 미평가 논문(status='new')의 abstract를 **`.claude/commands/triage.md`의 루브릭**(small molecule generation + lead optimization 플랫폼 관점, 0~5점)으로 채점.
- 결과 JSON 배열(`[{"id","score","reason"}]`, reason은 한국어 한 줄)을 `python scripts/save_scores.py`에 stdin으로 전달해 저장.
- 미평가가 0건이면 스킵.

## 3. 한글 요약 (score>=threshold 미요약 전부)
```bash
python scripts/list_for_kr_summary.py --limit 500
```
- 출력된 논문 각각을 **`.claude/commands/kr-summarize.md` 규칙**(문제·방법·결과 3축, 3문장 이내, 용어 한영 병기)으로 한글 요약.
- 결과 JSON 배열(`[{"id","kr_summary"}]`)을 `python scripts/save_kr_summary.py`에 stdin으로 전달해 저장.
- 대상이 0건이면 스킵.

## 4. Obsidian 인덱스 재생성 (실제 vault)
```bash
python scripts/build_keyword_indexes.py --outdir "C:/Users/230016/OneDrive/Obsidian/Yuhan/Research/by-keyword"
python scripts/build_paper_index.py --outdir "C:/Users/230016/OneDrive/Obsidian/Yuhan/Research/claude_paper"
```

## 5. 보고 (한 번만, 간결히)
- 신규 fetch 건수, triage 점수 분포(특히 ≥4), 한글요약 처리 건수, 인덱스 그룹별 편수.
- score 5점 신규가 있으면 제목을 짚고, **본문 노트(/summarize)는 수동 대상**임을 한 줄로 안내(루틴에서는 자동 생성하지 않음).
