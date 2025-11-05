# 醫療站庫存管理系統 v1.4.1 - 5分鐘快速啟動

## 🚀 快速部署（適合樹莓派）

### 前置需求
- Python 3.8 或更高版本
- 網路連線（首次安裝時）

---

## 📦 步驟 1: 安裝依賴套件

```bash
# 安裝 FastAPI 和 Uvicorn
pip3 install fastapi uvicorn --break-system-packages

# 或使用 requirements.txt
pip3 install -r requirements.txt --break-system-packages
```

---

## 📁 步驟 2: 準備檔案

確保你有以下檔案：
```
/your/project/folder/
├── main.py              (後端 API - v1.4.1)
├── Index.html           (前端介面 - v1.4.1)
└── medical_inventory.db (資料庫，首次運行時自動建立)
```

**重要:** 
- `main.py` 應該是 `main_v1_4_1.py` 的內容
- `Index.html` 應該是 `Index_v1_4_1.html` 的內容

---

## ▶️ 步驟 3: 啟動服務

### 方法 A: 直接啟動（簡單）
```bash
python3 main.py
```

### 方法 B: 使用 nohup（背景執行）
```bash
nohup python3 main.py > server.log 2>&1 &
```

### 方法 C: 使用 systemd（開機自動啟動）
建立服務檔 `/etc/systemd/system/medical-inventory.service`:
```ini
[Unit]
Description=Medical Inventory Management System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/medical-inventory
ExecStart=/usr/bin/python3 /home/pi/medical-inventory/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

然後執行:
```bash
sudo systemctl daemon-reload
sudo systemctl enable medical-inventory
sudo systemctl start medical-inventory
sudo systemctl status medical-inventory
```

---

## 🌐 步驟 4: 開啟瀏覽器

### 本機訪問
```
http://localhost:8000
```

### 區域網路訪問
```
http://你的樹莓派IP:8000
```

找不到 IP？執行：
```bash
hostname -I
```

---

## ✅ 步驟 5: 驗證安裝

### 5.1 檢查版本
瀏覽器應該顯示：
```
醫療站庫存系統
v1.4.1 - 手術記錄版
```

### 5.2 檢查 API
```bash
curl http://localhost:8000/api/health
```

應該回應：
```json
{
  "status": "healthy",
  "version": "1.4.1",
  "timestamp": "2025-11-05T10:30:00.123456"
}
```

### 5.3 檢查功能
1. ✅ 統計卡片正常顯示
2. ✅ 可以切換各個分頁
3. ✅ **新功能** 手術記錄分頁存在
4. ✅ **新功能** 可以新增手術記錄
5. ✅ **新功能** 可以匯出 CSV

---

## 🎯 首次使用指南

### 1. 新增物品（如果還沒有）

1. 點擊「📦 物品查詢」
2. 點擊「➕ 新增物品」
3. 填寫資訊：
   - 物品代碼：**留空**（系統自動生成）
   - 名稱：例如「手術刀」
   - 分類：選擇「手術耗材」
   - 單位：EA
   - 最小庫存：10
4. 提交

### 2. 進貨登記

1. 點擊「📥 進貨」
2. 選擇物品
3. 輸入數量
4. 提交

### 3. 記錄一台手術 🆕

1. 點擊「🏥 手術記錄」
2. 點擊「➕ 新增手術記錄」
3. 填寫資訊：
   ```
   病患姓名: 王小明
   手術類型: 闌尾切除術
   主刀醫師: 張醫師
   麻醉方式: 全身麻醉
   手術時長: 120 (分鐘)
   ```
4. 新增耗材（點擊「➕ 新增耗材」）：
   - 選擇物品
   - 輸入數量
5. 提交

**系統會自動:**
- 生成記錄編號：`20251105-王小明-1`
- 扣減耗材庫存
- 記錄庫存消耗事件

### 4. 查詢手術記錄

1. 在手術記錄分頁
2. 可選擇性設定日期範圍
3. 可選擇性輸入病患姓名搜尋
4. 點擊「詳情」查看完整資訊

### 5. 匯出 CSV 報表

1. 在手術記錄分頁
2. （可選）設定日期範圍
3. 點擊「📊 匯出 CSV」
4. 下載檔案到本機

---

## 🔧 常見問題排除

### Q1: 服務無法啟動
```bash
# 檢查 Python 版本
python3 --version  # 應該 >= 3.8

# 檢查套件安裝
python3 -c "import fastapi; print('FastAPI OK')"
python3 -c "import uvicorn; print('Uvicorn OK')"

# 檢查 port 8000 是否被佔用
sudo lsof -i :8000
```

### Q2: 瀏覽器無法連線
```bash
# 檢查服務是否運行
ps aux | grep main.py

# 檢查防火牆
sudo ufw status
sudo ufw allow 8000/tcp  # 如果需要開放

# 檢查 IP
hostname -I
```

### Q3: 資料庫錯誤
```bash
# 檢查資料庫檔案
ls -lh medical_inventory.db

# 如果損壞，還原備份
cp medical_inventory.db.backup medical_inventory.db

# 重新建立（會失去所有資料！）
rm medical_inventory.db
python3 main.py  # 會自動建立新的
```

### Q4: CSV 匯出亂碼（Excel）
Excel 開啟 CSV 時：
1. 選擇「資料」→「從文字/CSV」
2. 選擇匯出的檔案
3. 編碼選擇「UTF-8」
4. 確定

---

## 📊 效能建議

### 樹莓派 3/4
- 可流暢處理 100+ 物品
- 1000+ 庫存事件
- 500+ 手術記錄

### 樹莓派 Zero/1
- 建議物品數 < 50
- 定期清理舊記錄
- 考慮使用輕量級前端

---

## 🔐 安全建議

### 基本安全
```bash
# 1. 限制 IP 訪問（防火牆）
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw enable

# 2. 定期備份
crontab -e
# 新增這行（每天凌晨 2 點備份）
0 2 * * * cp /path/to/medical_inventory.db /path/to/backup/medical_inventory_$(date +\%Y\%m\%d).db
```

### 進階安全（生產環境）
- 使用 HTTPS（nginx + Let's Encrypt）
- 新增身份驗證（JWT Token）
- 設定 CORS 白名單

---

## 📱 使用技巧

### 1. 鍵盤快捷鍵
- `Tab` / `Shift+Tab`: 在表單欄位間移動
- `Enter`: 提交表單
- `Esc`: 關閉 Modal

### 2. 快速操作
- 代碼欄位留空 → 自動生成
- 雙擊物品 → 快速進貨
- Ctrl+點擊 → 新分頁開啟

### 3. 資料匯入（進階）
如有大量資料要匯入，可直接操作資料庫：
```bash
sqlite3 medical_inventory.db
.mode csv
.import your_data.csv items
```

---

## 🎓 學習資源

### API 文件
```
http://localhost:8000/docs
```
提供互動式 API 測試介面

### 資料庫結構
```bash
sqlite3 medical_inventory.db
.schema  # 查看所有表結構
```

---

## 📞 獲取協助

### 檢查日誌
```bash
# 查看最新日誌
tail -f medical_inventory.log

# 查看錯誤日誌
grep ERROR medical_inventory.log

# 查看最近 100 行
tail -n 100 medical_inventory.log
```

### 系統資訊
```bash
# Python 版本
python3 --version

# 套件版本
pip3 list | grep -E 'fastapi|uvicorn'

# 系統資源
free -h
df -h
```

---

## ✨ 更新到 v1.4.1 的原因

### 主要改進
1. **🏥 手術記錄管理** - 自動記錄、耗材追蹤
2. **📊 CSV 匯出** - 健保申報、統計分析
3. **🔢 自動編號** - 無需手動輸入記錄編號
4. **📅 日序管理** - 自動追蹤當日手術順序

### 向下相容
- ✅ 所有舊功能完全保留
- ✅ 資料庫自動遷移
- ✅ 無需手動調整設定

---

**🎉 恭喜！你已經成功部署 v1.4.1，可以開始使用了！**

**下一步:** 試著記錄第一台手術吧！ 🏥

---

**最後更新:** 2025-11-05  
**版本:** v1.4.1 Quick Start Guide
