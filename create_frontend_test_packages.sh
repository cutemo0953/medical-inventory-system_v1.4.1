#!/bin/bash
#
# 創建前端測試封包
#
# 此腳本會創建多個測試封包，用於測試前端的上傳驗證邏輯
#

echo "======================================================================"
echo "🧪 創建前端測試封包"
echo "======================================================================"
echo ""

# 創建測試目錄
mkdir -p frontend_test_packages
cd frontend_test_packages

# 1. 有效的測試封包
echo "1. 創建有效的測試封包..."
python3 << 'EOF'
import json
import hashlib

changes = [
    {
        'table': 'items',
        'operation': 'INSERT',
        'data': {
            'item_code': 'FRONTEND-TEST-001',
            'item_name': '前端測試物品',
            'current_stock': 100,
            'unit': '包'
        },
        'timestamp': '2025-11-14T15:00:00'
    }
]

package_content = json.dumps(changes, ensure_ascii=False, sort_keys=True)
checksum = hashlib.sha256(package_content.encode('utf-8')).hexdigest()

package = {
    'success': True,
    'package_id': 'PKG-FRONTEND-TEST-001',
    'package_type': 'DELTA',
    'package_size': len(package_content.encode('utf-8')),
    'checksum': checksum,
    'changes_count': len(changes),
    'changes': changes,
    'message': '前端測試封包'
}

with open('valid_frontend_test.json', 'w', encoding='utf-8') as f:
    json.dump(package, f, ensure_ascii=False, indent=2)

print('✓ valid_frontend_test.json')
EOF

# 2. 缺少 checksum 的封包
echo "2. 創建缺少 checksum 的封包..."
cat > missing_checksum.json << 'EOF'
{
  "success": true,
  "package_id": "PKG-MISSING-CHECKSUM",
  "package_type": "DELTA",
  "changes_count": 1,
  "changes": [
    {
      "table": "items",
      "operation": "INSERT",
      "data": {"item_code": "TEST001"},
      "timestamp": "2025-11-14T15:00:00"
    }
  ]
}
EOF
echo "✓ missing_checksum.json"

# 3. changes 不是陣列
echo "3. 創建 changes 不是陣列的封包..."
cat > changes_not_array.json << 'EOF'
{
  "success": true,
  "package_id": "PKG-INVALID-CHANGES",
  "package_type": "DELTA",
  "checksum": "abc123def4567890123456789012345678901234567890123456789012345678",
  "changes_count": 1,
  "changes": "not an array"
}
EOF
echo "✓ changes_not_array.json"

# 4. 變更記錄缺少 operation
echo "4. 創建變更記錄缺少 operation 的封包..."
python3 << 'EOF'
import json
import hashlib

changes = [
    {
        'table': 'items',
        # 缺少 operation
        'data': {'item_code': 'TEST001'},
        'timestamp': '2025-11-14T15:00:00'
    }
]

package_content = json.dumps(changes, ensure_ascii=False, sort_keys=True)
checksum = hashlib.sha256(package_content.encode('utf-8')).hexdigest()

package = {
    'success': True,
    'package_id': 'PKG-MISSING-OPERATION',
    'package_type': 'DELTA',
    'package_size': len(package_content.encode('utf-8')),
    'checksum': checksum,
    'changes_count': len(changes),
    'changes': changes,
    'message': '缺少 operation'
}

with open('missing_operation.json', 'w', encoding='utf-8') as f:
    json.dump(package, f, ensure_ascii=False, indent=2)

print('✓ missing_operation.json')
EOF

# 5. 無效的 operation 值
echo "5. 創建無效 operation 值的封包..."
python3 << 'EOF'
import json
import hashlib

changes = [
    {
        'table': 'items',
        'operation': 'INVALID_OP',  # 無效的 operation
        'data': {'item_code': 'TEST001'},
        'timestamp': '2025-11-14T15:00:00'
    }
]

package_content = json.dumps(changes, ensure_ascii=False, sort_keys=True)
checksum = hashlib.sha256(package_content.encode('utf-8')).hexdigest()

package = {
    'success': True,
    'package_id': 'PKG-INVALID-OPERATION',
    'package_type': 'DELTA',
    'package_size': len(package_content.encode('utf-8')),
    'checksum': checksum,
    'changes_count': len(changes),
    'changes': changes,
    'message': '無效的 operation'
}

with open('invalid_operation_value.json', 'w', encoding='utf-8') as f:
    json.dump(package, f, ensure_ascii=False, indent=2)

print('✓ invalid_operation_value.json')
EOF

# 6. 損壞的 JSON
echo "6. 創建損壞的 JSON..."
cat > broken_json.json << 'EOF'
{
  "success": true,
  "package_id": "PKG-BROKEN",
  this is not valid json
}
EOF
echo "✓ broken_json.json"

# 7. 非 JSON 檔案
echo "7. 創建非 JSON 檔案..."
echo "This is a text file, not JSON" > test.txt
echo "✓ test.txt"

cd ..

echo ""
echo "======================================================================"
echo "📦 測試封包已創建"
echo "======================================================================"
echo ""
echo "位置: frontend_test_packages/"
echo ""
echo "測試案例："
echo "  1. ✅ valid_frontend_test.json       - 有效的封包"
echo "  2. ❌ missing_checksum.json          - 缺少 checksum"
echo "  3. ❌ changes_not_array.json         - changes 不是陣列"
echo "  4. ❌ missing_operation.json         - 缺少 operation 欄位"
echo "  5. ❌ invalid_operation_value.json   - 無效的 operation 值"
echo "  6. ❌ broken_json.json               - 損壞的 JSON"
echo "  7. ❌ test.txt                       - 非 JSON 檔案"
echo ""
echo "使用方式："
echo "  1. 啟動後端: python3 main.py"
echo "  2. 開啟瀏覽器: http://localhost:8000"
echo "  3. 打開 DevTools (F12) > Console 標籤"
echo "  4. 在「匯入同步封包」區塊上傳測試檔案"
echo "  5. 觀察 Console 日誌和錯誤訊息"
echo ""
echo "更多資訊: FRONTEND_SYNC_TEST_GUIDE.md"
echo ""
