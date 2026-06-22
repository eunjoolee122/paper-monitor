---
description: 한글 요약된 논문을 keyword별로 묶어 Obsidian markdown 인덱스 생성
argument-hint: [없음]
allowed-tools: Bash(python:*)
---

DB의 한글 요약 데이터를 읽어 keyword 그룹별 인덱스 페이지를 Obsidian에 생성합니다.

config의 `obsidian_notes_dir`는 repo 내부(`./notes`)라 실제 vault와 다름. 그래서
`--outdir`로 실제 Obsidian vault의 by-keyword 폴더를 직접 지정한다.

```bash
python scripts/build_keyword_indexes.py --outdir "C:/Users/230016/OneDrive/Obsidian/Yuhan/Research/by-keyword"
```

## 출력 확인

명령이 끝나면 (vault의 `Research/by-keyword/`):
- `_index.md` — 전체 그룹 목차
- `<group-slug>.md` — 6개 그룹별 페이지 (분자 생성 / 구조기반 설계 /
  스캐폴드·프래그먼트 / 리드 최적화 / 예측 / 합성·표현)

생성된 파일 수, 위치, 그룹별 편수, 논문 없는 그룹이 출력됨.
사용자에게 그 결과를 그대로 보여주세요.

Obsidian vault를 열면 `Research/by-keyword/` 폴더가 6개 그룹으로 정리되어 보입니다.

참고: 키워드→그룹 매핑은 `scripts/build_keyword_indexes.py`의 `KEYWORD_GROUPS`에
정의돼 있음. 묶음을 바꾸려면 거기만 수정하면 됨 (queries.yaml은 fetch용이라 그대로 둠).
