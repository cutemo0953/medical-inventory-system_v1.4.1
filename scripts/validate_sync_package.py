#!/usr/bin/env python3
"""
同步封包格式驗證工具

驗證下載的同步封包格式是否正確，包含：
- JSON 格式驗證
- 必要欄位檢查
- 變更記錄結構驗證
- 資料類型檢查
- 校驗碼驗證

使用方式：
    python scripts/validate_sync_package.py <package.json>
    python scripts/validate_sync_package.py --verify-checksum <package.json>
"""

import json
import sys
import hashlib
from pathlib import Path


def validate_json_format(package_path: str) -> tuple:
    """驗證 JSON 格式並載入封包"""
    try:
        with open(package_path, 'r', encoding='utf-8') as f:
            package = json.load(f)
        print("✓ JSON 格式正確")
        return True, package
    except FileNotFoundError:
        print(f"✗ 檔案不存在: {package_path}")
        return False, None
    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析失敗: {str(e)}")
        print(f"  位置: 行 {e.lineno}, 列 {e.colno}")
        return False, None
    except Exception as e:
        print(f"✗ 讀取檔案失敗: {str(e)}")
        return False, None


def validate_required_fields(package: dict) -> bool:
    """檢查必要欄位"""
    print("\n檢查必要欄位:")

    # 封包級別必要欄位
    required_fields = {
        'package_id': str,
        'package_type': str,
        'checksum': str,
        'changes': list
    }

    # 可選但建議的欄位
    optional_fields = {
        'success': bool,
        'package_size': int,
        'changes_count': int,
        'message': str
    }

    all_valid = True

    # 檢查必要欄位
    for field, expected_type in required_fields.items():
        if field not in package:
            print(f"  ✗ 缺少必要欄位: {field}")
            all_valid = False
        elif not isinstance(package[field], expected_type):
            print(f"  ✗ 欄位 {field} 類型錯誤: 期望 {expected_type.__name__}, 實際 {type(package[field]).__name__}")
            all_valid = False
        else:
            print(f"  ✓ 欄位 {field} 存在且類型正確")

    # 檢查可選欄位
    for field, expected_type in optional_fields.items():
        if field in package:
            if isinstance(package[field], expected_type):
                print(f"  ✓ 可選欄位 {field} 存在且類型正確")
            else:
                print(f"  ⚠ 可選欄位 {field} 類型錯誤: 期望 {expected_type.__name__}, 實際 {type(package[field]).__name__}")

    return all_valid


def validate_changes_structure(changes: list) -> bool:
    """檢查變更記錄結構"""
    print(f"\n檢查變更記錄結構:")
    print(f"  ✓ 包含 {len(changes)} 筆變更記錄")

    if not changes:
        print("  ⚠ 變更記錄為空（可能是全新的站點）")
        return True

    # 變更記錄必要欄位
    change_required_fields = {
        'table': str,
        'operation': str,
        'data': dict,
        'timestamp': str
    }

    all_valid = True
    errors_count = 0
    max_errors_display = 5  # 最多顯示 5 個錯誤

    # 檢查第一筆記錄的結構
    print("\n  檢查第一筆變更記錄:")
    first_change = changes[0]

    for field, expected_type in change_required_fields.items():
        if field not in first_change:
            print(f"    ✗ 缺少欄位: {field}")
            all_valid = False
        elif not isinstance(first_change[field], expected_type):
            print(f"    ✗ 欄位 {field} 類型錯誤: 期望 {expected_type.__name__}, 實際 {type(first_change[field]).__name__}")
            all_valid = False
        else:
            print(f"    ✓ 欄位 {field} 正確")

    # 檢查 operation 的有效值
    if 'operation' in first_change:
        valid_operations = ['INSERT', 'UPDATE', 'DELETE']
        if first_change['operation'] not in valid_operations:
            print(f"    ✗ operation 值無效: {first_change['operation']} (應為 {', '.join(valid_operations)} 之一)")
            all_valid = False
        else:
            print(f"    ✓ operation 值有效: {first_change['operation']}")

    # 抽樣檢查所有記錄
    print(f"\n  抽樣檢查所有 {len(changes)} 筆記錄...")
    for i, change in enumerate(changes):
        # 檢查必要欄位
        for field in change_required_fields.keys():
            if field not in change:
                if errors_count < max_errors_display:
                    print(f"    ✗ 變更 {i+1} 缺少欄位: {field}")
                errors_count += 1
                all_valid = False

        # 檢查是否有非 JSON 可序列化的類型
        try:
            json.dumps(change)
        except (TypeError, ValueError) as e:
            if errors_count < max_errors_display:
                print(f"    ✗ 變更 {i+1} 包含非 JSON 可序列化的資料: {str(e)}")
            errors_count += 1
            all_valid = False

    if errors_count > max_errors_display:
        print(f"    ... 還有 {errors_count - max_errors_display} 個錯誤未顯示")

    if all_valid:
        print("  ✓ 所有變更記錄格式正確")

    return all_valid


def validate_data_types(changes: list) -> bool:
    """檢查資料類型"""
    print("\n檢查資料類型:")

    all_valid = True
    invalid_types = []

    for i, change in enumerate(changes):
        for key, value in change.items():
            # 檢查頂層欄位
            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                invalid_types.append({
                    'index': i,
                    'field': key,
                    'type': type(value).__name__,
                    'value': str(value)[:50]  # 只顯示前 50 個字元
                })
                all_valid = False

            # 檢查 data 欄位的內容
            if key == 'data' and isinstance(value, dict):
                for data_key, data_value in value.items():
                    if not isinstance(data_value, (str, int, float, bool, list, dict, type(None))):
                        invalid_types.append({
                            'index': i,
                            'field': f'data.{data_key}',
                            'type': type(data_value).__name__,
                            'value': str(data_value)[:50]
                        })
                        all_valid = False

    if invalid_types:
        print(f"  ✗ 發現 {len(invalid_types)} 個非 JSON 可序列化的值:")
        for item in invalid_types[:5]:  # 只顯示前 5 個
            print(f"    變更 {item['index']+1}, 欄位 {item['field']}: {item['type']} (值: {item['value']})")
        if len(invalid_types) > 5:
            print(f"    ... 還有 {len(invalid_types) - 5} 個")
    else:
        print("  ✓ 所有資料類型都是 JSON 可序列化的")

    return all_valid


def validate_checksum(package: dict, verify: bool = False) -> bool:
    """驗證校驗碼"""
    print("\n檢查校驗碼:")

    if 'checksum' not in package:
        print("  ✗ 封包缺少 checksum 欄位")
        return False

    checksum = package['checksum']
    print(f"  ✓ 校驗碼存在: {checksum[:16]}...")

    # 檢查校驗碼格式（應該是 64 字元的十六進位字串）
    if len(checksum) != 64:
        print(f"  ✗ 校驗碼長度錯誤: {len(checksum)} (應為 64)")
        return False

    try:
        int(checksum, 16)
        print("  ✓ 校驗碼格式正確 (SHA-256)")
    except ValueError:
        print("  ✗ 校驗碼格式錯誤 (不是有效的十六進位字串)")
        return False

    # 如果要求驗證校驗碼，則重新計算
    if verify and 'changes' in package:
        print("\n  計算實際校驗碼...")
        try:
            package_content = json.dumps(package['changes'], ensure_ascii=False, sort_keys=True)
            calculated_checksum = hashlib.sha256(package_content.encode('utf-8')).hexdigest()

            if calculated_checksum == checksum:
                print(f"  ✓ 校驗碼驗證通過")
                return True
            else:
                print(f"  ✗ 校驗碼驗證失敗")
                print(f"    期望: {checksum}")
                print(f"    實際: {calculated_checksum}")
                return False
        except Exception as e:
            print(f"  ✗ 計算校驗碼失敗: {str(e)}")
            return False

    return True


def validate_package(package_path: str, verify_checksum: bool = False) -> bool:
    """驗證封包格式（主函數）"""
    print("=" * 70)
    print(f"驗證同步封包: {package_path}")
    print("=" * 70)

    # 1. 驗證 JSON 格式
    valid, package = validate_json_format(package_path)
    if not valid:
        return False

    # 2. 檢查必要欄位
    if not validate_required_fields(package):
        return False

    # 3. 檢查變更記錄結構
    if 'changes' in package:
        if not validate_changes_structure(package['changes']):
            return False

    # 4. 檢查資料類型
    if 'changes' in package:
        if not validate_data_types(package['changes']):
            return False

    # 5. 驗證校驗碼
    if not validate_checksum(package, verify=verify_checksum):
        return False

    # 摘要
    print("\n" + "=" * 70)
    print("驗證摘要:")
    print("=" * 70)
    if 'package_id' in package:
        print(f"  封包ID: {package['package_id']}")
    if 'package_type' in package:
        print(f"  封包類型: {package['package_type']}")
    if 'changes_count' in package:
        print(f"  變更數量: {package['changes_count']}")
    if 'package_size' in package:
        print(f"  封包大小: {package['package_size']} bytes")

    print("\n✅ 封包格式完全正確，可以安全匯入！")
    return True


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方式:")
        print("  python scripts/validate_sync_package.py <package.json>")
        print("  python scripts/validate_sync_package.py --verify-checksum <package.json>")
        print("\n選項:")
        print("  --verify-checksum    重新計算並驗證校驗碼")
        sys.exit(1)

    # 解析參數
    verify_checksum = False
    package_path = None

    for arg in sys.argv[1:]:
        if arg == '--verify-checksum':
            verify_checksum = True
        elif not arg.startswith('--'):
            package_path = arg

    if not package_path:
        print("✗ 錯誤: 未指定封包檔案")
        sys.exit(1)

    # 驗證封包
    success = validate_package(package_path, verify_checksum=verify_checksum)

    if not success:
        print("\n❌ 封包格式驗證失敗，請檢查上述錯誤訊息")
        print("\n常見問題:")
        print("  1. 封包是否在下載過程中損毀？")
        print("  2. 封包是否包含非 JSON 可序列化的資料類型？")
        print("  3. 封包是否缺少必要欄位？")
        print("\n請參考 ERROR_HANDLING_GUIDE.md 以獲取更多資訊")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
