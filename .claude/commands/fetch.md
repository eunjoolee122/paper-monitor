---
description: 신규 논문 가져오기 (arXiv / chemRxiv / Europe PMC)
allowed-tools: Bash(python:*), Bash(uv:*)
---

증분 fetch를 실행해서 새 논문을 DB에 추가하세요.

```bash
python scripts/fetch_new.py
```

실행 결과를 보고:
1. 신규 건수를 알려주세요.
2. DB 통계도 같이 보여주세요: `python scripts/stats.py`
3. 신규 건이 있다면 사용자에게 `/triage`를 다음으로 실행할지 물어보세요.
