# 🏥 醫療站合併作業指南

## 📋 適用情境

### 1. 站點合併
- **情境**：兩個前線醫療站需要合併為一個
- **時機**：戰線移動、人員調整、資源整合
- **目標**：保全所有醫療記錄、整合物資與設備

### 2. 病患結局處理
合併前需要處理所有病患記錄，可能的結局：

| 結局類型 | 代碼 | 處理方式 | 記錄保留 |
|---------|------|---------|---------|
| 康復出院 | DISCHARGED | 封存記錄 | ✓ 永久保留 |
| 轉院 | TRANSFERRED | 封存記錄 | ✓ 永久保留 |
| 死亡 | DECEASED | 封存記錄 | ✓ 永久保留 |
| 手術進行中 | ONGOING | **需完成或封存** | ✓ 保留 |
| 手術中止 | CANCELLED | 封存記錄 | ✓ 保留 |

---

## 🔄 合併流程（三階段）

### 階段一：合併前準備 (Pre-Merge)

#### 1.1 清點物資（盤點模式）
```
目的：確認實際庫存，避免帳面與實物不符
方式：
  1. 啟動盤點：POST /api/inventory/audit/start
     - 類型：PRE_MERGE（合併前盤點）
     - 生成盤點編號：AUDIT-{YYMMDD}-{SEQ}

  2. 逐項清點：POST /api/inventory/audit/record
     - 記錄：系統數量 vs 實際數量
     - 自動計算差異

  3. 完成盤點：POST /api/inventory/audit/complete
     - 自動調整庫存
     - 生成差異報表
```

**盤點單範例：**
```
盤點編號：AUDIT-251110-001
類型：合併前盤點
開始時間：2025-11-10 15:00
執行人：張醫師

物品代碼    物品名稱         系統數量  實際數量  差異
SURG-001   外科縫合針        50       48       -2
MED-023    止痛劑(Morphine)  100      105      +5
PPE-005    N95口罩          500      480      -20
```

#### 1.2 封存病患記錄
```
API：POST /api/surgery/archive
必填：
  - record_number: 手術記錄編號
  - patient_outcome: 病患結局（DISCHARGED/TRANSFERRED/DECEASED）
  - archived_by: 封存人員

效果：
  ✓ status改為ARCHIVED
  ✓ 記錄封存時間
  ✓ 不可再修改
```

#### 1.3 產生備份檔案
```
使用緊急備份功能：
GET /api/emergency/download-all

備份包含：
  ✓ 完整資料庫 (.db)
  ✓ CSV匯出檔案
  ✓ 配置檔案
  ✓ 檔案清單 (manifest.json)
```

---

### 階段二：執行合併 (Merge)

#### 2.1 匯入資料庫
```
API：POST /api/station/merge/import

流程：
  1. 上傳來源站的備份檔案
  2. 系統自動處理衝突：

     物品代碼衝突：
       - 相同代碼但不同名稱 → 自動重新編號
       - 範例：SURG-001 (來源站) → SURG-001-M (合併後)

     血袋庫存：
       - 相同血型 → 數量相加
       - 範例：O+ 50U + 30U = 80U

     設備ID衝突：
       - 加上來源站前綴
       - 範例：power-1 → TC02-power-1

     手術記錄：
       - 保留原記錄編號
       - 加上來源站註記
```

**衝突處理規則：**
```javascript
{
  "items": {
    "conflict_resolution": "rename_with_suffix",
    "merge_identical": true
  },
  "blood_inventory": {
    "conflict_resolution": "sum_quantities",
    "separate_by_station": false
  },
  "equipment": {
    "conflict_resolution": "prefix_station_id",
    "merge_duplicates": false
  },
  "surgery_records": {
    "conflict_resolution": "keep_all",
    "add_source_note": true
  }
}
```

#### 2.2 合併統計
```
系統自動記錄到 station_merge_history 表：
  - 來源站點ID
  - 目標站點ID
  - 合併物品數量
  - 合併血袋數量
  - 合併設備數量
  - 合併手術記錄數量
```

---

### 階段三：合併後整理 (Post-Merge)

#### 3.1 再次盤點
```
目的：確認合併後的總庫存正確
類型：POST_MERGE

流程同「階段一：盤點」
```

#### 3.2 調整物資
```
依盤點結果調整：
  - 差異 > 0：補充庫存
  - 差異 < 0：減少庫存
  - 差異 = 0：無需調整
```

#### 3.3 完成合併
```
確認事項：
  ✓ 所有病患記錄已封存
  ✓ 物資盤點完成
  ✓ 無未處理的衝突
  ✓ 設備清單已更新
```

---

## 📊 資料庫結構

### 新增表格

#### 1. surgery_records 擴充欄位
```sql
status: TEXT             -- ONGOING/COMPLETED/ARCHIVED/CANCELLED
patient_outcome: TEXT    -- DISCHARGED/TRANSFERRED/DECEASED
archived_at: TIMESTAMP   -- 封存時間
archived_by: TEXT        -- 封存人員
```

#### 2. station_merge_history (合併歷史)
```sql
id: INTEGER PRIMARY KEY
source_station_id: TEXT           -- 來源站點
target_station_id: TEXT           -- 目標站點
merge_type: TEXT                  -- FULL_MERGE/PARTIAL_MERGE/IMPORT_BACKUP
items_merged: INTEGER             -- 合併物品數
blood_merged: INTEGER             -- 合併血袋數
equipment_merged: INTEGER         -- 合併設備數
surgery_records_merged: INTEGER   -- 合併手術記錄數
merge_notes: TEXT                 -- 備註
merged_by: TEXT                   -- 執行人
merged_at: TIMESTAMP              -- 合併時間
```

#### 3. inventory_audit (盤點記錄)
```sql
id: INTEGER PRIMARY KEY
audit_number: TEXT UNIQUE         -- 盤點編號
audit_type: TEXT                  -- ROUTINE/PRE_MERGE/POST_MERGE/EMERGENCY
status: TEXT                      -- IN_PROGRESS/COMPLETED/CANCELLED
station_id: TEXT
started_by: TEXT                  -- 啟動人
started_at: TIMESTAMP
completed_by: TEXT                -- 完成人
completed_at: TIMESTAMP
total_items: INTEGER              -- 總項目數
discrepancies: INTEGER            -- 差異項目數
notes: TEXT
```

#### 4. inventory_audit_details (盤點明細)
```sql
id: INTEGER PRIMARY KEY
audit_id: INTEGER                 -- 盤點ID
item_code: TEXT                   -- 物品代碼
item_name: TEXT                   -- 物品名稱
system_quantity: INTEGER          -- 系統數量
actual_quantity: INTEGER          -- 實際數量
discrepancy: INTEGER              -- 差異
remarks: TEXT                     -- 備註
audited_by: TEXT                  -- 清點人
audited_at: TIMESTAMP
```

---

## 🔌 API 端點

### 1. 盤點功能

#### 1.1 開始盤點
```http
POST /api/inventory/audit/start
Content-Type: application/json

{
  "audit_type": "PRE_MERGE",  // ROUTINE/PRE_MERGE/POST_MERGE/EMERGENCY
  "station_id": "TC-01",
  "started_by": "張醫師",
  "notes": "合併前全面盤點"
}

Response:
{
  "success": true,
  "audit_number": "AUDIT-251110-001",
  "audit_id": 1,
  "total_items": 150,
  "message": "盤點已啟動，請逐項清點"
}
```

#### 1.2 記錄盤點結果
```http
POST /api/inventory/audit/record
Content-Type: application/json

{
  "audit_id": 1,
  "item_code": "SURG-001",
  "actual_quantity": 48,
  "audited_by": "李護理師",
  "remarks": "發現2支已過期"
}

Response:
{
  "success": true,
  "item_code": "SURG-001",
  "system_quantity": 50,
  "actual_quantity": 48,
  "discrepancy": -2,
  "message": "已記錄，差異 -2"
}
```

#### 1.3 完成盤點
```http
POST /api/inventory/audit/complete
Content-Type: application/json

{
  "audit_id": 1,
  "completed_by": "張醫師",
  "auto_adjust": true,  // 自動調整庫存
  "notes": "盤點完成，總計發現20項差異"
}

Response:
{
  "success": true,
  "audit_number": "AUDIT-251110-001",
  "total_items": 150,
  "discrepancies": 20,
  "adjusted_items": 20,
  "message": "盤點完成，庫存已調整"
}
```

#### 1.4 查詢盤點記錄
```http
GET /api/inventory/audit/list?status=COMPLETED&limit=10

Response:
{
  "audits": [
    {
      "audit_number": "AUDIT-251110-001",
      "audit_type": "PRE_MERGE",
      "status": "COMPLETED",
      "total_items": 150,
      "discrepancies": 20,
      "started_by": "張醫師",
      "started_at": "2025-11-10T15:00:00",
      "completed_at": "2025-11-10T17:30:00"
    }
  ],
  "count": 1
}
```

### 2. 封存功能

#### 2.1 封存手術記錄
```http
POST /api/surgery/archive
Content-Type: application/json

{
  "record_number": "TC01-20251110-001",
  "patient_outcome": "DISCHARGED",  // DISCHARGED/TRANSFERRED/DECEASED
  "archived_by": "王醫師",
  "notes": "病患已康復出院"
}

Response:
{
  "success": true,
  "record_number": "TC01-20251110-001",
  "status": "ARCHIVED",
  "patient_outcome": "DISCHARGED",
  "archived_at": "2025-11-10T18:00:00",
  "message": "手術記錄已封存"
}
```

#### 2.2 查詢已封存記錄
```http
GET /api/surgery/archived?outcome=DECEASED&limit=20

Response:
{
  "records": [
    {
      "record_number": "TC01-20251109-003",
      "patient_name": "李XX",
      "surgery_type": "緊急剖腹探查",
      "status": "ARCHIVED",
      "patient_outcome": "DECEASED",
      "archived_at": "2025-11-09T22:30:00",
      "archived_by": "張醫師"
    }
  ],
  "count": 1
}
```

### 3. 合併功能

#### 3.1 匯入備份進行合併
```http
POST /api/station/merge/import
Content-Type: multipart/form-data

backup_file: (binary)
source_station_id: TC-02
merge_type: FULL_MERGE  // FULL_MERGE/PARTIAL_MERGE
merged_by: 管理員
notes: 合併TC-02站資料

Response:
{
  "success": true,
  "merge_id": 1,
  "source_station_id": "TC-02",
  "target_station_id": "TC-01",
  "summary": {
    "items_merged": 85,
    "items_conflicts": 5,
    "blood_merged": 8,
    "equipment_merged": 12,
    "surgery_records_merged": 23
  },
  "conflicts": [
    {
      "type": "item_code",
      "original": "SURG-001",
      "renamed": "SURG-001-M",
      "reason": "代碼衝突，自動重新命名"
    }
  ],
  "message": "合併完成，請檢查衝突項目"
}
```

#### 3.2 查詢合併歷史
```http
GET /api/station/merge/history?limit=10

Response:
{
  "merges": [
    {
      "merge_id": 1,
      "source_station_id": "TC-02",
      "target_station_id": "TC-01",
      "merge_type": "FULL_MERGE",
      "items_merged": 85,
      "blood_merged": 8,
      "equipment_merged": 12,
      "surgery_records_merged": 23,
      "merged_by": "管理員",
      "merged_at": "2025-11-10T19:00:00"
    }
  ],
  "count": 1
}
```

---

## ⚠️ 注意事項

### 1. 合併前檢查清單
- [ ] 所有病患記錄已處理（康復、轉院或死亡）
- [ ] 完成合併前盤點
- [ ] 已產生完整備份檔案
- [ ] 確認來源站備份檔案完整性
- [ ] 通知所有人員即將合併

### 2. 不可逆操作
- ✓ 封存的記錄**無法解除封存**
- ✓ 合併後資料**無法分離**
- ✓ 調整的庫存**無法自動還原**

### 3. 資料保全
- ✓ 合併前必須備份
- ✓ 封存記錄永久保留
- ✓ 所有操作記錄留存

### 4. 權限控制
建議只有管理員或指揮官權限才能：
- 啟動盤點
- 封存記錄
- 執行合併
- 調整庫存

---

## 📱 前端操作流程

### 建議新增的UI元素

#### 1. 盤點模式按鈕
```
位置：庫存管理頁面頂部
樣式：橙色按鈕 + 清點圖示
功能：進入盤點模式
```

#### 2. 手術記錄封存按鈕
```
位置：手術記錄詳情頁
條件：status = ONGOING 或 COMPLETED
樣式：紅色按鈕 + 封存圖示
需要：選擇病患結局
```

#### 3. 合併功能入口
```
位置：系統設定頁面
權限：僅管理員可見
功能：上傳備份、執行合併、查看歷史
```

---

## 🔍 測試場景

### 場景一：日常盤點
1. 啟動例行盤點
2. 清點前20項物資
3. 發現3項差異
4. 完成盤點，自動調整

### 場景二：病患出院
1. 查詢進行中的手術記錄
2. 選擇病患康復出院
3. 填寫備註
4. 確認封存

### 場景三：站點合併
1. 合併前盤點 (TC-01)
2. 封存所有病患記錄
3. 產生完整備份
4. 匯入TC-02備份
5. 處理衝突（物品重新命名）
6. 合併後盤點
7. 調整差異
8. 完成合併

---

## 📞 支援

如有問題請聯繫系統管理員或查閱完整API文件。

---

**版本：v1.4.5**
**最後更新：2025-11-10**
