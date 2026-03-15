# Gift Ranking Index Schema
## index
- gift_product_ranking

## 주요 필드
### 메타 정보
- batch_id (keyword) - 배치 ID
- product_id (long) - 상품 ID
- name (keyword) - 상품명
- brand_id (long) - 브랜드 ID
- brand_name (keyword) - 브랜드명
- price (long) - 가격
- type (keyword) - 상품 타입
- fs_updated_at (date) - Feature Store 업데이트 시각
- standard_category_large_code (keyword) - 표준 카테고리 대분류 코드
- standard_category_large_name (keyword) - 표준 카테고리 대분류명
- standard_category_medium_code (keyword) - 표준 카테고리 중분류 코드
- standard_category_medium_name (keyword) - 표준 카테고리 중분류명

### 클릭 스코어
- click_total_score (double) - 클릭 전체 스코어
- click_trending_score (double) - 클릭 트렌딩 스코어
- click_user_count_4h (double) - 4시간 클릭 유저 수
- click_user_count_1d (double) - 1일 클릭 유저 수
- click_user_count_7d (double) - 7일 클릭 유저 수
- click_user_count_30d (double) - 30일 클릭 유저 수

### 주문 스코어 (전체)
- order_total_score (double) - 주문 전체 스코어
- order_trending_score (double) - 주문 트렌딩 스코어
- order_user_count_4h (double) - 4시간 주문 유저 수
- order_user_count_1d (double) - 1일 주문 유저 수
- order_user_count_7d (double) - 7일 주문 유저 수
- order_user_count_30d (double) - 30일 주문 유저 수

### 주문 스코어 (선물)
- order_gift_total_score (double) - 선물 주문 전체 스코어
- order_gift_trending_score (double) - 선물 주문 트렌딩 스코어
- order_gift_user_count_4h (double) - 4시간 선물 주문 유저 수
- order_gift_user_count_1d (double) - 1일 선물 주문 유저 수
- order_gift_user_count_7d (double) - 7일 선물 주문 유저 수
- order_gift_user_count_30d (double) - 30일 선물 주문 유저 수

### 주문 스코어 (자가구매)
- order_self_purchase_total_score (double) - 자가구매 주문 전체 스코어
- order_self_purchase_trending_score (double) - 자가구매 주문 트렌딩 스코어
- order_self_purchase_user_count_4h (double) - 4시간 자가구매 주문 유저 수
- order_self_purchase_user_count_1d (double) - 1일 자가구매 주문 유저 수
- order_self_purchase_user_count_7d (double) - 7일 자가구매 주문 유저 수
- order_self_purchase_user_count_30d (double) - 30일 자가구매 주문 유저 수

### 위시 스코어
- wish_total_score (double) - 위시 전체 스코어
- wish_trending_score (double) - 위시 트렌딩 스코어
- wish_user_count_4h (double) - 4시간 위시 유저 수
- wish_user_count_1d (double) - 1일 위시 유저 수
- wish_user_count_7d (double) - 7일 위시 유저 수
- wish_user_count_30d (double) - 30일 위시 유저 수

### 리뷰 유저 수
- review_user_count_4h (double) - 4시간 리뷰 유저 수
- review_user_count_1d (double) - 1일 리뷰 유저 수
- review_user_count_7d (double) - 7일 리뷰 유저 수
- review_user_count_30d (double) - 30일 리뷰 유저 수

---
# Epsilon Gift Product Index Schema

## index
- epsilon_gift_product_v1

## 주요 필드
- gift_product_id (keyword) - 상품 ID

### 스코어 (원본)
- score (long) - 통합 스코어
- gift_purchase_score (long) - 선물 구매 스코어
- self_purchase_score (long) - 자가 구매 스코어

### 스코어 (정규화)
- normalized_score (float) - 정규화된 통합 스코어
- normalized_gift_purchase_score (float) - 정규화된 선물 구매 스코어
- normalized_self_purchase_score (float) - 정규화된 자가 구매 스코어

---
# Promotion Builder Index Schema

## index
- kcai_integrated_gift_product

## 주요 필드
- product_id (keyword) - 상품 ID
- display_name (text) - 상품명
- brand_id (keyword) - 브랜드 ID
- brand_name (keyword) - 브랜드명
- status (long) - 상품 상태 (201: 정상 판매 가능한 상품)
- large_display_category_code (keyword) - 대분류 노출 카테고리 코드
- large_display_category_name (keyword) - 대분류 노출 카테고리명
- selling_price (long) - 판매가격
- self_purchase_score (long) - 자가구매 스코어
- gift_purchase_score (long) - 선물구매 스코어
- service_score (long) - 서비스 스코어
