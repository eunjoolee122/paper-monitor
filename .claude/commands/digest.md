---
description: 최근 처리한 논문들의 주간 다이제스트 생성
argument-hint: [days, 기본 7]
allowed-tools: Bash(python:*), Bash(sqlite3:*), Write
---

지난 N일간 새로 들어왔고/요약된 논문을 한 페이지로 정리해서 Obsidian에 저장.

## 1단계: 최근 활동 조회

`${ARGUMENTS:-7}`일 기준으로:

```bash
DAYS=${ARGUMENTS:-7}
DB=$(python -c "from paper_monitor.config import load_config; print(load_config()['db_path'])")
SINCE=$(date -u -d "-${DAYS} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${DAYS}d +%Y-%m-%dT%H:%M:%SZ)

# 새로 fetch된 것
sqlite3 -header -csv "$DB" "SELECT id, source, title, published_date, score, status FROM papers WHERE fetched_at > '$SINCE' ORDER BY score DESC NULLS LAST, published_date DESC"

# 이번 주기에 요약된 것
sqlite3 -header -csv "$DB" "SELECT id, title, note_path FROM papers WHERE summarized_at > '$SINCE'"
```

## 2단계: 다이제스트 markdown 작성

다음 구조로:

```markdown
---
title: "Paper Digest YYYY-MM-DD"
tags: [digest, drug-discovery]
period_days: <N>
---

# 📰 Paper Digest — <YYYY-MM-DD>

지난 <N>일 활동 요약.

## 통계
- 신규 수집: <건>
- 채점 완료: <건>
- 본문 요약 완료: <건>

## 🔥 4점 이상 (반드시 읽을 것)
- **<제목>** — <한 줄 사유> · [[<노트 파일명>]] (요약됨) 또는 (대기 중)
- ...

## 📌 3점 (훑어볼 만함)
- **<제목>** — <한 줄 사유>
- ...

## 🆕 이번 주기 새로 요약된 노트
- [[<note1>]]
- [[<note2>]]

## 트렌드 관찰
짧게: 어떤 키워드/방법론이 이번 주기에 많이 등장했는지.
```

## 3단계: Obsidian에 저장

```bash
NOTES_DIR=$(python -c "from paper_monitor.config import load_config; print(load_config()['obsidian_notes_dir'])")
DATE=$(date +%Y-%m-%d)
mkdir -p "$NOTES_DIR/digests"
# 위에서 작성한 markdown을 여기에 씀
```

저장 후 경로를 사용자에게 보여주고 끝.
