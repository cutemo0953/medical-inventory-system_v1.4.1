# 同步封包格式驗證工具

## 概述

`validate_sync_package.py` 是一個用於驗證同步封包格式的工具。在將下載的封包匯入系統之前，使用此工具可以快速檢測格式錯誤，避免匯入失敗。

## 功能特點

✓ **JSON 格式驗證** - 檢查檔案是否為有效的 JSON
✓ **必要欄位檢查** - 驗證封包包含所有必要欄位
✓ **變更記錄結構驗證** - 檢查每筆變更記錄的格式
✓ **資料類型檢查** - 確保所有資料都是 JSON 可序列化的
✓ **校驗碼驗證** - 可選的校驗碼完整性檢查
✓ **詳細錯誤報告** - 提供具體的錯誤位置和原因

## 使用方式

### 基本驗證

```bash
# 驗證封包格式
python3 scripts/validate_sync_package.py <封包檔案路徑>

# 範例
python3 scripts/validate_sync_package.py ~/Downloads/sync_package.json
```

### 校驗碼驗證

```bash
# 驗證格式並重新計算校驗碼
python3 scripts/validate_sync_package.py --verify-checksum <封包檔案路徑>

# 範例
python3 scripts/validate_sync_package.py --verify-checksum ~/Downloads/sync_package.json
```

## 輸出說明

### 成功的輸出

```
======================================================================
驗證同步封包: sync_package.json
======================================================================
✓ JSON 格式正確

檢查必要欄位:
  ✓ 欄位 package_id 存在且類型正確
  ✓ 欄位 package_type 存在且類型正確
  ✓ 欄位 checksum 存在且類型正確
  ✓ 欄位 changes 存在且類型正確

檢查變更記錄結構:
  ✓ 包含 150 筆變更記錄
  ✓ 所有變更記錄格式正確

檢查資料類型:
  ✓ 所有資料類型都是 JSON 可序列化的

檢查校驗碼:
  ✓ 校驗碼存在: abc123...
  ✓ 校驗碼格式正確 (SHA-256)

======================================================================
驗證摘要:
======================================================================
  封包ID: PKG-20251114-120000-TC01
  封包類型: DELTA
  變更數量: 150
  封包大小: 51200 bytes

✅ 封包格式完全正確，可以安全匯入！
```

### 錯誤的輸出

```
======================================================================
驗證同步封包: invalid_package.json
======================================================================
✓ JSON 格式正確

檢查必要欄位:
  ✓ 欄位 package_id 存在且類型正確
  ✗ 缺少必要欄位: checksum
  ✓ 欄位 changes 存在且類型正確

❌ 封包格式驗證失敗，請檢查上述錯誤訊息

常見問題:
  1. 封包是否在下載過程中損毀？
  2. 封包是否包含非 JSON 可序列化的資料類型？
  3. 封包是否缺少必要欄位？

請參考 ERROR_HANDLING_GUIDE.md 以獲取更多資訊
```

## 封包格式要求

### 必要欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `package_id` | string | 封包唯一識別碼（例：PKG-20251114-120000-TC01） |
| `package_type` | string | 封包類型（DELTA 或 FULL） |
| `checksum` | string | SHA-256 校驗碼（64 字元十六進位字串） |
| `changes` | array | 變更記錄清單 |

### 可選欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `success` | boolean | 封包產生是否成功 |
| `package_size` | integer | 封包大小（bytes） |
| `changes_count` | integer | 變更記錄數量 |
| `message` | string | 描述訊息 |

### 變更記錄格式

每筆變更記錄必須包含：

```json
{
  "table": "items",           // 資料表名稱（必要）
  "operation": "INSERT",      // 操作類型（必要，INSERT/UPDATE/DELETE）
  "data": {                   // 資料內容（必要，dict）
    "item_code": "MED001",
    "item_name": "紗布",
    "current_stock": 100
  },
  "timestamp": "2025-11-14T12:00:00"  // 時間戳（必要，ISO 8601 格式）
}
```

## 驗證檢查項目

### 1. JSON 格式檢查
- 檔案是否存在
- JSON 語法是否正確
- 編碼是否為 UTF-8

### 2. 必要欄位檢查
- package_id: 必須存在且為字串
- package_type: 必須存在且為字串
- checksum: 必須存在且為字串
- changes: 必須存在且為陣列

### 3. 變更記錄結構檢查
- 每筆變更必須包含 table, operation, data, timestamp
- operation 必須是 INSERT, UPDATE, DELETE 之一
- data 必須是 dict 類型
- timestamp 必須是字串

### 4. 資料類型檢查
- 所有值必須是 JSON 可序列化的類型：
  - string, int, float, bool, list, dict, null
- 不允許的類型：
  - datetime 物件
  - bytes 物件
  - 自訂類別實例
  - 函數或方法

### 5. 校驗碼檢查（可選）
- 校驗碼長度必須是 64 字元
- 校驗碼必須是有效的十六進位字串
- 使用 `--verify-checksum` 選項時，會重新計算並比對校驗碼

## 常見錯誤和解決方案

### 錯誤 1: JSON 解析失敗

**錯誤訊息**:
```
✗ JSON 解析失敗: Expecting ',' delimiter: line 10 column 5
```

**原因**: JSON 語法錯誤（缺少逗號、括號不匹配等）

**解決方案**:
1. 使用 JSON 編輯器檢查語法
2. 檢查引號、逗號、括號是否正確配對
3. 重新下載封包

### 錯誤 2: 缺少必要欄位

**錯誤訊息**:
```
✗ 缺少必要欄位: checksum
```

**原因**: 封包產生時未包含必要欄位

**解決方案**:
1. 檢查 generate endpoint 的實現
2. 確認封包產生過程沒有被中斷
3. 重新產生封包

### 錯誤 3: 非 JSON 可序列化的資料

**錯誤訊息**:
```
✗ 變更 5 包含非 JSON 可序列化的資料: Object of type datetime is not JSON serializable
變更 5, 欄位 data.created_at: datetime (值: 2025-11-14 12:00:00)
```

**原因**: 資料庫查詢返回的 datetime 物件未轉換為字串

**解決方案**:
1. 檢查 `generate_sync_package()` 方法
2. 確認 SQLite Row 正確轉換為 dict
3. 確認 datetime 欄位轉換為 ISO 8601 字串

### 錯誤 4: operation 值無效

**錯誤訊息**:
```
✗ operation 值無效: MODIFY (應為 INSERT, UPDATE, DELETE 之一)
```

**原因**: operation 欄位使用了不支援的值

**解決方案**:
1. 檢查產生封包的程式碼
2. 確認只使用 INSERT, UPDATE, DELETE
3. 修正並重新產生封包

### 錯誤 5: 校驗碼不符

**錯誤訊息**:
```
✗ 校驗碼驗證失敗
  期望: abc123...
  實際: def456...
```

**原因**: 封包在傳輸過程中被修改或損毀

**解決方案**:
1. 重新下載封包
2. 檢查傳輸過程（USB、網路）
3. 確認沒有手動編輯封包內容

## 工作流程建議

### 下載後立即驗證

```bash
# 1. 從 Safari 下載封包
# 2. 立即驗證格式
python3 scripts/validate_sync_package.py ~/Downloads/sync_package.json

# 3. 如果驗證通過，再匯入系統
# 4. 如果驗證失敗，檢查錯誤訊息並修復
```

### 產生後驗證

```bash
# 1. 在系統中產生封包
# 2. 下載封包
# 3. 驗證格式和校驗碼
python3 scripts/validate_sync_package.py --verify-checksum ~/Downloads/sync_package.json

# 4. 確認無誤後分發給其他站點
```

## 自動化測試

執行完整的驗證測試套件：

```bash
./test_package_validation.sh
```

測試內容包括：
- 有效的封包
- 缺少必要欄位
- 無效的 operation
- 校驗碼驗證
- 不存在的檔案

## 返回碼

- `0`: 驗證成功
- `1`: 驗證失敗

可用於腳本自動化：

```bash
if python3 scripts/validate_sync_package.py package.json; then
    echo "封包有效，開始匯入..."
    # 匯入邏輯
else
    echo "封包無效，中止匯入"
    exit 1
fi
```

## 與其他工具整合

### 與 import endpoint 整合

```bash
# 先驗證
python3 scripts/validate_sync_package.py package.json || exit 1

# 再匯入
curl -X POST http://localhost:8000/api/station/sync/import \
  -H "Content-Type: application/json" \
  -d @package.json
```

### 批次驗證

```bash
# 驗證目錄下所有封包
for file in ~/Downloads/sync_*.json; do
    echo "驗證 $file ..."
    python3 scripts/validate_sync_package.py "$file"
done
```

## 技術細節

### 校驗碼計算方式

```python
import hashlib
import json

# 1. 序列化 changes 陣列（ensure_ascii=False, sort_keys=True）
package_content = json.dumps(changes, ensure_ascii=False, sort_keys=True)

# 2. 計算 SHA-256
checksum = hashlib.sha256(package_content.encode('utf-8')).hexdigest()
```

### 驗證順序

1. JSON 格式驗證（載入檔案）
2. 必要欄位檢查（封包級別）
3. 變更記錄結構檢查（記錄級別）
4. 資料類型檢查（深度遍歷）
5. 校驗碼驗證（可選）

## 相關文件

- `ERROR_HANDLING_GUIDE.md` - 錯誤處理完整指南
- `test_sync_serialization.py` - 序列化測試
- `test_error_handling.py` - 錯誤處理測試

## 故障排除

如果驗證工具本身出現問題：

```bash
# 1. 檢查 Python 版本（需要 3.6+）
python3 --version

# 2. 檢查檔案權限
ls -l scripts/validate_sync_package.py

# 3. 手動測試
python3 -c "import json, hashlib; print('OK')"

# 4. 查看詳細錯誤
python3 -u scripts/validate_sync_package.py package.json
```

## 更新歷史

- **2025-11-14**: 初版發布
  - JSON 格式驗證
  - 必要欄位檢查
  - 變更記錄結構驗證
  - 資料類型檢查
  - 校驗碼驗證
  - 完整的錯誤報告
