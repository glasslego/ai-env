# TDD Workflow Reference

## Red → Green → Refactor 사이클

```
Step 1 (Red):    테스트 작성 → 실행 → 실패 확인
Step 2 (Green):  최소 구현 → 테스트 통과
Step 3 (Refactor): 코드 정리 → 테스트 재통과 확인
```

## 테스트 작성 가이드

### 네이밍 컨벤션

```python
def test_{feature}_{condition}_{expected_result}():
    # 예시
    def test_login_valid_credentials_returns_token():
    def test_login_invalid_password_raises_401():
    def test_search_empty_query_returns_empty_list():
```

### 구조 (AAA 패턴)

```python
def test_example():
    # Arrange — 준비
    user = create_test_user()

    # Act — 실행
    result = login(user.email, user.password)

    # Assert — 검증
    assert result.token is not None
    assert result.status == "authenticated"
```

### Mock/Stub 가이드

```python
# 외부 API
@patch("app.services.payment.PaymentGateway.charge")
def test_checkout(mock_charge):
    mock_charge.return_value = PaymentResult(success=True)
    ...

# DB (in-memory SQLite)
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    ...
```

## 아키텍처 패턴별 코드 배치

### 3-Layer (Endpoint → Service → Repository)

```
변경 대상 판별:
  DB 모델/쿼리 변경? → repository 먼저
  비즈니스 로직? → service
  API 인터페이스? → endpoint + schema
  전부? → repository → service → endpoint 순서
```

### 테스트 배치

```
tests/
├── unit/           # Service/Repository 단위 테스트
├── integration/    # API 엔드포인트 통합 테스트
└── conftest.py     # 공유 fixture
```
