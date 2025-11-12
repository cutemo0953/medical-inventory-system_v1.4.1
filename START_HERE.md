# 🎯 開始測試 - 快速指南

## ✅ 您的問題解答

### 1. **血庫列印標籤按鈕** - 已找到！
**位置**：`Index.html:729-734`

**如何使用**：
1. 啟動服務後訪問 http://localhost:8000
2. 點擊頂部的「**血袋管理**」標籤頁（紅色心形 ❤️ 圖標）
3. 向下滾動找到「**血袋入庫**」區塊
4. 填寫血袋資訊（編號、血型、數量等）
5. 點擊「**列印標籤**」按鈕（藍色按鈕，在「確認入庫」旁邊）
6. 會彈出新視窗顯示標籤，包含 QR Code，可直接列印

---

### 2. **同步管理標籤頁** - 已找到！
**位置**：`Index.html:233-240` (按鈕), `1715-1721` (內容)

**如何使用**：
1. 在頂部導航列找到「**同步管理**」按鈕（紫色循環箭頭 🔄 圖標）
2. 點擊後會顯示：
   - 待同步變更數量
   - 已同步封包數量
   - 最後同步時間
   - 同步記錄列表
3. 可以點擊「手動同步」按鈕進行同步

---

### 3. **單機多站點測試** - 已就緒！

---

## 🚀 立即開始測試

### 方法 A：使用測試腳本（推薦）

```bash
cd /home/user/medical-inventory-system_v1.4.1
./test_multi_station.sh
```

**選項說明**：
1. 啟動後端服務
2. 檢查資料庫狀態
3. 清空測試資料
4. 查看測試指南

---

### 方法 B：手動啟動

```bash
cd /home/user/medical-inventory-system_v1.4.1
python main.py
```

---

## 📍 設定站點 - 超簡單！

### 選項 1：使用圖形介面（最簡單）✨

1. 啟動服務後，訪問：**http://localhost:8000/setup**
2. 點擊預設站點按鈕（TC-01, TC-02, TC-03, TC-04）
3. 或者輸入自訂站點ID
4. 點擊「前往主系統」

### 選項 2：使用開發者工具

1. 訪問 http://localhost:8000
2. 按 F12 開啟開發者工具
3. 切換到 Console 標籤
4. 執行：
```javascript
localStorage.setItem('stationId', 'TC-01');
localStorage.setItem('stationName', '前線醫療站01');
location.reload();
```

---

## 🧪 測試流程

### Step 1: 設定兩個站點

**分頁 1 - TC-01**：
```
http://localhost:8000/setup
→ 點擊「TC-01 - 前線醫療站」
→ 點擊「前往主系統」
```

**分頁 2 - TC-02**（開新分頁）：
```
http://localhost:8000/setup
→ 點擊「TC-02 - 後勤補給站」
→ 點擊「前往主系統」
```

---

### Step 2: 建立初始庫存（在 TC-01）

1. 點擊「**物品管理**」標籤頁
2. 新增物資：
   - 名稱：繃帶
   - 數量：100
   - 單位：個
   - 位置：A-01
3. 點擊「確認入庫」

---

### Step 3: 測試調撥（TC-01 → TC-02）

**在 TC-01 分頁**：
1. 找到「繃帶」
2. 點擊「調撥」
3. 填寫：
   - 目標站點：TC-02
   - 數量：30
4. 確認調撥

**在 TC-02 分頁**：
1. 按 F5 刷新頁面
2. 應該看到「繃帶」出現，數量為 30 ✅

---

### Step 4: 測試血袋管理（在 TC-01）

1. 點擊「**血袋管理**」標籤頁
2. 填寫血袋入庫資訊：
   - 編號：BB-001
   - 血型：O+
   - 數量：10
3. 點擊「**列印標籤**」查看標籤（包含 QR Code）
4. 點擊「確認入庫」
5. 在列表中找到 BB-001，點擊「站點轉移」
6. 轉移 5 個單位到 TC-02

**在 TC-02 分頁**：
1. 刷新頁面
2. 應該看到 BB-001 的 5 個單位 ✅

---

### Step 5: 查看同步管理

1. 點擊「**同步管理**」標籤頁（紫色按鈕）
2. 查看同步狀態
3. 點擊「手動同步」測試同步功能

---

## 📚 詳細文檔

- **快速測試指南**：`QUICK_TEST_MULTI_STATION.md`（必讀！）
- **聯邦架構說明**：`FEDERATED_ARCHITECTURE.md`
- **多站點設定**：`MULTI_STATION_SETUP.md`
- **站點合併指南**：`STATION_MERGE_GUIDE.md`
- **測試與部署**：`TESTING_DEPLOYMENT_GUIDE.md`

---

## 🔍 驗證測試成功

### 資料庫檢查
```bash
sqlite3 database/medical_inventory.db
```

```sql
-- 查看站點庫存
SELECT station_id, name, quantity, unit FROM inventory;

-- 查看調撥記錄
SELECT source_station, target_station, item_name, quantity, timestamp
FROM transfers
ORDER BY timestamp DESC;

-- 查看血袋庫存
SELECT station_id, blood_bag_id, blood_type, quantity
FROM blood_inventory;

.quit
```

---

## ⚠️ 常見問題

### Q: 找不到「列印標籤」按鈕？
**A**: 確認您在「血袋管理」標籤頁，向下滾動找到「血袋入庫」區塊，按鈕在藍色「確認入庫」旁邊。

### Q: 找不到「同步管理」標籤頁？
**A**: 在頂部導航列找紫色的循環箭頭圖標。如果螢幕較小，可能需要橫向滾動。

### Q: 調撥後目標站點看不到？
**A**:
1. 確認目標站點ID正確（區分大小寫）
2. 在目標站點分頁按 F5 刷新
3. 檢查瀏覽器 Console 是否有錯誤

### Q: 站點ID設定不成功？
**A**: 使用新的圖形介面工具：http://localhost:8000/setup

---

## 📊 測試檢查清單

完成後打勾：

- [ ] 成功啟動後端服務（localhost:8000）
- [ ] 使用 /setup 頁面設定 TC-01
- [ ] 使用 /setup 頁面設定 TC-02（新分頁）
- [ ] 在 TC-01 建立物資庫存
- [ ] 從 TC-01 調撥物資到 TC-02
- [ ] 在 TC-02 確認收到物資
- [ ] 找到「血袋管理」標籤頁
- [ ] 建立血袋庫存
- [ ] 成功使用「列印標籤」功能
- [ ] 執行血袋站點轉移
- [ ] 找到「同步管理」標籤頁
- [ ] 測試手動同步功能
- [ ] 查看歷史記錄和調撥記錄

---

## 🎉 測試成功後

您可以進一步探索：
- 站點合併功能（參考 `STATION_MERGE_GUIDE.md`）
- 緊急撤離功能
- Walking Blood Bank（緊急捐血者）
- 離線同步與聯邦架構

---

## 📞 需要幫助？

1. 檢查瀏覽器 Console (F12) 的錯誤訊息
2. 檢查後端終端的日誌
3. 確認依賴安裝：
```bash
pip install -r requirements_v1.4.1.txt
```

---

## 🔗 重要連結

- **主系統**：http://localhost:8000
- **站點設定**：http://localhost:8000/setup ⭐ 新增！
- **API 文檔**：http://localhost:8000/docs
- **API 資訊**：http://localhost:8000/api/info

---

**祝測試順利！** 🚀✨

如有任何問題，請參考 `QUICK_TEST_MULTI_STATION.md` 獲取更詳細的說明。
