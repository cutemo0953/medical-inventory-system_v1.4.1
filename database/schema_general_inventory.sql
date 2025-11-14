-- ============================================================================
-- 一般庫存資料庫 Schema (General Inventory Database)
-- Version: 1.5.0
-- 用途: 衛材、設備、試劑等非藥品物資管理
-- ============================================================================

-- ============================================================================
-- 1. 站點後設資料表 (Station Metadata)
-- ============================================================================
CREATE TABLE IF NOT EXISTS station_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 基本資訊
    station_uuid TEXT UNIQUE,                    -- 站點全域唯一識別碼
    station_code TEXT NOT NULL UNIQUE,           -- 站點代碼 (如: TC-01)
    station_name TEXT NOT NULL,                  -- 站點名稱

    -- 站點分類
    station_type TEXT NOT NULL,                  -- 站點類型: FIRST_CLASS, SECOND_CLASS, THIRD_CLASS_BORP
    admin_level TEXT NOT NULL,                   -- 管理層級: STATION_LOCAL, DISTRICT, COUNTY, MOHW
    parent_node TEXT,                            -- 上級節點站點代碼

    -- 組織資訊
    organization_code TEXT,                      -- 組織代碼
    organization_name TEXT,                      -- 組織名稱
    region_code TEXT,                            -- 區域代碼
    region_name TEXT,                            -- 區域名稱

    -- 能力配置
    beds INTEGER DEFAULT 0,                      -- 床位數
    daily_capacity INTEGER DEFAULT 0,            -- 每日門診量
    has_pharmacy BOOLEAN DEFAULT 0,              -- 是否有藥局
    has_surgery BOOLEAN DEFAULT 0,               -- 是否有手術室
    has_emergency BOOLEAN DEFAULT 0,             -- 是否有急診
    storage_capacity_m3 REAL DEFAULT 0,          -- 儲存空間（立方公尺）

    -- 狀態與時間戳
    status TEXT DEFAULT 'ACTIVE',                -- 狀態: ACTIVE, INACTIVE, MAINTENANCE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP,                      -- 最後同步時間

    -- 版本控制
    schema_version TEXT DEFAULT '1.5.0',
    data_version INTEGER DEFAULT 1,

    -- 索引
    CHECK (station_type IN ('FIRST_CLASS', 'SECOND_CLASS', 'THIRD_CLASS_BORP')),
    CHECK (admin_level IN ('STATION_LOCAL', 'DISTRICT', 'COUNTY', 'MOHW')),
    CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE'))
);

CREATE INDEX IF NOT EXISTS idx_station_code ON station_metadata(station_code);
CREATE INDEX IF NOT EXISTS idx_station_type ON station_metadata(station_type);
CREATE INDEX IF NOT EXISTS idx_admin_level ON station_metadata(admin_level);

-- ============================================================================
-- 2. 物品主檔表 (Items Master)
-- ============================================================================
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 基本資訊
    item_code TEXT NOT NULL UNIQUE,              -- 物品代碼
    item_name TEXT NOT NULL,                     -- 物品名稱
    item_name_en TEXT,                           -- 英文名稱

    -- 分類
    item_category TEXT NOT NULL,                 -- 物品類別: CONSUMABLE（耗材）, EQUIPMENT（設備）, REAGENT（試劑）
    category TEXT,                                -- 次分類（如：繃帶、手套、消毒用品等）
    subcategory TEXT,                            -- 子分類

    -- 規格
    specification TEXT,                          -- 規格說明
    unit TEXT NOT NULL DEFAULT '個',             -- 單位
    unit_en TEXT,                                -- 英文單位
    package_size INTEGER DEFAULT 1,              -- 包裝數量

    -- 儲存與管理
    storage_location TEXT,                       -- 儲存位置
    storage_temp_min REAL,                       -- 最低儲存溫度（℃）
    storage_temp_max REAL,                       -- 最高儲存溫度（℃）
    storage_humidity_max INTEGER,                -- 最高儲存濕度（%）

    -- 庫存管理
    baseline_qty_7days INTEGER DEFAULT 0,        -- 7天標準儲備量（重點欄位）
    min_stock INTEGER DEFAULT 0,                 -- 最低庫存量
    max_stock INTEGER DEFAULT 0,                 -- 最高庫存量
    reorder_point INTEGER DEFAULT 0,             -- 再訂購點
    current_stock INTEGER DEFAULT 0,             -- 當前庫存
    reserved_stock INTEGER DEFAULT 0,            -- 保留庫存
    available_stock INTEGER GENERATED ALWAYS AS (current_stock - reserved_stock) VIRTUAL,

    -- 供應商資訊
    supplier_code TEXT,                          -- 供應商代碼
    supplier_name TEXT,                          -- 供應商名稱
    manufacturer TEXT,                           -- 製造商
    country_of_origin TEXT,                      -- 產地

    -- 成本與價格
    unit_cost REAL DEFAULT 0,                    -- 單位成本
    unit_price REAL DEFAULT 0,                   -- 單位售價
    currency TEXT DEFAULT 'TWD',                 -- 幣別

    -- 效期管理
    has_expiry BOOLEAN DEFAULT 0,                -- 是否有效期
    default_shelf_life_days INTEGER,             -- 預設保存期限（天）
    nearest_expiry_date DATE,                    -- 最近效期

    -- 標籤與追溯
    barcode TEXT,                                -- 條碼
    qr_code TEXT,                                -- QR Code
    lot_number TEXT,                             -- 批號
    serial_number TEXT,                          -- 序號
    is_traceable BOOLEAN DEFAULT 0,              -- 是否需追溯

    -- 狀態與標記
    is_active BOOLEAN DEFAULT 1,                 -- 是否啟用
    is_critical BOOLEAN DEFAULT 0,               -- 是否為關鍵物資
    is_controlled BOOLEAN DEFAULT 0,             -- 是否為管制物品
    requires_cold_chain BOOLEAN DEFAULT 0,       -- 是否需冷鏈
    is_hazardous BOOLEAN DEFAULT 0,              -- 是否為危險品

    -- 備註
    description TEXT,                            -- 描述
    usage_notes TEXT,                            -- 使用說明
    safety_notes TEXT,                           -- 安全注意事項
    remarks TEXT,                                -- 備註

    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,

    -- 約束
    CHECK (item_category IN ('CONSUMABLE', 'EQUIPMENT', 'REAGENT')),
    CHECK (current_stock >= 0),
    CHECK (reserved_stock >= 0),
    CHECK (unit_cost >= 0),
    CHECK (unit_price >= 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_item_code ON items(item_code);
CREATE INDEX IF NOT EXISTS idx_item_name ON items(item_name);
CREATE INDEX IF NOT EXISTS idx_item_category ON items(item_category);
CREATE INDEX IF NOT EXISTS idx_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_barcode ON items(barcode);
CREATE INDEX IF NOT EXISTS idx_is_active ON items(is_active);
CREATE INDEX IF NOT EXISTS idx_is_critical ON items(is_critical);
CREATE INDEX IF NOT EXISTS idx_current_stock ON items(current_stock);

-- ============================================================================
-- 3. 交易記錄表 (Transactions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 交易基本資訊
    transaction_id TEXT NOT NULL UNIQUE,         -- 交易唯一識別碼
    transaction_type TEXT NOT NULL,              -- 交易類型: IN（入庫）, OUT（出庫）, TRANSFER（調撥）, ADJUST（調整）, RETURN（退貨）
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 物品資訊
    item_code TEXT NOT NULL,                     -- 物品代碼
    item_name TEXT NOT NULL,                     -- 物品名稱
    item_category TEXT,                          -- 物品類別

    -- 數量與單位
    quantity INTEGER NOT NULL,                   -- 數量
    unit TEXT NOT NULL,                          -- 單位

    -- 站點資訊
    station_code TEXT NOT NULL,                  -- 站點代碼
    from_station TEXT,                           -- 來源站點（調撥用）
    to_station TEXT,                             -- 目標站點（調撥用）

    -- 批次與效期
    batch_number TEXT,                           -- 批號
    lot_number TEXT,                             -- 批次號
    expiry_date DATE,                            -- 效期

    -- 成本與價格
    unit_cost REAL DEFAULT 0,                    -- 單位成本
    total_cost REAL GENERATED ALWAYS AS (quantity * unit_cost) VIRTUAL,

    -- 儲存位置
    storage_location TEXT,                       -- 儲存位置

    -- 原因與用途
    reason TEXT,                                 -- 交易原因
    purpose TEXT,                                -- 用途（出庫時）
    patient_id TEXT,                             -- 病患ID（用於病患使用時）
    patient_name TEXT,                           -- 病患姓名

    -- 參考資料
    reference_doc TEXT,                          -- 參考單據號碼
    related_transaction_id TEXT,                 -- 關聯交易ID

    -- 操作者資訊
    operator TEXT NOT NULL,                      -- 操作人員
    operator_role TEXT,                          -- 操作人員角色
    approved_by TEXT,                            -- 核准人員

    -- 狀態
    status TEXT DEFAULT 'COMPLETED',             -- 狀態: PENDING, COMPLETED, CANCELLED, REVERSED

    -- 備註
    remarks TEXT,                                -- 備註

    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,

    -- 外鍵
    FOREIGN KEY (item_code) REFERENCES items(item_code) ON DELETE RESTRICT,

    -- 約束
    CHECK (transaction_type IN ('IN', 'OUT', 'TRANSFER', 'ADJUST', 'RETURN')),
    CHECK (quantity > 0),
    CHECK (status IN ('PENDING', 'COMPLETED', 'CANCELLED', 'REVERSED'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_transaction_id ON transactions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_transaction_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transaction_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_trans_item_code ON transactions(item_code);
CREATE INDEX IF NOT EXISTS idx_trans_station_code ON transactions(station_code);
CREATE INDEX IF NOT EXISTS idx_trans_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_trans_batch_number ON transactions(batch_number);

-- ============================================================================
-- 觸發器 (Triggers)
-- ============================================================================

-- 更新 items 的 updated_at
CREATE TRIGGER IF NOT EXISTS update_items_timestamp
AFTER UPDATE ON items
FOR EACH ROW
BEGIN
    UPDATE items SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 更新 station_metadata 的 updated_at
CREATE TRIGGER IF NOT EXISTS update_station_metadata_timestamp
AFTER UPDATE ON station_metadata
FOR EACH ROW
BEGIN
    UPDATE station_metadata SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- 初始資料 (Initial Data)
-- ============================================================================

-- 插入預設站點資料（如果不存在）
INSERT OR IGNORE INTO station_metadata (
    station_code, station_name, station_type, admin_level,
    organization_code, organization_name, region_code, region_name,
    beds, daily_capacity, has_pharmacy, has_surgery, has_emergency,
    storage_capacity_m3, status
) VALUES (
    'TC-01', '前線醫療站01', 'THIRD_CLASS_BORP', 'STATION_LOCAL',
    'DNO', 'De Novo Orthopedics', 'TC', '桃園地區',
    20, 50, 1, 0, 1,
    20.0, 'ACTIVE'
);

-- ============================================================================
-- 視圖 (Views)
-- ============================================================================

-- 庫存狀態視圖
CREATE VIEW IF NOT EXISTS v_inventory_status AS
SELECT
    i.item_code,
    i.item_name,
    i.item_category,
    i.category,
    i.unit,
    i.current_stock,
    i.reserved_stock,
    i.available_stock,
    i.baseline_qty_7days,
    i.min_stock,
    i.reorder_point,
    CASE
        WHEN i.current_stock <= 0 THEN 'OUT_OF_STOCK'
        WHEN i.current_stock <= i.min_stock THEN 'LOW_STOCK'
        WHEN i.current_stock <= i.reorder_point THEN 'REORDER'
        ELSE 'NORMAL'
    END AS stock_status,
    i.nearest_expiry_date,
    i.is_active,
    i.is_critical
FROM items i
WHERE i.is_active = 1;

-- 交易統計視圖
CREATE VIEW IF NOT EXISTS v_transaction_summary AS
SELECT
    t.station_code,
    t.transaction_type,
    t.item_category,
    DATE(t.transaction_date) AS transaction_date,
    COUNT(*) AS transaction_count,
    SUM(t.quantity) AS total_quantity,
    SUM(t.total_cost) AS total_cost
FROM transactions t
WHERE t.status = 'COMPLETED'
GROUP BY t.station_code, t.transaction_type, t.item_category, DATE(t.transaction_date);

-- ============================================================================
-- 4. 血袋庫存表 (Blood Inventory)
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
-- 5. 血袋事件記錄表 (Blood Events)
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
-- 6. 血袋庫存視圖
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
-- 7. 血袋庫存觸發器
-- ============================================================================

-- 自動更新 blood_inventory.updated_at
CREATE TRIGGER IF NOT EXISTS update_blood_inventory_timestamp
AFTER UPDATE ON blood_inventory
FOR EACH ROW
BEGIN
    UPDATE blood_inventory SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- 結束
-- ============================================================================
