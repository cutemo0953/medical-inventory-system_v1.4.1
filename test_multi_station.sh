#!/bin/bash
# 多站點整合測試腳本
# Sprint 0+0.5 完整測試流程

set -e  # 遇到錯誤立即退出

echo "========================================================================"
echo "🏥 醫療庫存管理系統 - Sprint 0+0.5 整合測試"
echo "========================================================================"
echo ""

# ============================================================================
# Step 1: 清理舊測試資料
# ============================================================================
echo "Step 1: 清理舊測試資料..."
echo "------------------------------------------------------------------------"

rm -f database/test_*.db
rm -f config/test_*.json
rm -f exports/test_*.json

echo "✓ 清理完成"
echo ""

# ============================================================================
# Step 2: 創建 Station A 和 Station B 的配置檔案
# ============================================================================
echo "Step 2: 創建測試站點配置..."
echo "------------------------------------------------------------------------"

# Station A 配置
cat > config/test_station_a.json << 'EOF'
{
  "schema_version": "1.5.0",
  "station": {
    "uuid": "uuid-station-a",
    "code": "TEST-A",
    "name": "測試站點A",
    "station_type": "SECOND_CLASS",
    "admin_level": "STATION_LOCAL",
    "parent_node": null,
    "status": "ACTIVE",
    "created_at": null
  },
  "organization": {
    "uuid": null,
    "code": "TEST-ORG",
    "name": "測試組織",
    "type": "MILITARY"
  },
  "location": {
    "region_code": "TEST",
    "region_name": "測試區域",
    "address": null,
    "coordinates": {
      "latitude": null,
      "longitude": null
    }
  },
  "contact": {
    "primary_name": null,
    "primary_phone": null,
    "secondary_name": null,
    "secondary_phone": null,
    "emergency_contact": null
  },
  "database": {
    "general_inventory_path": "database/test_station_a_general.db",
    "pharmacy_path": "database/test_station_a_pharmacy.db",
    "backup_path": "database/backups",
    "export_path": "exports"
  },
  "system": {
    "timezone": "Asia/Taipei",
    "language": "zh-TW",
    "auto_backup_enabled": false,
    "auto_backup_interval_hours": 4,
    "max_backup_days": 7
  },
  "capabilities": {
    "beds": 50,
    "daily_capacity": 200,
    "has_pharmacy": true,
    "has_surgery": true,
    "has_icu": false,
    "has_emergency": true,
    "has_blood_bank": true,
    "can_store_controlled": true,
    "max_staff": 80,
    "storage_capacity_m3": 50,
    "backup_power": true,
    "satellite_comms": true
  }
}
EOF

# Station B 配置
cat > config/test_station_b.json << 'EOF'
{
  "schema_version": "1.5.0",
  "station": {
    "uuid": "uuid-station-b",
    "code": "TEST-B",
    "name": "測試站點B",
    "station_type": "THIRD_CLASS_BORP",
    "admin_level": "STATION_LOCAL",
    "parent_node": null,
    "status": "ACTIVE",
    "created_at": null
  },
  "organization": {
    "uuid": null,
    "code": "TEST-ORG",
    "name": "測試組織",
    "type": "MILITARY"
  },
  "location": {
    "region_code": "TEST",
    "region_name": "測試區域",
    "address": null,
    "coordinates": {
      "latitude": null,
      "longitude": null
    }
  },
  "contact": {
    "primary_name": null,
    "primary_phone": null,
    "secondary_name": null,
    "secondary_phone": null,
    "emergency_contact": null
  },
  "database": {
    "general_inventory_path": "database/test_station_b_general.db",
    "pharmacy_path": "database/test_station_b_pharmacy.db",
    "backup_path": "database/backups",
    "export_path": "exports"
  },
  "system": {
    "timezone": "Asia/Taipei",
    "language": "zh-TW",
    "auto_backup_enabled": false,
    "auto_backup_interval_hours": 4,
    "max_backup_days": 7
  },
  "capabilities": {
    "beds": 20,
    "daily_capacity": 50,
    "has_pharmacy": true,
    "has_surgery": false,
    "has_icu": false,
    "has_emergency": true,
    "has_blood_bank": false,
    "can_store_controlled": true,
    "max_staff": 30,
    "storage_capacity_m3": 20,
    "backup_power": true,
    "satellite_comms": true
  }
}
EOF

echo "✓ 創建 config/test_station_a.json"
echo "✓ 創建 config/test_station_b.json"
echo ""

# ============================================================================
# Step 3: 初始化兩個站點的資料庫
# ============================================================================
echo "Step 3: 初始化資料庫..."
echo "------------------------------------------------------------------------"

echo "初始化 Station A 資料庫..."
python3 scripts/init_databases.py config/test_station_a.json > /dev/null 2>&1
echo "✓ Station A 資料庫初始化完成"

echo "初始化 Station B 資料庫..."
python3 scripts/init_databases.py config/test_station_b.json > /dev/null 2>&1
echo "✓ Station B 資料庫初始化完成"

echo ""

# ============================================================================
# Step 4: 插入測試資料
# ============================================================================
echo "Step 4: 插入測試資料..."
echo "------------------------------------------------------------------------"

python3 << 'EOF'
import sqlite3

# ============================================================================
# Station A - Pharmacy
# ============================================================================
conn = sqlite3.connect('database/test_station_a_pharmacy.db')
cursor = conn.cursor()

# Morphine (管制藥)
cursor.execute("""
    INSERT INTO medicines (
        medicine_code, generic_name, brand_name, dosage_form, strength, unit,
        atc_code, is_controlled_drug, controlled_level,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'MED-001', 'Morphine', 'Morphine Sulfate', 'INJECTION', '10mg/ml', 'amp',
    'N02AA01', 1, 'LEVEL_1',
    100, 70, 50, 200,
    1
))

# Paracetamol
cursor.execute("""
    INSERT INTO medicines (
        medicine_code, generic_name, brand_name, dosage_form, strength, unit,
        atc_code, is_controlled_drug, controlled_level,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'MED-002', 'Paracetamol', 'Panadol', 'TABLET', '500mg', 'tab',
    'N02BE01', 0, None,
    500, 350, 200, 1000,
    1
))

conn.commit()
conn.close()
print("✓ Station A - Pharmacy: 插入 2 筆藥品 (Morphine, Paracetamol)")

# ============================================================================
# Station A - General
# ============================================================================
conn = sqlite3.connect('database/test_station_a_general.db')
cursor = conn.cursor()

# 紗布
cursor.execute("""
    INSERT INTO items (
        item_code, item_name, item_category, category, unit,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active, is_critical
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'ITEM-001', '紗布', 'CONSUMABLE', '醫療耗材', '包',
    200, 140, 100, 500,
    1, 1
))

# 氧氣鋼瓶
cursor.execute("""
    INSERT INTO items (
        item_code, item_name, item_category, category, unit,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active, is_critical
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'ITEM-002', '氧氣鋼瓶', 'EQUIPMENT', '醫療設備', '支',
    10, 7, 5, 20,
    1, 1
))

conn.commit()
conn.close()
print("✓ Station A - General: 插入 2 筆物品 (紗布, 氧氣鋼瓶)")

# ============================================================================
# Station B - Pharmacy
# ============================================================================
conn = sqlite3.connect('database/test_station_b_pharmacy.db')
cursor = conn.cursor()

# Morphine (管制藥)
cursor.execute("""
    INSERT INTO medicines (
        medicine_code, generic_name, brand_name, dosage_form, strength, unit,
        atc_code, is_controlled_drug, controlled_level,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'MED-001', 'Morphine', 'Morphine Sulfate', 'INJECTION', '10mg/ml', 'amp',
    'N02AA01', 1, 'LEVEL_1',
    50, 35, 25, 100,
    1
))

# Normal Saline
cursor.execute("""
    INSERT INTO medicines (
        medicine_code, generic_name, brand_name, dosage_form, strength, unit,
        atc_code, is_controlled_drug, controlled_level,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'MED-003', 'Normal Saline', 'NS 0.9%', 'INJECTION', '500ml', 'bag',
    'B05BB01', 0, None,
    300, 210, 150, 600,
    1
))

conn.commit()
conn.close()
print("✓ Station B - Pharmacy: 插入 2 筆藥品 (Morphine, Normal Saline)")

# ============================================================================
# Station B - General
# ============================================================================
conn = sqlite3.connect('database/test_station_b_general.db')
cursor = conn.cursor()

# 紗布
cursor.execute("""
    INSERT INTO items (
        item_code, item_name, item_category, category, unit,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active, is_critical
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'ITEM-001', '紗布', 'CONSUMABLE', '醫療耗材', '包',
    100, 70, 50, 300,
    1, 1
))

# IV Set
cursor.execute("""
    INSERT INTO items (
        item_code, item_name, item_category, category, unit,
        current_stock, baseline_qty_7days, min_stock, max_stock,
        is_active, is_critical
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'ITEM-003', 'IV Set', 'CONSUMABLE', '醫療耗材', '套',
    150, 105, 80, 400,
    1, 1
))

conn.commit()
conn.close()
print("✓ Station B - General: 插入 2 筆物品 (紗布, IV Set)")

EOF

echo ""

# ============================================================================
# Step 5: 使用 Service 創建交易
# ============================================================================
echo "Step 5: 創建交易記錄..."
echo "------------------------------------------------------------------------"

python3 << 'EOF'
from services.inventory_service import PharmacyService, GeneralInventoryService
from config.auth import UserRole

# Station A - Pharmacy: 管制藥出庫
pharmacy_service_a = PharmacyService('database/test_station_a_pharmacy.db')
tx1 = pharmacy_service_a.create_transaction(
    item_id='MED-001',
    transaction_type='OUT',
    quantity=10,
    operator='王藥師',
    operator_role='PHARMACIST',
    verified_by='李護理師',
    station_code='TEST-A',
    patient_id='P001',
    patient_name='張三',
    remarks='疼痛管理'
)
print(f"✓ Station A Pharmacy: Morphine 出庫 (交易ID: {tx1[:20]}...)")

# Station A - General: 紗布出庫
general_service_a = GeneralInventoryService('database/test_station_a_general.db')
tx2 = general_service_a.create_transaction(
    item_id='ITEM-001',
    transaction_type='OUT',
    quantity=20,
    operator='陳EMT',
    station_code='TEST-A',
    purpose='急診使用',
    remarks='緊急處置'
)
print(f"✓ Station A General: 紗布 出庫 (交易ID: {tx2[:20]}...)")

# Station B - Pharmacy: Normal Saline 出庫
pharmacy_service_b = PharmacyService('database/test_station_b_pharmacy.db')
tx3 = pharmacy_service_b.create_transaction(
    item_id='MED-003',
    transaction_type='OUT',
    quantity=15,
    operator='林護理師',
    operator_role='NURSE',
    station_code='TEST-B',
    patient_id='P002',
    patient_name='李四',
    remarks='靜脈輸液'
)
print(f"✓ Station B Pharmacy: Normal Saline 出庫 (交易ID: {tx3[:20]}...)")

# Station B - General: IV Set 入庫
general_service_b = GeneralInventoryService('database/test_station_b_general.db')
tx4 = general_service_b.create_transaction(
    item_id='ITEM-003',
    transaction_type='IN',
    quantity=50,
    operator='周後勤',
    station_code='TEST-B',
    reason='補貨',
    remarks='定期補充'
)
print(f"✓ Station B General: IV Set 入庫 (交易ID: {tx4[:20]}...)")

EOF

echo ""

# ============================================================================
# Step 6: 匯出兩個站點資料
# ============================================================================
echo "Step 6: 匯出站點資料..."
echo "------------------------------------------------------------------------"

echo "匯出 Station A..."
python3 scripts/export_station.py config/test_station_a.json exports/test_station_a_export.json > /dev/null 2>&1
echo "✓ Station A 資料匯出完成"

echo "匯出 Station B..."
python3 scripts/export_station.py config/test_station_b.json exports/test_station_b_export.json > /dev/null 2>&1
echo "✓ Station B 資料匯出完成"

echo ""

# ============================================================================
# Step 7: 驗證匯出格式
# ============================================================================
echo "Step 7: 驗證匯出格式..."
echo "------------------------------------------------------------------------"

python3 << 'EOF'
import json

def validate_export(filename, station_name):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 檢查必要欄位
    assert 'export_meta' in data, f"{station_name}: 缺少 export_meta"
    assert 'pharmacy_data' in data, f"{station_name}: 缺少 pharmacy_data"
    assert 'general_data' in data, f"{station_name}: 缺少 general_data"

    # 檢查 export_meta
    meta = data['export_meta']
    assert 'station_id' in meta, f"{station_name}: 缺少 station_id"
    assert 'station_name' in meta, f"{station_name}: 缺少 station_name"
    assert 'schema_version' in meta, f"{station_name}: 缺少 schema_version"

    # 檢查 pharmacy_data
    pharm = data['pharmacy_data']
    assert 'medicines' in pharm, f"{station_name}: 缺少 medicines"
    assert 'transactions' in pharm, f"{station_name}: 缺少 pharmacy transactions"
    assert 'controlled_drug_logs' in pharm, f"{station_name}: 缺少 controlled_drug_logs"
    assert 'record_count' in pharm, f"{station_name}: 缺少 pharmacy record_count"

    # 檢查 general_data
    general = data['general_data']
    assert 'items' in general, f"{station_name}: 缺少 items"
    assert 'transactions' in general, f"{station_name}: 缺少 general transactions"
    assert 'record_count' in general, f"{station_name}: 缺少 general record_count"

    print(f"✓ {station_name} 匯出格式驗證通過")
    print(f"  - Station ID: {meta['station_id']}")
    print(f"  - 藥品數: {pharm['record_count']['medicines']}")
    print(f"  - 藥品交易數: {pharm['record_count']['transactions']}")
    print(f"  - 管制藥記錄數: {pharm['record_count']['controlled_drug_logs']}")
    print(f"  - 物品數: {general['record_count']['items']}")
    print(f"  - 物品交易數: {general['record_count']['transactions']}")

validate_export('exports/test_station_a_export.json', 'Station A')
print()
validate_export('exports/test_station_b_export.json', 'Station B')

EOF

echo ""

# ============================================================================
# Step 8: 測試 coverage_days 計算
# ============================================================================
echo "Step 8: 測試 coverage_days 計算..."
echo "------------------------------------------------------------------------"

python3 << 'EOF'
from services.inventory_service import PharmacyService, GeneralInventoryService

# Station A - Pharmacy
pharmacy_service_a = PharmacyService('database/test_station_a_pharmacy.db')

# Morphine: current_stock=90 (100-10), baseline_qty_7days=70
# coverage_days = 90 / (70 / 7.0) = 90 / 10 = 9.0 days
coverage_morphine = pharmacy_service_a.calculate_coverage_days('MED-001')
print(f"✓ Station A Morphine: {coverage_morphine:.1f} 天")
assert abs(coverage_morphine - 9.0) < 0.1, f"計算錯誤: {coverage_morphine} != 9.0"

# Paracetamol: current_stock=500, baseline_qty_7days=350
# coverage_days = 500 / (350 / 7.0) = 500 / 50 = 10.0 days
coverage_paracetamol = pharmacy_service_a.calculate_coverage_days('MED-002')
print(f"✓ Station A Paracetamol: {coverage_paracetamol:.1f} 天")
assert abs(coverage_paracetamol - 10.0) < 0.1, f"計算錯誤: {coverage_paracetamol} != 10.0"

# Station A - General
general_service_a = GeneralInventoryService('database/test_station_a_general.db')

# 紗布: current_stock=180 (200-20), baseline_qty_7days=140
# coverage_days = 180 / (140 / 7.0) = 180 / 20 = 9.0 days
coverage_gauze = general_service_a.calculate_coverage_days('ITEM-001')
print(f"✓ Station A 紗布: {coverage_gauze:.1f} 天")
assert abs(coverage_gauze - 9.0) < 0.1, f"計算錯誤: {coverage_gauze} != 9.0"

# Station B - General
general_service_b = GeneralInventoryService('database/test_station_b_general.db')

# IV Set: current_stock=200 (150+50), baseline_qty_7days=105
# coverage_days = 200 / (105 / 7.0) = 200 / 15 = 13.33 days
coverage_iv = general_service_b.calculate_coverage_days('ITEM-003')
print(f"✓ Station B IV Set: {coverage_iv:.1f} 天")
assert abs(coverage_iv - 13.33) < 0.1, f"計算錯誤: {coverage_iv} != 13.33"

print()
print("✅ 所有 coverage_days 計算正確")

EOF

echo ""

# ============================================================================
# 完成總結
# ============================================================================
echo "========================================================================"
echo "✅ Multi-Station + Dual-Track Test Complete"
echo "========================================================================"
echo ""
echo "測試結果摘要："
echo "------------------------------------------------------------------------"
echo "資料庫檔案："
ls -lh database/test_*.db 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
echo ""
echo "配置檔案："
ls -lh config/test_*.json 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
echo ""
echo "匯出檔案："
ls -lh exports/test_*.json 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
echo ""
echo "========================================================================"
echo "🎉 Sprint 0+0.5 整合測試全部通過！"
echo "========================================================================"
