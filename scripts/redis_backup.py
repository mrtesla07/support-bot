#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from environs import Env

DEFAULT_PREFIX = "support-bot"
DEFAULT_OUTPUT_DIR = Path("backups")
DEFAULT_REDIS_CLI = "redis-cli"
DEFAULT_CHECK_RDB = "redis-check-rdb"
DEFAULT_DATA_DIR = Path("redis/data")


@dataclass(frozen=True)
class RedisConnection:
    host: str
    port: int
    db: int
    password: str | None = None


def load_connection() -> RedisConnection:
    env = Env()
    env.read_env()
    return RedisConnection(
        host=env.str("REDIS_HOST", "localhost"),
        port=env.int("REDIS_PORT", 6379),
        db=env.int("REDIS_DB", 0),
        password=env.str("REDIS_PASSWORD", default="") or None,
    )


def resolve_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Не найден исполняемый файл '{name}'. Добавьте его в PATH или укажите флагом.")
    return path


def build_filename(prefix: str, compress: bool) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = ".rdb.gz" if compress else ".rdb"
    return f"{prefix}-{timestamp}{suffix}"


def default_output_path(directory: Path, prefix: str, compress: bool) -> Path:
    return directory / build_filename(prefix, compress)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def run_redis_dump(
    *,
    executable: str,
    connection: RedisConnection,
    target: Path,
) -> None:
    env = os.environ.copy()
    if connection.password:
        env["REDISCLI_AUTH"] = connection.password
    elif "REDISCLI_AUTH" in env:
        env.pop("REDISCLI_AUTH")

    cmd = [
        executable,
        "-h",
        connection.host,
        "-p",
        str(connection.port),
        "-n",
        str(connection.db),
        "--rdb",
        str(target),
    ]
    subprocess.run(cmd, check=True, env=env)


def compress_file(source: Path, destination: Path) -> None:
    with source.open("rb") as src, gzip.open(destination, "wb") as dst:
        shutil.copyfileobj(src, dst)
    source.unlink()


def write_checksum(source: Path) -> Path:
    digest = hashlib.sha256()
    with source.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum_path = source.with_name(f"{source.name}.sha256")
    checksum_path.write_text(f"{digest.hexdigest()}  {source.name}\n", encoding="utf-8")
    return checksum_path


def collect_backups(directory: Path, prefix: str, suffix: str) -> list[Path]:
    def has_suffix(path: Path) -> bool:
        return "".join(path.suffixes) == suffix

    return sorted(
        [
            file
            for file in directory.iterdir()
            if file.is_file() and file.name.startswith(f"{prefix}-") and has_suffix(file)
        ],
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )


def prune_backups(directory: Path, prefix: str, suffix: str, keep: int) -> list[Path]:
    removed: list[Path] = []
    backups = collect_backups(directory, prefix, suffix)
    for candidate in backups[keep:]:
        candidate.unlink(missing_ok=True)
        checksum = candidate.with_name(f"{candidate.name}.sha256")
        if checksum.exists():
            checksum.unlink()
        removed.append(candidate)
    return removed


def verify_rdb(executable: str, target: Path) -> None:
    subprocess.run([executable, str(target)], check=True)


def backup_command(args: argparse.Namespace) -> None:
    connection = load_connection()
    redis_cli = resolve_binary(args.redis_cli)
    output_path: Path
    if args.output:
        output_path = args.output
    else:
        output_path = default_output_path(args.directory, args.prefix, args.compress)

    tmp_target = output_path
    if args.compress:
        tmp_target = output_path.with_name(f"{output_path.name}.tmp")

    ensure_parent(tmp_target)
    if tmp_target.exists() and not args.force:
        raise RuntimeError(f"Файл {tmp_target} уже существует. Укажите --force для перезаписи.")

    print(f"Создаю дамп Redis в {tmp_target}...")
    run_redis_dump(executable=redis_cli, connection=connection, target=tmp_target)

    if args.compress:
        ensure_parent(output_path)
        print(f"Сжимаю дамп в {output_path}...")
        compress_file(tmp_target, output_path)
    else:
        output_path = tmp_target

    if args.verify:
        checker = resolve_binary(args.redis_check_rdb)
        print("Проверяю целостность через redis-check-rdb...")
        verify_rdb(checker, output_path)

    checksum_path = None
    if args.checksum:
        checksum_path = write_checksum(output_path)
        print(f"SHA256 сохранён в {checksum_path}")

    if args.keep and not args.output:
        suffix = ".rdb.gz" if args.compress else ".rdb"
        removed = prune_backups(output_path.parent, args.prefix, suffix, args.keep)
        if removed:
            print("Удалены старые бэкапы:")
            for item in removed:
                print(f"  - {item}")

    print(f"Готово. Итоговый файл: {output_path}")
    if checksum_path:
        print(f"Контрольная сумма: {checksum_path}")


def restore_command(args: argparse.Namespace) -> None:
    source = args.input
    if not source.exists():
        raise RuntimeError(f"Файл {source} не найден.")

    data_dir = args.data_dir
    target = data_dir / "dump.rdb"
    ensure_parent(target)

    if not args.yes:
        answer = input(
            "Redis должен быть остановлен. Продолжить копирование бэкапа в data-директорию? [y/N]: "
        ).strip()
        if answer.lower() not in {"y", "yes", "д", "да"}:
            print("Операция отменена.")
            return

    if target.exists() and not args.force:
        raise RuntimeError(
            f"Файл {target} уже существует. Используйте --force для перезаписи или переместите его вручную."
        )

    tmp_target = target.with_suffix(".tmp")
    if source.suffix == ".gz":
        print(f"Распаковываю {source}...")
        with gzip.open(source, "rb") as src, tmp_target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    else:
        shutil.copyfile(source, tmp_target)

    tmp_target.replace(target)
    print(f"Файл {target} готов. Запустите Redis, используя этот dump.rdb.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Полный бэкап Redis в формате RDB.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="Создать RDB-дамп.")
    backup.add_argument("--output", type=Path, help="Полный путь до файла (если не задан, используется --dir и --prefix).")
    backup.add_argument(
        "--dir",
        dest="directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Каталог, куда складывать бэкапы (по умолчанию ./backups).",
    )
    backup.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help="Префикс имени файла (по умолчанию support-bot).",
    )
    backup.add_argument(
        "--redis-cli",
        default=DEFAULT_REDIS_CLI,
        help="Путь к redis-cli (по умолчанию ищется в PATH).",
    )
    backup.add_argument(
        "--redis-check-rdb",
        default=DEFAULT_CHECK_RDB,
        help="Путь к redis-check-rdb для проверки (--verify).",
    )
    backup.add_argument(
        "--compress",
        action="store_true",
        help="Сохранять дамп в виде gzip (.rdb.gz).",
    )
    backup.add_argument(
        "--checksum",
        action="store_true",
        help="Сохранять SHA256 рядом с файлом.",
    )
    backup.add_argument(
        "--keep",
        type=int,
        default=0,
        help="Оставлять только N последних бэкапов (работает при автоматическом имени).",
    )
    backup.add_argument(
        "--verify",
        action="store_true",
        help="Запустить redis-check-rdb после создания дампа.",
    )
    backup.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующий файл.",
    )
    backup.set_defaults(func=backup_command)

    restore = subparsers.add_parser(
        "restore",
        help="Скопировать RDB-файл в data-директорию Redis (Redis должен быть остановлен).",
    )
    restore.add_argument("input", type=Path, help="Путь к файлу бэкапа (.rdb или .rdb.gz).")
    restore.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Каталог, в котором Redis ожидает dump.rdb (по умолчанию ./redis/data).",
    )
    restore.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать dump.rdb, даже если он существует.",
    )
    restore.add_argument(
        "--yes",
        action="store_true",
        help="Пропустить интерактивное подтверждение.",
    )
    restore.set_defaults(func=restore_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
