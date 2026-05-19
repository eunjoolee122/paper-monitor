# paper-monitor

Drug discovery (small molecule generation + lead optimization) 분야 신규 논문을 자동으로
수집·분류·요약하기 위한 Claude Code 워크플로우.

## 아키텍처

```
queries.yaml ──┐
config.yaml  ──┤
               ▼
┌──────────────────────┐    ┌─────────────┐    ┌──────────────────┐
│ fetcher (arxiv,      │ →  │  SQLite     │ →  │ Claude triage    │
│ chemrxiv, europepmc) │    │ papers.db   │    │ (abstract 채점)  │
└──────────────────────┘    └─────────────┘    └────────┬─────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────┐
                                              │ Claude summarize │
                                              │ (PDF → markdown) │
                                              └────────┬─────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │ Obsidian vault   │
                                              └──────────────────┘
```

- 메타데이터 수집·중복제거는 **Python 스크립트**가 처리 (값싸고 결정적)
- 채점·요약은 **Claude Code 슬래시 커맨드**가 처리 (판단력 필요)

## 셋업 (1회)

```bash
# 1. 의존성 설치
python -m venv .venv
source .venv/bin/activate     # Windows는 .venv\Scripts\activate
pip install -r requirements.txt

# 2. config.yaml 열어서 Obsidian vault 경로 수정
#    obsidian_notes_dir: "/Users/yourname/ObsidianVault/Papers"

# 3. queries.yaml은 이미 small molecule generation / lead opt 중심으로 세팅됨.
#    필요하면 키워드 추가·삭제.

# 4. DB 초기화 + 2년치 백필 (10~30분 소요, API rate limit 때문)
python scripts/backfill.py
```

백필이 끝나면 `data/papers.sqlite`에 메타데이터가 들어가 있음. `notes/`는 비어있음 (요약 전).

## 일상 워크플로우 (Claude Code)

이 디렉토리에서 `claude` 명령으로 Claude Code를 띄우면 슬래시 커맨드를 쓸 수 있음.

```
/fetch              # 새 논문 가져오기
/triage             # 미평가 abstract 채점 (Claude가 판단)
/triage 50          # 50개까지 한 번에 채점
/summarize next 3   # 점수 높은 미요약 논문 3건 본문까지 읽고 노트 생성
/summarize arxiv:2401.12345   # 특정 논문 강제 요약
/digest             # 주간 다이제스트 (지난 7일)
/digest 14          # 지난 14일 다이제스트
```

## 자동화 (선택)

매일 새벽 fetch만 자동으로:

```bash
# crontab -e
0 6 * * * cd /path/to/paper-monitor && .venv/bin/python scripts/fetch_new.py >> data/fetch.log 2>&1
```

채점·요약은 사람이 Claude Code에서 트리거하는 게 비용·품질 면에서 나음 (배치로 자동화하면
미흡한 abstract도 점수만 매겨지고 결국 다시 봐야 함).

## 파일별 역할

| 파일 | 용도 |
|---|---|
| `queries.yaml` | 검색 키워드 정의 (자유 수정) |
| `config.yaml` | Obsidian 경로, DB 경로 등 (자유 수정) |
| `paper_monitor/fetchers/` | 소스별 API 클라이언트 |
| `paper_monitor/db.py` | SQLite 스키마·헬퍼 |
| `scripts/backfill.py` | 초기 2년치 수집 |
| `scripts/fetch_new.py` | 증분 수집 |
| `scripts/list_untriaged.py` | 미평가 논문 JSON 출력 (triage 슬래시 커맨드용) |
| `scripts/save_scores.py` | 채점 결과 DB 저장 |
| `scripts/get_paper.py` | 특정 논문 또는 요약 대기 N건 메타데이터 |
| `scripts/save_note.py` | 요약 markdown을 Obsidian에 저장 |
| `scripts/stats.py` | DB 통계 |
| `.claude/commands/` | Claude Code 슬래시 커맨드 정의 |
| `templates/paper_note.md` | 노트 템플릿 (참고용) |

## 키워드 튜닝 팁

1. 처음 백필 후 `/triage`를 한 번 돌려보면 노이즈가 얼마나 들어왔는지 보임.
2. 자주 노이즈로 잡히는 토픽은 `queries.yaml`의 `exclude_keywords`에 추가.
3. 너무 적게 잡히면 `core_keywords` 늘리거나 `arxiv_categories`에 `cs.AI` 추가.
4. Triage 프롬프트(`.claude/commands/triage.md`)는 실제 사용해보면서 본인 판단 기준에
   맞게 다듬기. Few-shot 예시 (본인이 직접 라벨링한 5~10건)를 프롬프트에 박아두면
   품질이 확연히 올라감.

## 트러블슈팅

**arXiv 응답이 비어있음**: rate limit 걸렸을 수 있음. `fetchers/arxiv.py`의 `sleep_between`을 늘려보세요 (기본 3.5초).

**chemRxiv 검색 결과가 별로**: chemRxiv는 인덱스 품질이 인기 토픽에 편향됨. 너무 niche한
키워드는 결과가 적을 수 있음.

**Europe PMC에서 bioRxiv 논문이 안 잡힘**: 인덱싱 지연이 있음 (보통 1~2주). 최신 논문은
arXiv·chemRxiv가 더 빠를 수 있음.

**Claude Code에서 슬래시 커맨드가 안 보임**: 프로젝트 루트에서 `claude`를 띄웠는지 확인.
`.claude/commands/` 디렉토리가 cwd에 있어야 인식됨.
