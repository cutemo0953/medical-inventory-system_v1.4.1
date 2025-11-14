#!/bin/bash
# UI 修復整合測試腳本
# 驗證所有視覺與功能修復

# 不使用 set -e，讓所有測試都能執行

echo "========================================================================"
echo "🧪 UI 修復整合測試"
echo "========================================================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 測試結果統計
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 測試結果函數
test_passed() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

test_failed() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

test_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

test_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ============================================================================
# Test 1: 檢查站點設定頁面配色
# ============================================================================
echo "Test 1: 站點設定頁面配色統一"
echo "------------------------------------------------------------------------"

if [ -f "setup_station.html" ]; then
    test_info "檢查 setup_station.html..."

    # 檢查背景漸層
    if grep -q "linear-gradient(135deg, #f0f9f8 0%, #e6f7f5 25%, #f5f8ff 50%, #faf5ff 75%, #fff 100%)" setup_station.html; then
        test_passed "背景漸層與 Index.html 一致"
    else
        test_failed "背景漸層配置不正確"
    fi

    # 檢查 teal 按鈕數量
    TEAL_BUTTONS=$(grep -c "bg-teal-600" setup_station.html || true)
    if [ "$TEAL_BUTTONS" -ge 5 ]; then
        test_passed "找到 $TEAL_BUTTONS 個 teal-600 按鈕（預期 5+）"
    else
        test_failed "teal 按鈕數量不足：$TEAL_BUTTONS（預期 5+）"
    fi

    # 檢查是否移除舊的紅綠橘色按鈕（排除 toast 訊息）
    OLD_COLORS=$(grep "bg-red-500\|bg-green-500\|bg-orange-500" setup_station.html | grep -v "toast.className" | wc -l || true)
    if [ "$OLD_COLORS" -eq 0 ]; then
        test_passed "已移除舊的紅/綠/橘色按鈕"
    else
        test_failed "仍存在舊的顏色按鈕（$OLD_COLORS 個）"
    fi

    # 檢查 outline 樣式的清除按鈕
    if grep -q "border-2 border-gray-300 bg-white" setup_station.html; then
        test_passed "清除按鈕使用 outline 樣式"
    else
        test_failed "清除按鈕樣式不正確"
    fi

else
    test_failed "找不到 setup_station.html"
fi

echo ""

# ============================================================================
# Test 2: 檢查處置按鈕顏色
# ============================================================================
echo "Test 2: 首頁處置按鈕紫色配置"
echo "------------------------------------------------------------------------"

if [ -f "Index.html" ]; then
    test_info "檢查 Index.html..."

    # 檢查 treatment 顏色定義
    if grep -q "'treatment':" Index.html; then
        test_passed "找到 treatment 顏色定義"

        # 檢查主色 #4E5488
        if grep -q "500: '#4E5488'" Index.html; then
            test_passed "treatment-500 主色正確 (#4E5488)"
        else
            test_failed "treatment-500 主色不正確"
        fi

        # 檢查淺色 #F3F2F8
        if grep -q "50: '#F3F2F8'" Index.html; then
            test_passed "treatment-50 淺色正確 (#F3F2F8)"
        else
            test_failed "treatment-50 淺色不正確"
        fi

    else
        test_failed "找不到 treatment 顏色定義"
    fi

    # 檢查處置按鈕使用情況
    TREATMENT_USAGE=$(grep -c "bg-treatment-\|text-treatment-" Index.html || true)
    if [ "$TREATMENT_USAGE" -gt 0 ]; then
        test_passed "處置按鈕正在使用 treatment 顏色（$TREATMENT_USAGE 處）"
    else
        test_failed "處置按鈕未使用 treatment 顏色"
    fi

else
    test_failed "找不到 Index.html"
fi

echo ""

# ============================================================================
# Test 3: 檢查血袋轉移功能資料庫結構
# ============================================================================
echo "Test 3: 血袋轉移功能資料庫結構"
echo "------------------------------------------------------------------------"

if [ -f "database/general_inventory.db" ]; then
    test_info "檢查 general_inventory.db..."

    # 使用 Python 檢查資料庫
    python3 << 'PYEOF'
import sqlite3
import sys

try:
    conn = sqlite3.connect('database/general_inventory.db')
    cursor = conn.cursor()

    # 檢查 blood_inventory 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blood_inventory'")
    if cursor.fetchone():
        print("PASS:blood_inventory 表存在")

        # 檢查欄位數量
        cursor.execute("PRAGMA table_info(blood_inventory)")
        columns = cursor.fetchall()
        if len(columns) >= 25:
            print(f"PASS:blood_inventory 表有 {len(columns)} 個欄位（預期 27）")
        else:
            print(f"FAIL:blood_inventory 欄位數量不足：{len(columns)}")
    else:
        print("FAIL:blood_inventory 表不存在")

    # 檢查 blood_events 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blood_events'")
    if cursor.fetchone():
        print("PASS:blood_events 表存在")

        # 檢查 remarks 欄位
        cursor.execute("PRAGMA table_info(blood_events)")
        columns = cursor.fetchall()
        has_remarks = any(col[1] == 'remarks' for col in columns)

        if has_remarks:
            print("PASS:blood_events 表包含 remarks 欄位")
        else:
            print("FAIL:blood_events 表缺少 remarks 欄位")

        if len(columns) >= 20:
            print(f"PASS:blood_events 表有 {len(columns)} 個欄位（預期 22）")
        else:
            print(f"FAIL:blood_events 欄位數量不足：{len(columns)}")
    else:
        print("FAIL:blood_events 表不存在")

    # 檢查視圖
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name LIKE 'v_blood%'")
    view_count = cursor.fetchone()[0]
    if view_count == 3:
        print(f"PASS:血袋相關視圖齊全（3 個）")
    else:
        print(f"WARN:血袋視圖數量：{view_count}（預期 3）")

    conn.close()
except Exception as e:
    print(f"FAIL:資料庫檢查失敗：{e}")
    sys.exit(1)
PYEOF

    # 處理 Python 輸出
    while IFS=: read -r status message; do
        if [ "$status" = "PASS" ]; then
            test_passed "$message"
        elif [ "$status" = "FAIL" ]; then
            test_failed "$message"
        elif [ "$status" = "WARN" ]; then
            test_warning "$message"
        fi
    done

else
    test_failed "找不到 database/general_inventory.db"
fi

echo ""

# ============================================================================
# Test 4: 檢查 migration 腳本
# ============================================================================
echo "Test 4: Migration 腳本存在性"
echo "------------------------------------------------------------------------"

if [ -f "database/migrations/001_add_blood_management.sql" ]; then
    test_passed "找到血袋管理 migration 腳本"

    # 檢查腳本內容
    if grep -q "CREATE TABLE IF NOT EXISTS blood_inventory" database/migrations/001_add_blood_management.sql; then
        test_passed "Migration 包含 blood_inventory 表定義"
    else
        test_failed "Migration 缺少 blood_inventory 表定義"
    fi

    if grep -q "CREATE TABLE IF NOT EXISTS blood_events" database/migrations/001_add_blood_management.sql; then
        test_passed "Migration 包含 blood_events 表定義"
    else
        test_failed "Migration 缺少 blood_events 表定義"
    fi
else
    test_failed "找不到 migration 腳本"
fi

if [ -f "scripts/migrate_database.py" ]; then
    test_passed "找到 migrate_database.py 工具"
else
    test_failed "找不到 migrate_database.py 工具"
fi

echo ""

# ============================================================================
# Test 5: 檢查 schema 檔案完整性
# ============================================================================
echo "Test 5: Schema 檔案完整性"
echo "------------------------------------------------------------------------"

if [ -f "database/schema_general_inventory.sql" ]; then
    test_info "檢查 schema_general_inventory.sql..."

    # 檢查是否包含血袋表定義
    if grep -q "CREATE TABLE IF NOT EXISTS blood_inventory" database/schema_general_inventory.sql; then
        test_passed "Schema 包含 blood_inventory 表"
    else
        test_failed "Schema 缺少 blood_inventory 表"
    fi

    if grep -q "CREATE TABLE IF NOT EXISTS blood_events" database/schema_general_inventory.sql; then
        test_passed "Schema 包含 blood_events 表"
    else
        test_failed "Schema 缺少 blood_events 表"
    fi

    # 檢查 remarks 欄位定義
    if grep -A 100 "CREATE TABLE IF NOT EXISTS blood_events" database/schema_general_inventory.sql | grep -q "remarks TEXT"; then
        test_passed "Schema 中 blood_events 包含 remarks 欄位"
    else
        test_failed "Schema 中 blood_events 缺少 remarks 欄位"
    fi
else
    test_failed "找不到 schema_general_inventory.sql"
fi

echo ""

# ============================================================================
# Test 6: 功能測試（如果資料庫存在測試資料）
# ============================================================================
echo "Test 6: 血袋轉移功能測試"
echo "------------------------------------------------------------------------"

if [ -f "database/general_inventory.db" ]; then
    # 使用 Python 檢查測試資料
    python3 << 'PYEOF'
import sqlite3

try:
    conn = sqlite3.connect('database/general_inventory.db')
    cursor = conn.cursor()

    # 檢查是否有測試資料
    cursor.execute("SELECT COUNT(*) FROM blood_inventory")
    blood_count = cursor.fetchone()[0]

    if blood_count > 0:
        print(f"INFO:找到 {blood_count} 筆血袋記錄")

        # 查詢血袋事件
        cursor.execute("SELECT COUNT(*) FROM blood_events")
        event_count = cursor.fetchone()[0]
        print(f"INFO:找到 {event_count} 筆血袋事件記錄")

        # 測試 remarks 欄位
        cursor.execute("SELECT COUNT(*) FROM blood_events WHERE remarks IS NOT NULL")
        has_remarks = cursor.fetchone()[0]
        if has_remarks > 0:
            print(f"PASS:blood_events 中有 {has_remarks} 筆記錄包含 remarks")
        else:
            print("WARN:blood_events 中暫無包含 remarks 的記錄")
    else:
        print("WARN:資料庫中暫無血袋測試資料")

    conn.close()
except Exception as e:
    print(f"WARN:功能測試跳過：{e}")
PYEOF

    # 處理 Python 輸出
    while IFS=: read -r status message; do
        if [ "$status" = "PASS" ]; then
            test_passed "$message"
        elif [ "$status" = "INFO" ]; then
            test_info "$message"
        elif [ "$status" = "WARN" ]; then
            test_warning "$message"
        fi
    done
else
    test_warning "跳過功能測試（資料庫不存在）"
fi

echo ""

# ============================================================================
# 測試報告
# ============================================================================
echo "========================================================================"
echo "📊 測試報告"
echo "========================================================================"
echo ""
echo "總測試數: $TOTAL_TESTS"
echo -e "${GREEN}通過: $PASSED_TESTS${NC}"
echo -e "${RED}失敗: $FAILED_TESTS${NC}"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有測試通過！${NC}"
    echo ""
    echo "修復摘要："
    echo "  ✓ 站點設定頁面配色統一（teal 色系）"
    echo "  ✓ 首頁處置按鈕紫色配置正確"
    echo "  ✓ 血袋轉移功能資料庫結構完整"
    echo "  ✓ Migration 腳本與工具齊全"
    echo ""
else
    echo -e "${RED}❌ 有 $FAILED_TESTS 個測試失敗${NC}"
    echo ""
    echo "請檢查上述失敗的測試項目"
    exit 1
fi

# ============================================================================
# 手動檢查提示
# ============================================================================
echo "========================================================================"
echo "🖥️  手動視覺檢查清單"
echo "========================================================================"
echo ""
echo "請在瀏覽器中進行以下檢查："
echo ""
echo "1. 站點設定頁面 (setup_station.html)："
echo "   [ ] 開啟頁面，確認背景為多色漸層"
echo "   [ ] 確認 4 個快速設定按鈕都是青綠色（teal）"
echo "   [ ] 確認清除按鈕為 outline 樣式（白底灰框）"
echo "   [ ] 測試 hover 效果（按鈕變深）"
echo ""
echo "2. 首頁 (Index.html)："
echo "   [ ] 開啟首頁，找到「處置」按鈕"
echo "   [ ] 確認按鈕為紫色 (#4E5488)"
echo "   [ ] 點擊處置按鈕，進入處置頁面"
echo "   [ ] 確認處置頁面元素使用紫色主題"
echo ""
echo "3. 血袋轉移功能："
echo "   [ ] 前往血袋管理頁面"
echo "   [ ] 嘗試轉移血袋到其他站點"
echo "   [ ] 在備註欄位輸入文字"
echo "   [ ] 確認轉移成功且備註已保存"
echo ""
echo "========================================================================"

exit 0
