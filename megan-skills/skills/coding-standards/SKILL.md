# Coding Standards Skill
---
name: coding-standards
description: |
  Project-wide coding standards for Python/SQL development.
  Auto-apply when writing or modifying code.
---

# Coding Standards - Commerce Data Engineering Team

## 🚨 필수 준수 사항

### 1. Pre-commit 검증 (최우선)
```bash
pre-commit run --all-files --show-diff-on-failure
```

### 2. TDD (Test-Driven Development)
```
1. 테스트 작성 (Red)
2. 최소 구현 (Green)
3. 리팩토링 (Refactor)
```

## 📝 Python 코딩 스타일

### Type Hints (필수)
```python
from typing import Dict, Any, Optional, List

def process_data(
    products: List[Dict[str, Any]],
    batch_id: str,
    threshold: float = 0.0
) -> pd.DataFrame:
    """처리된 데이터를 반환합니다."""
    pass
```

### Docstrings (Google Style)
```python
def calculate_score(value: int, weight: float = 0.7) -> float:
    """
    스코어를 계산합니다.

    Args:
        value: 입력 값
        weight: 가중치 (0.0~1.0)

    Returns:
        계산된 스코어

    Raises:
        ValueError: weight가 범위를 벗어날 경우
    """
    pass
```

### Import 순서 (isort)
```python
# 1. Standard library
import os
from typing import Any, Dict

# 2. Third-party
import pandas as pd
from elasticsearch import Elasticsearch

# 3. Local
from src.app.utils import get_logger
```

## 🗄️ SQL 쿼리 스타일

### CTE 사용 (복잡한 쿼리)
```sql
WITH recent_orders AS (
    SELECT product_id, COUNT(*) AS order_count
    FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY product_id
)
SELECT * FROM recent_orders;
```

## ✅ Code Review Checklist
```bash
pre-commit run --all-files
pytest tests/ -v --cov=.
```

- [ ] Type hints
- [ ] Docstrings
- [ ] Pre-commit 통과
- [ ] Tests 작성
