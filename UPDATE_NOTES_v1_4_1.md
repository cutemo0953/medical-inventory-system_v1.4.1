# 醫療站庫存管理系統 v1.4.1 - 更新說明

## 🎉 版本資訊

**版本號:** v1.4.1  
**發佈日期:** 2025-11-05  
**類型:** 重大功能更新（手術記錄管理）

---

## ✨ 新增功能

### 1. 🏥 手術記錄管理系統

#### 核心功能
- ✅ **自動記錄編號生成**
  - 格式: `YYYYMMDD-病患姓名-N`
  - 範例: `20251105-王小明-1` (當天第1台手術)
  - 自動追蹤每日手術序號

- ✅ **完整手術資訊記錄**
  - 病患姓名
  - 手術類型
  - 主刀醫師
  - 麻醉方式
  - 手術時長（分鐘）
  - 手術備註

- ✅ **術中耗材追蹤**
  - 多項耗材登記
  - 自動從物品清單選擇
  - 自動扣減庫存
  - 耗材數量、單位記錄

- ✅ **手術記錄查詢**
  - 依日期範圍篩選
  - 依病患姓名搜尋
  - 詳細記錄檢視
  - 耗材清單展示

### 2. 📊 CSV 匯出功能

- ✅ **一鍵匯出**
  - 完整手術記錄
  - 耗材使用明細
  - 支援日期範圍篩選

- ✅ **檔案命名規則**
  - 格式: `surgery_records_YYYYMMDD_HHMMSS.csv`
  - 範例: `surgery_records_20251105_143022.csv`

- ✅ **CSV 欄位**
  ```
  記錄編號, 日期, 病患姓名, 當日第N台, 手術類型, 主刀醫師, 
  麻醉方式, 手術時長(分), 耗材代碼, 耗材名稱, 數量, 單位, 
  備註, 建立時間
  ```

### 3. 📁 資料庫結構優化

新增兩張資料表：

#### surgery_records (手術記錄主檔)
```sql
- id: 主鍵
- record_number: 記錄編號 (唯一)
- record_date: 記錄日期
- patient_name: 病患姓名
- surgery_sequence: 當日手術序號
- surgery_type: 手術類型
- surgeon_name: 主刀醫師
- anesthesia_type: 麻醉方式
- duration_minutes: 手術時長
- remarks: 備註
- station_id: 站點ID
```

#### surgery_consumptions (手術耗材明細)
```sql
- id: 主鍵
- surgery_id: 關聯手術記錄
- item_code: 物品代碼
- item_name: 物品名稱
- quantity: 數量
- unit: 單位
```

---

## 🎯 使用場景

### 場景 1: 記錄一台手術
1. 點擊「🏥 手術記錄」分頁
2. 點擊「➕ 新增手術記錄」
3. 填寫病患資訊、手術類型、主刀醫師
4. 新增使用的耗材（從下拉選單選擇）
5. 提交後自動：
   - 生成記錄編號
   - 扣減耗材庫存
   - 記錄庫存事件

**範例輸出:**
```
記錄編號: 20251105-李大華-1
病患: 李大華
手術: 闌尾切除術
醫師: 張醫師
耗材:
  - SURG-001 手術刀 x2
  - SURG-015 縫合線 x5
```

### 場景 2: 查詢特定病患的手術記錄
1. 在搜尋欄輸入病患姓名
2. 系統顯示該病患所有手術記錄
3. 點擊「詳情」查看完整資訊

### 場景 3: 月度報表匯出
1. 設定日期範圍（如 2025-11-01 到 2025-11-30）
2. 點擊「📊 匯出 CSV」
3. 下載包含所有手術及耗材的 CSV 檔
4. 用於健保申報或統計分析

---

## 📋 API 端點

### 新增的 API

#### 1. 建立手術記錄
```
POST /api/surgery/record
```

**請求範例:**
```json
{
  "patientName": "王小明",
  "surgeryType": "骨折固定手術",
  "surgeonName": "陳醫師",
  "anesthesiaType": "全身麻醉",
  "durationMinutes": 120,
  "remarks": "手術順利",
  "consumptions": [
    {
      "itemCode": "SURG-001",
      "itemName": "手術刀",
      "quantity": 2,
      "unit": "EA"
    },
    {
      "itemCode": "SURG-015",
      "itemName": "縫合線",
      "quantity": 5,
      "unit": "EA"
    }
  ],
  "stationId": "TC-01"
}
```

**回應範例:**
```json
{
  "success": true,
  "message": "手術記錄 20251105-王小明-1 建立成功",
  "recordNumber": "20251105-王小明-1",
  "surgeryId": 1,
  "sequence": 1
}
```

#### 2. 查詢手術記錄
```
GET /api/surgery/records?start_date=2025-11-01&end_date=2025-11-30&patient_name=王小明&limit=50
```

**回應範例:**
```json
{
  "records": [
    {
      "id": 1,
      "record_number": "20251105-王小明-1",
      "record_date": "2025-11-05",
      "patient_name": "王小明",
      "surgery_sequence": 1,
      "surgery_type": "骨折固定手術",
      "surgeon_name": "陳醫師",
      "anesthesia_type": "全身麻醉",
      "duration_minutes": 120,
      "remarks": "手術順利",
      "station_id": "TC-01",
      "created_at": "2025-11-05T10:30:00",
      "consumptions": [
        {
          "item_code": "SURG-001",
          "item_name": "手術刀",
          "quantity": 2,
          "unit": "EA"
        }
      ]
    }
  ],
  "count": 1
}
```

#### 3. 匯出 CSV
```
GET /api/surgery/export/csv?start_date=2025-11-01&end_date=2025-11-30
```

**直接下載 CSV 檔案**

---

## 🚀 快速部署

### 步驟 1: 備份現有資料
```bash
# 備份資料庫
cp medical_inventory.db medical_inventory.db.backup_$(date +%Y%m%d)
```

### 步驟 2: 更新後端檔案
```bash
# 複製新版本到伺服器
scp main_v1_4_1.py 你的伺服器:/path/to/medical-inventory/main.py
```

### 步驟 3: 更新前端檔案
```bash
# 複製新版本到伺服器
scp Index_v1_4_1.html 你的伺服器:/path/to/medical-inventory/Index.html
```

### 步驟 4: 重啟服務
```bash
# SSH 到伺服器
ssh user@你的伺服器

# 停止舊服務
pkill -f "python.*main.py"

# 啟動新服務
cd /path/to/medical-inventory
python3 main.py
```

### 步驟 5: 驗證部署
1. 開啟瀏覽器: `http://你的伺服器:8000`
2. 檢查版本號: 應顯示「v1.4.1 - 手術記錄版」
3. 測試新功能:
   - 新增一筆手術記錄
   - 查詢手術記錄
   - 匯出 CSV

---

## 🔄 資料庫遷移

系統會**自動執行**資料庫遷移，無需手動操作。

首次啟動 v1.4.1 時，系統會自動：
1. 建立 `surgery_records` 表
2. 建立 `surgery_consumptions` 表
3. 建立相關索引

**舊資料完全不受影響**，所有現有功能正常運作。

---

## 📊 統計資料

系統統計不變，維持原有四項指標：
- 總物品數
- 庫存警戒
- 血袋庫存
- 設備警報

---

## 🎨 UI/UX 改進

### 新增的使用者介面

1. **手術記錄分頁**
   - 清晰的表格展示
   - 搜尋篩選功能
   - 詳情檢視 Modal

2. **新增手術記錄 Modal**
   - 分步驟輸入
   - 動態耗材清單
   - 即時驗證

3. **手術詳情 Modal**
   - 完整資訊展示
   - 耗材明細表格
   - 友善的日期格式

---

## ⚠️ 注意事項

### 重要提醒

1. **庫存扣減**: 建立手術記錄時會**自動扣減**耗材庫存，請確認庫存充足

2. **記錄不可刪除**: 手術記錄一旦建立，無法刪除（可新增編輯功能）

3. **CSV 格式**: 匯出的 CSV 使用 UTF-8 編碼，Excel 開啟時需選擇正確編碼

4. **日期格式**: 所有日期使用 `YYYY-MM-DD` 格式

### 建議最佳實踐

1. **定期匯出**: 建議每月匯出一次手術記錄備份
2. **庫存檢查**: 手術前確認耗材庫存充足
3. **記錄完整性**: 盡量填寫完整資訊，包括麻醉方式、手術時長
4. **備註欄位**: 善用備註記錄特殊情況或併發症

---

## 🐛 已知問題

目前無已知問題。

---

## 🔮 未來規劃

### v1.5.0 (計劃中)
- [ ] 手術記錄編輯功能
- [ ] 手術排程管理
- [ ] 手術統計圖表
- [ ] 自動產生健保申報格式

### v1.6.0 (計劃中)
- [ ] 手術影像上傳
- [ ] 醫師簽名功能
- [ ] 病歷系統整合
- [ ] 行動版 APP

---

## 📞 技術支援

遇到問題？

1. **查看日誌**: `tail -f medical_inventory.log`
2. **檢查 API**: `curl http://localhost:8000/api/health`
3. **資料庫檢查**: 
   ```bash
   sqlite3 medical_inventory.db
   .tables
   .schema surgery_records
   ```

---

## ✅ 更新檢查清單

部署完成後，請確認：

- [ ] 版本號顯示為 v1.4.1
- [ ] 手術記錄分頁可正常開啟
- [ ] 可以新增手術記錄
- [ ] 耗材自動扣減庫存
- [ ] 記錄編號自動生成
- [ ] 可以查詢手術記錄
- [ ] CSV 匯出功能正常
- [ ] 所有舊功能正常運作

---

**v1.4.1 - 為醫療站提供完整的手術管理解決方案！** 🏥✨

**更新日期:** 2025-11-05  
**維護者:** Claude (Anthropic)
