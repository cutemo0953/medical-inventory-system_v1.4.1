# 同步功能錯誤處理指南

## 概述

本指南說明如何使用增強的同步功能錯誤處理和日誌系統來快速定位和解決問題。

## 日誌級別說明

### INFO 級別
記錄關鍵操作的進度和成功訊息：
```
✓ 同步封包已產生: PKG-20251114-120000-TC01 (150 項變更, 51200 bytes)
✓ 同步封包匯入成功: PKG-20251114-120000-TC01 (150 項變更)
✓ 醫院層已接收同步: TC-01 - PKG-20251114-120000-TC01 (150 項變更)
```

### DEBUG 級別
記錄詳細的處理流程（需要設定 log level 為 DEBUG）：
```
開始 JSON 序列化...
處理變更 1/150: table=items, operation=INSERT
處理變更 2/150: table=blood_events, operation=INSERT
```

### WARNING 級別
記錄潛在問題但不影響執行：
```
增量同步未提供 sinceTimestamp，將使用全量同步
發現 2 項衝突
```

### ERROR 級別
記錄錯誤詳情和堆疊追蹤：
```
✗ 產生同步封包失敗: no such table: blood_events
✗ 無法序列化記錄 items[5]: Object of type datetime is not JSON serializable
✗ 封包驗證失敗: 變更 10 缺少必要欄位 (table/operation/data)
```

## 常見錯誤和解決方案

### 1. 序列化錯誤

**錯誤訊息**:
```
ERROR - JSON 序列化失敗: Object of type datetime is not JSON serializable
ERROR - 無法序列化的變更 [5]: table=blood_events, data_type=<class 'datetime.datetime'>
```

**原因**: 資料庫中的某些欄位（如 datetime）無法直接轉換為 JSON

**解決方案**:
1. 檢查日誌中標示的 table 和 index
2. 確認該表的資料類型是否正確
3. 確保 sqlite3.Row 正確轉換為 dict
4. 檢查是否有自訂的資料類型需要特殊處理

### 2. 封包格式錯誤

**錯誤訊息**:
```
ERROR - 封包格式錯誤：缺少封包ID
ERROR - 封包格式錯誤：變更記錄清單為空
ERROR - 變更 10 缺少必要欄位 (table/operation/data)
```

**原因**: 封包格式不完整或錯誤

**解決方案**:
1. 檢查封包是否包含所有必要欄位：
   - packageId: 封包ID
   - checksum: SHA-256 校驗碼
   - changes: 變更記錄清單（非空）
2. 檢查每筆變更記錄是否包含：
   - table: 資料表名稱
   - operation: INSERT/UPDATE/DELETE
   - data: 資料內容（dict）
   - timestamp: 時間戳

### 3. 資料庫查詢錯誤

**錯誤訊息**:
```
ERROR - 查詢表 blood_events 失敗: no such table: blood_events
ERROR - 保存封包記錄失敗: NOT NULL constraint failed: sync_packages.hospital_id
```

**原因**: 資料表不存在或約束條件不滿足

**解決方案**:
1. 確認資料庫 schema 已正確初始化
2. 執行 migration 腳本：
   ```bash
   python3 scripts/migrate_database.py --db general_inventory.db
   ```
3. 檢查約束條件（NOT NULL, UNIQUE, FOREIGN KEY）

### 4. 校驗碼不符

**錯誤訊息**:
```
ERROR - 校驗碼不符，封包可能已損毀
Expected: abc123...
Actual: def456...
```

**原因**: 封包在傳輸過程中被修改或損毀

**解決方案**:
1. 重新產生同步封包
2. 檢查傳輸過程（USB、網路）是否有問題
3. 確認沒有手動修改封包內容

## 啟用詳細日誌

### 方法 1: 修改 main.py
```python
import logging

# 設定為 DEBUG 級別以查看所有日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 方法 2: 環境變數
```bash
export LOG_LEVEL=DEBUG
python3 main.py
```

### 方法 3: 啟動參數
```bash
python3 main.py --log-level DEBUG
```

## 測試錯誤處理

執行測試腳本驗證錯誤處理功能：

```bash
# 測試序列化修復
python3 test_sync_serialization.py

# 測試錯誤處理增強
python3 test_error_handling.py
```

## API Endpoint 錯誤處理

### Generate Endpoint

**請求範例**:
```bash
curl -X POST http://localhost:8000/api/station/sync/generate \
  -H "Content-Type: application/json" \
  -d '{
    "stationId": "TC-01",
    "hospitalId": "HOSP-001",
    "syncType": "DELTA",
    "sinceTimestamp": "2025-11-14T00:00:00"
  }'
```

**成功回應** (200):
```json
{
  "success": true,
  "package_id": "PKG-20251114-120000-TC01",
  "package_type": "DELTA",
  "package_size": 51200,
  "checksum": "abc123...",
  "changes_count": 150,
  "changes": [...]
}
```

**錯誤回應** (400):
```json
{
  "detail": "無效的同步類型: INVALID"
}
```

**錯誤回應** (500):
```json
{
  "detail": "產生同步封包失敗: no such table: blood_events"
}
```

### Import Endpoint

**請求範例**:
```bash
curl -X POST http://localhost:8000/api/station/sync/import \
  -H "Content-Type: application/json" \
  -d '{
    "stationId": "TC-01",
    "packageId": "PKG-20251114-120000-TC01",
    "checksum": "abc123...",
    "changes": [
      {
        "table": "items",
        "operation": "INSERT",
        "data": {"item_code": "TEST001", "item_name": "測試物品"},
        "timestamp": "2025-11-14T12:00:00"
      }
    ]
  }'
```

**成功回應** (200):
```json
{
  "success": true,
  "package_id": "PKG-20251114-120000-TC01",
  "changes_applied": 150,
  "conflicts": []
}
```

**錯誤回應** (400):
```json
{
  "detail": "封包格式錯誤：變更記錄清單為空"
}
```

**錯誤回應** (400):
```json
{
  "detail": "變更 10 缺少必要欄位 (table/operation/data)"
}
```

## 日誌檔案位置

預設日誌會輸出到：
- 標準輸出（console）
- 日誌檔案（如果有設定）

查看即時日誌：
```bash
# 如果使用 systemd
sudo journalctl -u medical-inventory -f

# 如果直接執行
python3 main.py 2>&1 | tee sync.log
```

## 監控建議

1. **定期檢查錯誤日誌**:
   ```bash
   grep "ERROR" sync.log | tail -50
   ```

2. **監控序列化錯誤**:
   ```bash
   grep "無法序列化" sync.log
   ```

3. **追蹤同步失敗率**:
   ```bash
   grep "✗.*失敗" sync.log | wc -l
   ```

4. **檢查校驗碼錯誤**:
   ```bash
   grep "校驗碼不符" sync.log
   ```

## 效能影響

增強的錯誤處理和日誌記錄對效能的影響：

- **INFO 級別**: 幾乎無影響 (< 1%)
- **DEBUG 級別**: 輕微影響 (< 5%)
- **序列化錯誤偵測**: 僅在發生錯誤時執行

建議：
- 生產環境使用 INFO 級別
- 開發/測試環境使用 DEBUG 級別
- 問題排查時臨時啟用 DEBUG 級別

## 技術細節

### 錯誤處理層級

1. **API Endpoint 層**:
   - 參數驗證
   - 格式檢查
   - HTTP 狀態碼回應

2. **Database 層**:
   - SQL 查詢錯誤
   - 記錄序列化錯誤
   - 事務管理

3. **JSON 序列化層**:
   - 類型檢查
   - 錯誤定位
   - 詳細日誌

### 異常類型處理

- `HTTPException`: API 層錯誤，回傳給客戶端
- `ValueError`: 驗證錯誤，轉換為 400 狀態碼
- `TypeError`: 序列化錯誤，詳細記錄後回傳 500
- `Exception`: 通用錯誤，完整堆疊追蹤

## 故障排除檢查清單

當同步失敗時，按順序檢查：

- [ ] 檢查日誌中的錯誤訊息
- [ ] 確認資料庫 schema 正確
- [ ] 驗證封包格式完整
- [ ] 檢查網路/USB 傳輸
- [ ] 確認資料類型正確
- [ ] 檢查約束條件
- [ ] 驗證校驗碼
- [ ] 查看詳細堆疊追蹤

## 聯絡支援

如果問題仍然存在，請提供：

1. 完整的錯誤日誌（包含堆疊追蹤）
2. 請求的 JSON payload
3. 資料庫版本和 schema
4. 復現步驟

## 變更歷史

- **2025-11-14**: 初版發布
  - 加強三個同步 endpoints 的錯誤處理
  - 新增詳細的日誌記錄
  - 新增測試腳本
