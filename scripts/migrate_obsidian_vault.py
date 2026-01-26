#!/usr/bin/env python3
"""Obsidian Vault 폴더 구조 마이그레이션 스크립트.

기존 Obsidian Vault와 Notion Import 폴더를 새로운 구조로 재정리합니다.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ObsidianVaultMigrator:
    """Obsidian Vault 마이그레이션 클래스."""

    def __init__(self, vault_path: str | Path, dry_run: bool = False):
        self.vault_path = Path(vault_path)
        self.notion_import = self.vault_path / "Notion Import"
        self.dry_run = dry_run
        self.stats = {
            "folders_created": 0,
            "folders_moved": 0,
            "files_moved": 0,
            "errors": [],
        }

        # 마이그레이션 매핑 정의
        self.migration_map = self._build_migration_map()

    def _build_migration_map(self) -> list[dict]:
        """마이그레이션 매핑 정의."""
        return [
            # === 현재 진행 업무 (최상위) ===
            {
                "src": self.vault_path / "01_랭킹업무정리",
                "dst": self.vault_path / "01_work_랭킹",
                "action": "rename",
            },
            {
                "src": self.vault_path / "02_CDE업무",
                "dst": self.vault_path / "02_work_CDE",
                "action": "rename",
            },
            # === 03_work (기타 업무) ===
            {
                "src": self.notion_import / "01__카카오_업무정리" / "#_커머스AI",
                "dst": self.vault_path / "03_work" / "커머스AI",
                "action": "move",
            },
            {
                "src": self.notion_import / "01__카카오_업무정리" / "#cactf",
                "dst": self.vault_path / "03_work" / "광고팀",
                "action": "move",
            },
            {
                "src": self.notion_import / "01__카카오_업무정리" / "#오픈링크팀",
                "dst": self.vault_path / "03_work" / "오픈링크팀",
                "action": "move",
            },
            {
                "src": self.notion_import / "01__카카오_업무정리" / "광고필독논문",
                "dst": self.vault_path / "03_work" / "광고필독논문",
                "action": "move",
            },
            {
                "src": self.notion_import / "지난 업무 (백업용)",
                "dst": self.vault_path / "03_work" / "지난업무",
                "action": "move",
            },
            # === 10_tech (기술) ===
            {
                "src": self.notion_import / "02_데이터기술",
                "dst": self.vault_path / "10_tech" / "data-engineering",
                "action": "move",
            },
            {
                "src": self.notion_import / "03_코딩" / "bash & vim",
                "dst": self.vault_path / "10_tech" / "coding" / "bash",
                "action": "move",
            },
            {
                "src": self.notion_import / "03_코딩" / "scala",
                "dst": self.vault_path / "10_tech" / "coding" / "scala",
                "action": "move",
            },
            {
                "src": self.notion_import / "03_코딩" / "tool & util",
                "dst": self.vault_path / "10_tech" / "coding" / "tools",
                "action": "move",
            },
            {
                "src": self.vault_path / "AI 도구 정리",
                "dst": self.vault_path / "10_tech" / "ai-tools",
                "action": "move",
            },
            {
                "src": self.vault_path / "기술정리",
                "dst": self.vault_path / "10_tech" / "기타",
                "action": "move",
            },
            # === 20_study (스터디) ===
            {
                "src": self.notion_import / "04_스터디" / "1_수학 & 통계 & 분석",
                "dst": self.vault_path / "20_study" / "math-stats",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "2_ML",
                "dst": self.vault_path / "20_study" / "ml",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "3_딥러닝",
                "dst": self.vault_path / "20_study" / "deep-learning",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "4_추천 & 검색",
                "dst": self.vault_path / "20_study" / "recsys",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "5_NLP & LLM",
                "dst": self.vault_path / "20_study" / "nlp-llm",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "A B 테스트",
                "dst": self.vault_path / "20_study" / "ab-test",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "강의_강필성교수님",
                "dst": self.vault_path / "20_study" / "courses" / "강필성교수님",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "강의_김성범교수님",
                "dst": self.vault_path / "20_study" / "courses" / "김성범교수님",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "혁펜하임_AI딥다이브",
                "dst": self.vault_path / "20_study" / "courses" / "혁펜하임",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "[2023]추천시스템 입문",
                "dst": self.vault_path / "20_study" / "courses" / "추천시스템입문",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "0_공부 계획 세워보기",
                "dst": self.vault_path / "20_study" / "계획",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "외부자료정리",
                "dst": self.vault_path / "20_study" / "외부자료",
                "action": "move",
            },
            {
                "src": self.notion_import / "04_스터디" / "캐글 및 그외 예제",
                "dst": self.vault_path / "20_study" / "kaggle",
                "action": "move",
            },
            # === 30_career (커리어) ===
            {
                "src": self.notion_import / "기술관련" / "면접 준비",
                "dst": self.vault_path / "30_career" / "interview",
                "action": "move",
            },
            {
                "src": self.notion_import / "기술관련" / "코테 준비(SQL 만)",
                "dst": self.vault_path / "30_career" / "coding-test" / "sql",
                "action": "move",
            },
            {
                "src": self.notion_import / "기술관련" / "코테 준비(SQL 외)",
                "dst": self.vault_path / "30_career" / "coding-test" / "algorithm",
                "action": "move",
            },
            # === 40_개인 ===
            {
                "src": self.notion_import / "남종개인" / "2) 남정잡다",
                "dst": self.vault_path / "40_개인",
                "action": "move",
            },
            {
                "src": self.vault_path / "개인정보",
                "dst": self.vault_path / "40_개인" / "개인정보",
                "action": "move",
            },
            {
                "src": self.notion_import / "남종개인" / "1) TODO",
                "dst": self.vault_path / "40_개인" / "TODO",
                "action": "move",
            },
            {
                "src": self.notion_import / "남종개인" / "가자 하와이",
                "dst": self.vault_path / "40_개인" / "여행",
                "action": "move",
            },
            # === 41_재테크 ===
            {
                "src": self.notion_import / "재테크",
                "dst": self.vault_path / "41_재테크",
                "action": "move",
            },
            {
                "src": self.notion_import / "남종개인" / "3) 재테크",
                "dst": self.vault_path / "41_재테크" / "노션백업",
                "action": "move",
            },
            # === 42_독서노트 ===
            {
                "src": self.notion_import / "독서노트",
                "dst": self.vault_path / "42_독서노트",
                "action": "move",
            },
            # === 50_blog ===
            {
                "src": self.vault_path / "티스토리용",
                "dst": self.vault_path / "50_blog",
                "action": "rename",
            },
            # === attachments ===
            {
                "src": self.notion_import / "attachments",
                "dst": self.vault_path / "attachments",
                "action": "merge",
            },
            # === 기타 정리 ===
            {
                "src": self.vault_path / "할일정리",
                "dst": self.vault_path / "00_inbox" / "할일정리",
                "action": "move",
            },
            {
                "src": self.vault_path / "TODO 자동화",
                "dst": self.vault_path / "00_inbox" / "TODO자동화",
                "action": "move",
            },
        ]

    def migrate(self) -> dict:
        """마이그레이션 실행."""
        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}마이그레이션 시작: {self.vault_path}")

        # 백업 생성 (dry_run이 아닐 때만)
        if not self.dry_run:
            self._create_backup_marker()

        # 매핑 순서대로 처리
        for mapping in self.migration_map:
            try:
                self._process_mapping(mapping)
            except Exception as e:
                logger.error(f"Error processing {mapping['src']}: {e}")
                self.stats["errors"].append(
                    {
                        "src": str(mapping["src"]),
                        "error": str(e),
                    }
                )

        # 루트에 남은 파일들 정리
        self._cleanup_root_files()

        # 빈 폴더 정리
        self._cleanup_empty_folders()

        logger.info(f"마이그레이션 완료: {self.stats}")
        return self.stats

    def _create_backup_marker(self) -> None:
        """백업 마커 파일 생성."""
        marker_file = (
            self.vault_path / f".migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        marker_file.write_text(f"Migration started at {datetime.now().isoformat()}\n")
        logger.info(f"백업 마커 생성: {marker_file.name}")

    def _process_mapping(self, mapping: dict) -> None:
        """개별 매핑 처리."""
        src = mapping["src"]
        dst = mapping["dst"]
        action = mapping["action"]

        if not src.exists():
            logger.warning(f"소스 없음 (스킵): {src}")
            return

        logger.info(f"{action.upper()}: {src.name} -> {dst}")

        if self.dry_run:
            return

        # 대상 부모 폴더 생성
        dst.parent.mkdir(parents=True, exist_ok=True)
        self.stats["folders_created"] += 1

        if action == "rename":
            src.rename(dst)
            self.stats["folders_moved"] += 1

        elif action == "move":
            if dst.exists():
                # 대상이 이미 존재하면 내용 병합
                self._merge_folders(src, dst)
            else:
                shutil.move(str(src), str(dst))
            self.stats["folders_moved"] += 1

        elif action == "merge":
            self._merge_folders(src, dst)
            self.stats["folders_moved"] += 1

    def _merge_folders(self, src: Path, dst: Path) -> None:
        """폴더 내용 병합."""
        dst.mkdir(parents=True, exist_ok=True)

        for item in src.iterdir():
            target = dst / item.name
            if item.is_file():
                if target.exists():
                    # 중복 파일은 이름 변경
                    base = item.stem
                    ext = item.suffix
                    counter = 1
                    while target.exists():
                        target = dst / f"{base}_{counter}{ext}"
                        counter += 1
                shutil.move(str(item), str(target))
                self.stats["files_moved"] += 1
            elif item.is_dir():
                if target.exists():
                    self._merge_folders(item, target)
                else:
                    shutil.move(str(item), str(target))

    def _cleanup_root_files(self) -> None:
        """루트에 남은 개별 파일들 정리."""
        root_files = [
            ("Untitled.md", self.vault_path / "00_inbox"),
            ("Welcome.md", self.vault_path / "00_inbox"),
            ("chap3 hdfs.md", self.vault_path / "10_tech" / "data-engineering"),
            (
                "flink 에서 만든 테이블 --> 스냅샷 테이블 만들때 timestamp 이슈.md",
                self.vault_path / "10_tech" / "data-engineering",
            ),
        ]

        for filename, target_dir in root_files:
            src = self.vault_path / filename
            if src.exists():
                logger.info(f"파일 이동: {filename} -> {target_dir.name}/")
                if not self.dry_run:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target_dir / filename))
                    self.stats["files_moved"] += 1

        # Notion Import 루트 파일들
        notion_root_files = [
            "megan.won.md",
            "open ai key.md",
            "기술관련.md",
            "남정.md",
            "남종개인.md",
            "지난 업무 (백업용).md",
        ]

        for filename in notion_root_files:
            src = self.notion_import / filename
            if src.exists():
                target = self.vault_path / "99_archive" / "notion_root"
                logger.info(f"Notion 루트 파일 아카이브: {filename}")
                if not self.dry_run:
                    target.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target / filename))
                    self.stats["files_moved"] += 1

    def _cleanup_empty_folders(self) -> None:
        """빈 폴더 정리."""
        # Notion Import 하위 빈 폴더 제거
        folders_to_check = [
            self.notion_import / "01__카카오_업무정리",
            self.notion_import / "02_데이터기술",
            self.notion_import / "03_코딩",
            self.notion_import / "04_스터디",
            self.notion_import / "기술관련",
            self.notion_import / "남종개인",
            self.notion_import / "남정",
            self.notion_import / "megan won",
            self.notion_import / "People",
            self.notion_import,
        ]

        for folder in folders_to_check:
            if folder.exists():
                self._remove_empty_recursive(folder)

    def _remove_empty_recursive(self, path: Path) -> bool:
        """빈 폴더 재귀적 제거. 제거되면 True 반환."""
        if not path.is_dir():
            return False

        # 하위 항목 처리
        for item in list(path.iterdir()):
            if item.is_dir():
                self._remove_empty_recursive(item)

        # .obsidian, .DS_Store 무시하고 비어있는지 확인
        remaining = [f for f in path.iterdir() if f.name not in [".DS_Store", ".obsidian"]]

        if not remaining:
            logger.info(f"빈 폴더 제거: {path}")
            if not self.dry_run:
                # .DS_Store 먼저 제거
                ds_store = path / ".DS_Store"
                if ds_store.exists():
                    ds_store.unlink()
                # .obsidian 제거
                obsidian = path / ".obsidian"
                if obsidian.exists():
                    shutil.rmtree(obsidian)
                path.rmdir()
            return True
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Obsidian Vault 폴더 구조 마이그레이션")
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path("/Users/megan/Documents/Obsidian Vault"),
        help="Obsidian Vault 경로",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 변경 없이 미리보기만 실행",
    )

    args = parser.parse_args()

    migrator = ObsidianVaultMigrator(args.vault, dry_run=args.dry_run)
    stats = migrator.migrate()

    print("\n" + "=" * 50)
    print("📊 마이그레이션 결과")
    print("=" * 50)
    print(f"  📁 폴더 생성: {stats['folders_created']}")
    print(f"  📂 폴더 이동: {stats['folders_moved']}")
    print(f"  📄 파일 이동: {stats['files_moved']}")
    if stats["errors"]:
        print(f"  ❌ 오류: {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            print(f"     - {err['src']}: {err['error']}")
    print("=" * 50)

    if args.dry_run:
        print("\n🔍 [DRY RUN] 실제 변경 없음. --dry-run 제거 후 다시 실행하세요.")
    else:
        print("\n✨ 마이그레이션 완료! Obsidian을 재시작하세요.")


if __name__ == "__main__":
    main()
