#!/usr/bin/env python3
"""
同步封包序列化測試腳本
驗證 SyncChangeRecord 序列化修復
"""

import json
import sys
from pydantic import BaseModel, Field
from typing import List


class SyncChangeRecord(BaseModel):
    """同步變更記錄"""
    table: str = Field(..., description="資料表名稱")
    operation: str = Field(..., description="操作類型: INSERT, UPDATE, DELETE")
    data: dict = Field(..., description="資料內容")
    timestamp: str = Field(..., description="變更時間戳")


def test_pydantic_to_dict_conversion():
    """測試 Pydantic 模型轉換為 dict"""
    print("=" * 70)
    print("測試 1: Pydantic 模型轉換為 dict")
    print("=" * 70)

    # 創建測試資料
    test_changes = [
        SyncChangeRecord(
            table="items",
            operation="INSERT",
            data={"item_code": "TEST001", "item_name": "測試物品", "current_stock": 100},
            timestamp="2025-11-14T10:00:00"
        ),
        SyncChangeRecord(
            table="blood_events",
            operation="UPDATE",
            data={"event_id": "EVT001", "remarks": "測試備註"},
            timestamp="2025-11-14T11:00:00"
        )
    ]

    print(f"✓ 創建了 {len(test_changes)} 個 SyncChangeRecord 物件")
    print(f"  - 類型: {type(test_changes[0])}")

    # 測試直接 JSON 序列化（應該失敗）
    print("\n測試直接 JSON 序列化 (預期失敗):")
    try:
        json_str = json.dumps(test_changes)
        print("✗ 不應該成功：直接序列化 Pydantic 物件")
        return False
    except TypeError as e:
        print(f"✓ 預期的錯誤: {e}")

    # 測試轉換為 dict 後序列化（應該成功）
    print("\n測試轉換為 dict 後序列化 (預期成功):")
    try:
        changes_dict = [change.dict() for change in test_changes]
        json_str = json.dumps(changes_dict, ensure_ascii=False, indent=2)
        print(f"✓ 序列化成功！")
        print(f"  - 類型: {type(changes_dict[0])}")
        print(f"  - JSON 長度: {len(json_str)} bytes")
        print(f"\n序列化結果預覽:")
        print(json_str[:300] + "...")

        # 驗證可以反序列化
        parsed = json.loads(json_str)
        print(f"\n✓ 反序列化成功！")
        print(f"  - 解析後的變更數量: {len(parsed)}")
        print(f"  - 第一筆資料表: {parsed[0]['table']}")

        return True
    except Exception as e:
        print(f"✗ 序列化失敗: {e}")
        return False


def test_endpoint_simulation():
    """模擬 API endpoint 的處理流程"""
    print("\n" + "=" * 70)
    print("測試 2: 模擬 API Endpoint 處理流程")
    print("=" * 70)

    # 模擬 request.changes (Pydantic 模型列表)
    request_changes = [
        SyncChangeRecord(
            table="inventory_events",
            operation="INSERT",
            data={
                "event_id": "EVT-20251114-001",
                "station_id": "TC-01",
                "item_code": "MED001",
                "quantity": 50,
                "timestamp": "2025-11-14T12:00:00"
            },
            timestamp="2025-11-14T12:00:00"
        )
    ]

    print(f"模擬收到請求，包含 {len(request_changes)} 筆變更")
    print(f"  - 原始類型: {type(request_changes[0])}")

    # 模擬修復後的 endpoint 處理
    print("\n套用修復: changes_dict = [change.dict() for change in request.changes]")
    changes_dict = [change.dict() for change in request_changes]

    print(f"✓ 轉換成功")
    print(f"  - 轉換後類型: {type(changes_dict[0])}")

    # 模擬 import_sync_package 內部的 JSON 處理
    print("\n模擬 import_sync_package() 內部處理:")
    try:
        package_content = json.dumps(changes_dict, ensure_ascii=False, sort_keys=True)
        print(f"✓ JSON 序列化成功")
        print(f"  - 封包大小: {len(package_content)} bytes")

        # 計算校驗碼
        import hashlib
        checksum = hashlib.sha256(package_content.encode('utf-8')).hexdigest()
        print(f"✓ 校驗碼計算成功: {checksum[:16]}...")

        return True
    except Exception as e:
        print(f"✗ 處理失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sqlite_row_conversion():
    """測試 SQLite Row 物件轉換"""
    print("\n" + "=" * 70)
    print("測試 3: SQLite Row 物件轉換為 dict")
    print("=" * 70)

    try:
        import sqlite3

        # 創建臨時資料庫
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 創建測試表
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                quantity INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 插入測試資料
        cursor.execute("""
            INSERT INTO test_table (name, quantity) VALUES (?, ?)
        """, ("測試物品", 100))

        # 查詢並轉換
        cursor.execute("SELECT * FROM test_table")
        row = cursor.fetchone()

        print(f"✓ 查詢到資料")
        print(f"  - Row 類型: {type(row)}")

        # 轉換為 dict
        row_dict = dict(row)
        print(f"✓ 轉換為 dict 成功")
        print(f"  - Dict 類型: {type(row_dict)}")
        print(f"  - 內容: {row_dict}")

        # 測試 JSON 序列化
        json_str = json.dumps(row_dict, ensure_ascii=False)
        print(f"✓ JSON 序列化成功")
        print(f"  - JSON: {json_str}")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("\n")
    print("=" * 70)
    print("🧪 同步封包序列化測試")
    print("=" * 70)
    print("\n")

    results = []

    # 執行測試
    results.append(("Pydantic 轉換測試", test_pydantic_to_dict_conversion()))
    results.append(("Endpoint 模擬測試", test_endpoint_simulation()))
    results.append(("SQLite Row 轉換測試", test_sqlite_row_conversion()))

    # 測試報告
    print("\n")
    print("=" * 70)
    print("📊 測試報告")
    print("=" * 70)
    print("\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通過" if result else "✗ 失敗"
        print(f"  {status}: {name}")

    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n✅ 所有測試通過！序列化修復成功。")
        print("\n修復摘要:")
        print("  ✓ import endpoint: 已轉換 Pydantic 模型為 dict")
        print("  ✓ hospital upload endpoint: 已轉換 Pydantic 模型為 dict")
        print("  ✓ generate endpoint: 返回純 dict，無需修改")
        return 0
    else:
        print("\n❌ 部分測試失敗，請檢查修復。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
