-- ============================================================================
-- Migration: Add Blood Management Tables
-- Version: 001
-- Created: 2025-11-14
-- Description: 添加血袋管理功能所需的表、視圖和索引
-- ============================================================================

-- ============================================================================
-- 1. 血袋庫存表 (Blood Inventory)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blood_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 血袋唯一識別
    blood_id TEXT NOT NULL UNIQUE,               -- 血袋唯一識別碼
    batch_number TEXT,                           -- 批號
    donation_number TEXT,                        -- 捐血袋號

    -- 血液資訊
    blood_type TEXT NOT NULL,                    -- 血型: A+, A-, B+, B-, AB+, AB-, O+, O-
    component_type TEXT DEFAULT 'WHOLE_BLOOD',   -- 血液成分: WHOLE_BLOOD, RBC, PLASMA, PLATELET, CRYO
    volume_ml INTEGER NOT NULL,                  -- 容量 (毫升)
    unit TEXT DEFAULT 'bag',                     -- 單位

    -- 站點與庫存狀態
    station_code TEXT NOT NULL,                  -- 當前站點代碼
    storage_location TEXT,                       -- 儲存位置
    status TEXT DEFAULT 'AVAILABLE',             -- 狀態: AVAILABLE, RESERVED, USED, EXPIRED, DESTROYED, TRANSFERRED

    -- 日期與效期
    collection_date DATE,                        -- 採集日期
    expiry_date DATE NOT NULL,                   -- 效期
    received_date DATE,                          -- 入庫日期

    -- 品質與檢驗
    quality_status TEXT DEFAULT 'PASSED',        -- 品質狀態: PASSED, PENDING, FAILED
    test_results TEXT,                           -- 檢驗結果 (JSON)
    temperature_log TEXT,                        -- 溫度記錄 (JSON)

    -- 來源與使用
    source_station TEXT,                         -- 來源站點
    source_type TEXT,                            -- 來源類型: DONATION, TRANSFER, PURCHASE
    patient_id TEXT,                             -- 使用病患ID (如已使用)
    usage_date TIMESTAMP,                        -- 使用日期

    -- 備註與追蹤
    remarks TEXT,                                -- 備註
    notes TEXT,                                  -- 其他說明
    created_by TEXT,                             -- 創建者
    updated_by TEXT,                             -- 更新者

    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 約束
    CHECK (blood_type IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    CHECK (component_type IN ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELET', 'CRYO')),
    CHECK (status IN ('AVAILABLE', 'RESERVED', 'USED', 'EXPIRED', 'DESTROYED', 'TRANSFERRED')),
    CHECK (quality_status IN ('PASSED', 'PENDING', 'FAILED')),
    CHECK (source_type IN ('DONATION', 'TRANSFER', 'PURCHASE'))
);

-- 血袋庫存索引
CREATE INDEX IF NOT EXISTS idx_blood_station ON blood_inventory(station_code);
CREATE INDEX IF NOT EXISTS idx_blood_type ON blood_inventory(blood_type);
CREATE INDEX IF NOT EXISTS idx_blood_status ON blood_inventory(status);
CREATE INDEX IF NOT EXISTS idx_blood_expiry ON blood_inventory(expiry_date);

-- ============================================================================
-- 2. 血袋事件記錄表 (Blood Events)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blood_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 事件識別
    event_id TEXT NOT NULL UNIQUE,               -- 事件唯一識別碼
    blood_id TEXT NOT NULL,                      -- 血袋識別碼

    -- 事件類型與詳情
    event_type TEXT NOT NULL,                    -- 事件類型: RECEIVED, TRANSFERRED, USED, EXPIRED, DESTROYED, QUALITY_CHECK, RESERVED, RELEASED
    event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 數量與站點
    quantity INTEGER DEFAULT 1,                  -- 數量 (通常為1，表示1袋血)
    from_station TEXT,                           -- 來源站點
    to_station TEXT,                             -- 目標站點
    station_code TEXT,                           -- 當前站點

    -- 操作人員
    operator TEXT,                               -- 操作人員
    operator_role TEXT,                          -- 操作人員角色
    verified_by TEXT,                            -- 核驗人員

    -- 病患資訊 (使用時)
    patient_id TEXT,                             -- 病患ID
    patient_name TEXT,                           -- 病患姓名
    blood_type_match TEXT,                       -- 血型配對記錄

    -- 品質檢查 (品質檢查事件)
    quality_result TEXT,                         -- 品質檢查結果
    temperature REAL,                            -- 溫度記錄

    -- 備註與原因
    remarks TEXT,                                -- 備註
    reason TEXT,                                 -- 原因/理由
    notes TEXT,                                  -- 其他說明

    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,

    -- 外鍵
    FOREIGN KEY (blood_id) REFERENCES blood_inventory(blood_id),

    -- 約束
    CHECK (event_type IN ('RECEIVED', 'TRANSFERRED', 'USED', 'EXPIRED', 'DESTROYED', 'QUALITY_CHECK', 'RESERVED', 'RELEASED'))
);

-- 血袋事件索引
CREATE INDEX IF NOT EXISTS idx_blood_events_blood_id ON blood_events(blood_id);
CREATE INDEX IF NOT EXISTS idx_blood_events_type ON blood_events(event_type);
CREATE INDEX IF NOT EXISTS idx_blood_events_date ON blood_events(event_date);
CREATE INDEX IF NOT EXISTS idx_blood_events_station ON blood_events(station_code);

-- ============================================================================
-- 3. 血袋庫存視圖
-- ============================================================================

-- 可用血袋統計視圖
CREATE VIEW IF NOT EXISTS v_blood_inventory_summary AS
SELECT
    station_code,
    blood_type,
    component_type,
    COUNT(*) AS total_bags,
    SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_bags,
    SUM(CASE WHEN status = 'RESERVED' THEN 1 ELSE 0 END) AS reserved_bags,
    SUM(volume_ml) AS total_volume_ml,
    MIN(expiry_date) AS earliest_expiry,
    MAX(expiry_date) AS latest_expiry
FROM blood_inventory
WHERE status IN ('AVAILABLE', 'RESERVED')
GROUP BY station_code, blood_type, component_type;

-- 血袋過期警示視圖
CREATE VIEW IF NOT EXISTS v_blood_expiry_alert AS
SELECT
    blood_id,
    batch_number,
    blood_type,
    component_type,
    volume_ml,
    station_code,
    expiry_date,
    CAST((JULIANDAY(expiry_date) - JULIANDAY('now')) AS INTEGER) AS days_to_expiry,
    status,
    storage_location
FROM blood_inventory
WHERE status = 'AVAILABLE'
    AND expiry_date <= DATE('now', '+7 days')
ORDER BY expiry_date;

-- 血袋事件歷史視圖
CREATE VIEW IF NOT EXISTS v_blood_event_history AS
SELECT
    e.event_id,
    e.blood_id,
    b.blood_type,
    b.component_type,
    e.event_type,
    e.event_date,
    e.from_station,
    e.to_station,
    e.operator,
    e.patient_id,
    e.patient_name,
    e.remarks,
    b.status AS current_status
FROM blood_events e
LEFT JOIN blood_inventory b ON e.blood_id = b.blood_id
ORDER BY e.event_date DESC;

-- ============================================================================
-- 4. 血袋庫存觸發器
-- ============================================================================

-- 自動更新 blood_inventory.updated_at
CREATE TRIGGER IF NOT EXISTS update_blood_inventory_timestamp
AFTER UPDATE ON blood_inventory
FOR EACH ROW
BEGIN
    UPDATE blood_inventory SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- Migration 完成
-- ============================================================================
