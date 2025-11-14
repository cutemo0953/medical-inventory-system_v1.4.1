#!/bin/bash
#
# 測試封包格式驗證工具
#
# 測試所有驗證功能：
# - 有效的封包
# - 缺少必要欄位
# - 無效的 operation
# - 校驗碼驗證
#

echo "======================================================================"
echo "🧪 測試封包格式驗證工具"
echo "======================================================================"
echo ""

PASSED=0
FAILED=0

# 測試 1: 有效的封包
echo "測試 1: 有效的封包"
echo "----------------------------------------------------------------------"
if python3 scripts/validate_sync_package.py test_packages/valid_package.json > /dev/null 2>&1; then
    echo "✓ 測試通過"
    PASSED=$((PASSED + 1))
else
    echo "✗ 測試失敗：有效的封包被標記為無效"
    FAILED=$((FAILED + 1))
fi
echo ""

# 測試 2: 缺少必要欄位
echo "測試 2: 缺少必要欄位（應該失敗）"
echo "----------------------------------------------------------------------"
if python3 scripts/validate_sync_package.py test_packages/missing_fields.json > /dev/null 2>&1; then
    echo "✗ 測試失敗：缺少欄位的封包被標記為有效"
    FAILED=$((FAILED + 1))
else
    echo "✓ 測試通過：正確檢測到缺少欄位"
    PASSED=$((PASSED + 1))
fi
echo ""

# 測試 3: 無效的 operation
echo "測試 3: 無效的 operation（應該失敗）"
echo "----------------------------------------------------------------------"
if python3 scripts/validate_sync_package.py test_packages/invalid_operation.json > /dev/null 2>&1; then
    echo "✗ 測試失敗：無效的 operation 未被檢測"
    FAILED=$((FAILED + 1))
else
    echo "✓ 測試通過：正確檢測到無效的 operation"
    PASSED=$((PASSED + 1))
fi
echo ""

# 測試 4: 校驗碼驗證
echo "測試 4: 校驗碼驗證"
echo "----------------------------------------------------------------------"
if python3 scripts/validate_sync_package.py --verify-checksum test_packages/valid_checksum.json > /dev/null 2>&1; then
    echo "✓ 測試通過：校驗碼驗證成功"
    PASSED=$((PASSED + 1))
else
    echo "✗ 測試失敗：校驗碼驗證失敗"
    FAILED=$((FAILED + 1))
fi
echo ""

# 測試 5: 不存在的檔案
echo "測試 5: 不存在的檔案（應該失敗）"
echo "----------------------------------------------------------------------"
if python3 scripts/validate_sync_package.py test_packages/nonexistent.json > /dev/null 2>&1; then
    echo "✗ 測試失敗：不存在的檔案未被檢測"
    FAILED=$((FAILED + 1))
else
    echo "✓ 測試通過：正確檢測到檔案不存在"
    PASSED=$((PASSED + 1))
fi
echo ""

# 測試摘要
TOTAL=$((PASSED + FAILED))
echo "======================================================================"
echo "📊 測試摘要"
echo "======================================================================"
echo "總計: $TOTAL 測試"
echo "通過: $PASSED"
echo "失敗: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ 所有測試通過！"
    exit 0
else
    echo "❌ 部分測試失敗"
    exit 1
fi
