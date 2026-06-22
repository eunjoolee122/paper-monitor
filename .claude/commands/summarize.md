---
description: 점수 높은 논문 본문을 읽고 Obsidian용 markdown 노트 생성
argument-hint: [paper_id 또는 "next N" — 예: "arxiv:2401.12345" 또는 "next 3"]
allowed-tools: Bash(python:*), Bash(curl:*), Bash(mkdir:*), Read, Write
---

논문 본문을 읽고 구조화된 노트를 Obsidian vault에 저장하세요.

## 1단계: 대상 결정

`$ARGUMENTS`를 보고 처리:

- 비어있거나 `next N` 형태면: `python scripts/get_paper.py --next N` (기본 N=1)
- 그 외엔 ID로 간주: `python scripts/get_paper.py --id $ARGUMENTS`

JSON 결과에서 각 논문의 `pdf_url`, `title`, `id`, `landing_url`을 사용하세요.

## 2단계: PDF 다운로드 후 읽기

각 논문에 대해:

```bash
mkdir -p /tmp/paper-monitor
curl -L -o /tmp/paper-monitor/<safe-id>.pdf "<pdf_url>"
```

다운로드한 PDF를 Read 도구로 읽으세요. PDF가 너무 크거나 다운로드 실패면 abstract와 landing_url 기반으로만 작성하되 그 사실을 노트 첫 줄에 명시.

## 3단계: 노트 작성 (아래 템플릿 엄수)

**간결·스캔 우선.** 장황한 prose 금지. 요약 표 + 핵심 수치 **마크다운 표** 중심으로, 전체 ~45~60줄.
한국어, 도메인 용어 한글-영문 병기(예: 결합친화도(binding affinity)), 약어(SMILES/QED/Vina/GRPO 등) 유지.
**그림은 이미지 임베드하지 말고 텍스트 1~2줄로 설명**(렌더 도구 없음). 표는 논문 Table에서 핵심 1개를 마크다운 표로 옮긴다.

```markdown
---
title: "<논문 제목>"
authors: [<authors>]
source: <source>
published: <published_date>
score: <score>
id: <id>
url: <landing_url>
pdf: <pdf_url>
tags: [paper, drug-discovery, <세부 태그>]
read_at: <오늘 날짜>
---

# <짧은 제목 (약칭)>

> **TL;DR**: <트윗 길이 핵심 한 줄>

| 항목 | 내용 |
|---|---|
| **문제** | 무엇을, 기존 한계 |
| **방법** | 핵심 아이디어 한 줄 |
| **결과** | 핵심 성과 한 줄 |
| **한계** | 저자+본인 관점 |
| **재현 우선순위** | 높음/중간/낮음 — 이유 |

## 핵심 수치
<논문 Table에서 가장 중요한 표를 마크다운 표로. 정량 수치 부족하면 3~5 불릿. 이전 SOTA 대비 명시>

## 방법 (핵심만)
- 입력/출력 표현, 아키텍처·알고리즘 핵심, 학습 objective, 추론 절차를 3~5 불릿

## 핵심 그림 (텍스트)
- **Figure N**: 무엇을 보여주는지 1줄 (보통 방법/아키텍처 개요). 번호 모르면 개념만.

## 플랫폼 연결
- **통합**: 어떤 컴포넌트에 어떻게
- **비교**: 어떤 부분의 baseline

## 자료
코드: <링크 또는 "본문 명시 없음"> · 데이터: <…> · 모델: <…> · 관련: [[다른노트]]
```

## 4단계: 노트 저장

작성한 마크다운을 임시 파일에 쓴 다음 save_note.py로 저장:

```bash
cat > /tmp/paper-monitor/note.md << 'EOF'
<위에서 작성한 마크다운>
EOF

python scripts/save_note.py --id <paper_id> --file /tmp/paper-monitor/note.md
```

여러 논문 처리할 땐 각각 반복.

## 5단계: 보고

처리한 논문마다 한 줄로 보고 (제목 + 저장 경로 + 통합 우선순위).
