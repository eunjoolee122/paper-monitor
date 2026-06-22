---
description: triage 통과(score>=threshold) 논문 abstract를 한글 2-3문장으로 요약해 DB에 저장
argument-hint: [limit, 기본 20]
allowed-tools: Bash(python:*)
---

triage 통과한 논문 중 한글 요약이 비어있는 것을 채우세요.

## 1단계: 대상 가져오기

```bash
python scripts/list_for_kr_summary.py --limit ${ARGUMENTS:-20}
```

출력은 JSON 배열. 각 논문에 `id`, `title`, `abstract`, `matched_keywords`, `score` 가 있음.

## 2단계: 한글 요약 작성 (논문당 2-3문장)

다음 3축을 모두 담아 한국어로 작성:

1. **문제**: 무엇을 풀려고 하는가 (1문장)
2. **방법**: 어떻게 푸는가 — 핵심 아이디어/기법 (1문장)
3. **결과/의의**: 왜 주목할 만한가 — 정량 결과 또는 baseline 대비 차별점 (1문장)

규칙:
- **3문장 이내**. 길게 쓰지 말 것. 인덱스에서 한눈에 스캔하는 용도.
- 도메인 전문 용어는 **한글-영문 병기**. 예: "분자 생성(molecular generation)", "결합 친화도(binding affinity)".
- 약어는 그대로 (SMILES, PDBbind, GNN 등).
- 의역 자유 — 어색한 직역보다 자연스러운 한국어 문장 우선.

## 3단계: 저장

JSON 배열을 stdin으로 `save_kr_summary.py`에 전달:

```bash
echo '[
  {"id":"arxiv:2605.12784","kr_summary":"SMILES 기반 LLM이 만드는 invalid 분자 문제를 RDKit 도구 호출로 보강한 ToolMol 프레임워크. 다목적 유전 알고리즘과 agentic LLM 연산자를 결합해 표적 단백질 3종에서 결합 친화도 10%+ 향상. 절대 결합 자유에너지(Absolute Binding Free Energy) 스코어에서 기존 대비 35%+ 우위."},
  ...
]' | python scripts/save_kr_summary.py
```

## 4단계: 요약 보고

처리한 건수와 대표 1~2건의 한글 요약을 보여주세요. 매우 흥미로운 것이 있으면 짚어주세요.

다음 단계: `/build-indexes` 로 Obsidian 인덱스 페이지 생성.
