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

신약개발 도메인 관점에서 다음 구조로 markdown 작성. **Obsidian용**이므로 frontmatter, 태그, wikilink 적극 활용.

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

# <논문 제목>

> **한 줄 요약**: <트윗 길이로 핵심 한 줄>

## 문제 정의
무엇을 풀려고 하는가? 기존 접근의 한계는?

## 핵심 아이디어
새로운 방법의 본질을 3~5문장으로. 수식보다 직관 위주.

## 방법
- 입력 / 출력 표현
- 아키텍처 / 알고리즘 핵심
- 학습 데이터·objective
- 추론 시 절차

## 주요 결과
- 벤치마크: <어떤 데이터셋·메트릭>
- 핵심 수치: 표 또는 글머리표로 (이전 SOTA 대비 얼마나)
- ablation에서 가장 의미있는 발견

## 한계
저자가 명시한 한계 + 내가 보기에 추가되는 한계.

## 본인 플랫폼과의 연결
- 통합 가능성: 어떤 컴포넌트에 어떻게 붙일 수 있나
- 비교 대상: 본인 플랫폼의 어떤 부분의 베이스라인이 될 수 있나
- 재현 우선순위: 높음 / 중간 / 낮음 + 이유

## 관련 자료
- 코드: <github 링크 또는 "없음">
- 데이터: <링크 또는 "없음">
- 모델 가중치: <링크 또는 "없음">
- 관련 논문: [[다른노트]] 형식으로 (있으면)

## 인용
\`\`\`bibtex
<bibtex가 있으면 여기, 없으면 비워둠>
\`\`\`
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
