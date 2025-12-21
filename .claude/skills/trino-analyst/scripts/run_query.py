#!/usr/bin/env python
"""Trino 쿼리 실행 스크립트"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import trino
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Trino 쿼리 실행")
    parser.add_argument("--query", "-q", required=True, help="실행할 SQL 쿼리")
    parser.add_argument(
        "--format",
        "-f",
        choices=["csv", "json", "markdown"],
        default="markdown",
        help="출력 형식 (default: markdown)",
    )
    parser.add_argument("--limit", "-l", type=int, default=None, help="결과 행 수 제한")
    parser.add_argument("--output", "-o", type=str, default=None, help="결과를 저장할 파일 경로")
    args = parser.parse_args()

    # 환경변수 검증
    required_vars = ["TRINO_HOST", "TRINO_PORT", "TRINO_USER", "TRINO_PASSWORD"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Please set them in .env file", file=sys.stderr)
        sys.exit(1)

    query = args.query
    if args.limit and "LIMIT" not in query.upper():
        query = f"{query.rstrip(';')} LIMIT {args.limit}"

    try:
        # Trino 연결 설정
        conn = trino.dbapi.connect(
            host=os.getenv("TRINO_HOST"),
            port=int(os.getenv("TRINO_PORT")),
            user=os.getenv("TRINO_USER"),
            http_scheme="https",
            auth=trino.auth.BasicAuthentication(
                os.getenv("TRINO_USER"), os.getenv("TRINO_PASSWORD")
            ),
        )

        # 쿼리 실행 및 DataFrame 변환
        df = pd.read_sql(query, conn)
        conn.close()

        if args.format == "csv":
            output = df.to_csv(index=False)
        elif args.format == "json":
            output = df.to_json(orient="records", force_ascii=False, indent=2)
        else:  # markdown
            output = df.to_markdown(index=False)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            print(f"결과가 {args.output}에 저장되었습니다. ({len(df)}행)")
        else:
            print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
