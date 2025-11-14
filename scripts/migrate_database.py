#!/usr/bin/env python3
"""
資料庫 Migration 工具
執行資料庫結構變更
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime


def read_migration_file(migration_path: str) -> str:
    """
    讀取 migration SQL 檔案

    Args:
        migration_path: Migration 檔案路徑

    Returns:
        SQL 內容
    """
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"✗ 讀取 migration 檔案失敗: {e}")
        sys.exit(1)


def execute_migration(db_path: str, migration_sql: str, migration_name: str) -> bool:
    """
    執行 migration

    Args:
        db_path: 資料庫路徑
        migration_sql: Migration SQL
        migration_name: Migration 名稱

    Returns:
        是否成功
    """
    try:
        # 檢查資料庫是否存在
        if not os.path.exists(db_path):
            print(f"✗ 資料庫不存在: {db_path}")
            return False

        # 連接資料庫
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"正在執行 migration: {migration_name}")
        print(f"目標資料庫: {db_path}")
        print()

        # 執行 migration
        cursor.executescript(migration_sql)

        # 提交變更
        conn.commit()

        # 驗證表是否創建成功
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print(f"✓ Migration 執行成功")
        print(f"  - 當前表數量: {len(tables)}")
        print()

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Migration 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_tables(db_path: str):
    """
    列出資料庫中的所有表

    Args:
        db_path: 資料庫路徑
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 獲取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print("資料庫表列表:")
        for table in tables:
            table_name = table[0]
            # 獲取表的欄位資訊
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\n  {table_name} ({len(columns)} 欄位):")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                pk_str = " [PRIMARY KEY]" if pk else ""
                not_null_str = " NOT NULL" if not_null else ""
                print(f"    - {col_name}: {col_type}{not_null_str}{pk_str}")

        # 獲取所有視圖
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()

        if views:
            print("\n視圖列表:")
            for view in views:
                print(f"  - {view[0]}")

        conn.close()

    except Exception as e:
        print(f"✗ 列出表失敗: {e}")


def migrate_from_config(config_path: str, migration_path: str) -> bool:
    """
    從配置檔案讀取資料庫路徑並執行 migration

    Args:
        config_path: 配置檔案路徑
        migration_path: Migration 檔案路徑

    Returns:
        是否成功
    """
    try:
        # 取得專案根目錄
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        # 讀取配置
        if not os.path.isabs(config_path):
            config_path = os.path.join(project_root, config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 取得資料庫路徑
        db_config = config.get('database', {})
        general_db_path = db_config.get('general_inventory_path', 'database/general_inventory.db')

        # 轉換為絕對路徑
        general_db = os.path.join(project_root, general_db_path)

        # 讀取 migration
        if not os.path.isabs(migration_path):
            migration_path = os.path.join(project_root, migration_path)

        migration_sql = read_migration_file(migration_path)
        migration_name = os.path.basename(migration_path)

        # 執行 migration
        success = execute_migration(general_db, migration_sql, migration_name)

        if success:
            print("=" * 70)
            print("✅ Migration 完成")
            print("=" * 70)
            print()
            list_tables(general_db)

        return success

    except Exception as e:
        print(f"✗ Migration 失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("=" * 70)
    print("資料庫 Migration 工具 v1.0.0")
    print("=" * 70)
    print()

    # 檢查命令行參數
    if len(sys.argv) < 2:
        print("使用方式:")
        print()
        print("方法 1: 指定資料庫和 migration 檔案")
        print(f"  python {sys.argv[0]} --db <database_path> --migration <migration_file>")
        print()
        print("方法 2: 從配置檔案讀取資料庫路徑")
        print(f"  python {sys.argv[0]} --config <config_path> --migration <migration_file>")
        print()
        print("範例:")
        print(f"  python {sys.argv[0]} --db database/general_inventory.db --migration database/migrations/001_add_blood_management.sql")
        print(f"  python {sys.argv[0]} --config config/station.json --migration database/migrations/001_add_blood_management.sql")
        print()
        sys.exit(1)

    # 解析參數
    args = sys.argv[1:]
    db_path = None
    migration_path = None
    config_path = None

    for i in range(len(args)):
        if args[i] == '--db' and i + 1 < len(args):
            db_path = args[i + 1]
        elif args[i] == '--migration' and i + 1 < len(args):
            migration_path = args[i + 1]
        elif args[i] == '--config' and i + 1 < len(args):
            config_path = args[i + 1]

    # 驗證參數
    if not migration_path:
        print("✗ 錯誤: 必須指定 --migration 參數")
        sys.exit(1)

    # 執行 migration
    if config_path:
        # 從配置檔案讀取
        success = migrate_from_config(config_path, migration_path)
    elif db_path:
        # 直接指定資料庫
        migration_sql = read_migration_file(migration_path)
        migration_name = os.path.basename(migration_path)
        success = execute_migration(db_path, migration_sql, migration_name)

        if success:
            print("=" * 70)
            print("✅ Migration 完成")
            print("=" * 70)
            print()
            list_tables(db_path)
    else:
        print("✗ 錯誤: 必須指定 --db 或 --config 參數")
        sys.exit(1)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
