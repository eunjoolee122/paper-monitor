---
description: 미평가 논문 abstract들을 채점해서 DB에 저장
argument-hint: [limit, 기본 20]
allowed-tools: Bash(python:*)
---

미평가 논문 abstract를 읽고 신약개발 플랫폼 관점에서 채점하세요.

## 1단계: 채점 대상 가져오기

```bash
python scripts/list_untriaged.py --limit ${ARGUMENTS:-20}
```

출력은 JSON 배열입니다. 각 논문에 대해 abstract를 정독하세요.

## 2단계: 채점 기준 (0~5점, 정수)

본 사용자는 **small molecule generation + lead optimization** 중심의 AI 신약개발 플랫폼을 구축 중입니다. 다음 축을 모두 고려해서 종합 점수를 매기세요:

- **모달리티 일치 (필수)**: small molecule이 주 대상인가? 단백질/항체/RNA 중심이면 0~1점.
- **태스크 일치**: molecular generation, lead optimization, 또는 이걸 지원하는 predictor (binding affinity / ADMET / docking / synthesizability) 인가? 직접 관련이면 +2, 간접 관련이면 +1.
- **방법론 신선도**: 새로운 아이디어인가, 기존 베이스라인 살짝 튜닝인가? SOTA 갱신 / 새로운 패러다임이면 +1.
- **재현성·실용성**: 코드/데이터/모델 공개 명시되어 있나? 표준 벤치마크(PDBbind, MoleculeNet, GuacaMol, MOSES, DUD-E, CrossDocked2020 등) 사용? +1.
- **실험 검증**: wet-lab validation, 실제 분자 합성, 또는 잘 알려진 표적에 대한 평가? 있으면 +1. 순수 in silico toy task면 차감.
- **사용자 플랫폼과의 보완성**: 본인 플랫폼에 통합/벤치마크할 가치가 있어 보이는가?

**점수 가이드**:
- 5: 반드시 본문까지 읽고 가능하면 재현·통합 검토할 핵심 논문
- 4: 본문 읽을 가치 충분
- 3: 본문 훑어볼 만함
- 2: 제목만 기억해둠
- 1: 일단 스킵
- 0: 관련 없음 (exclude에서 안 잡힌 노이즈)

## 3단계: 결과 JSON으로 저장

각 논문에 대해 아래 형식의 JSON 배열을 만들어서 `save_scores.py`에 파이프하세요.
**reason은 한 줄(80자 이내), 한국어로** 작성하세요 — 왜 그 점수인지 핵심만.

```bash
echo '[
  {"id":"arxiv:2401.12345","score":4,"reason":"포켓 조건부 분자 생성, CrossDocked2020 벤치마크, 코드 공개"},
  {"id":"chemrxiv:xxxxx","score":2,"reason":"property prediction이지만 toy dataset만 사용"}
]' | python scripts/save_scores.py
```

## 4단계: 요약

채점이 끝나면 결과 요약을 보여주세요:
- 점수 분포 (4점 이상 몇 건, 3점 몇 건, 등)
- 점수 4~5인 논문의 제목과 한 줄 사유
- 다음 단계: `/summarize` 로 본문 요약 시작 안내
