#!/usr/bin/env python3
"""
醫療站庫存管理系統 - 後端 API
版本: v1.4.1
新增: 手術記錄管理、匯出功能
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import sqlite3
import json
import csv
import io
import zipfile
import shutil
import hashlib

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

# v1.4.5新增: 緊急功能相關套件
import qrcode
from io import BytesIO
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("Pandas not available, some export features will be limited")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available, PDF generation will be limited")


# ============================================================================
# 日誌配置
# ============================================================================

def setup_logging():
    """設定日誌系統"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('medical_inventory.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================================================
# 配置
# ============================================================================

class Config:
    """系統配置"""
    VERSION = "1.4.5"
    DATABASE_PATH = "medical_inventory.db"
    STATION_ID = "TC-01"
    DEBUG = True

    # 血型列表
    BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']

config = Config()


# ============================================================================
# Pydantic Models - 請求模型
# ============================================================================

class ReceiveRequest(BaseModel):
    """進貨請求"""
    itemCode: str = Field(..., description="物品代碼", min_length=1)
    quantity: int = Field(..., gt=0, description="數量必須大於0")
    batchNumber: Optional[str] = Field(None, description="批號")
    expiryDate: Optional[str] = Field(None, description="效期 (YYYY-MM-DD)")
    remarks: Optional[str] = Field(None, description="備註", max_length=500)
    stationId: str = Field(default="TC-01", description="站點ID")

    @field_validator('expiryDate')
    @classmethod
    def validate_expiry_date(cls, v):
        """驗證效期格式"""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('效期格式必須為 YYYY-MM-DD')
        return v


class ConsumeRequest(BaseModel):
    """消耗請求"""
    itemCode: str = Field(..., description="物品代碼", min_length=1)
    quantity: int = Field(..., gt=0, description="數量必須大於0")
    purpose: str = Field(..., description="用途說明", min_length=1, max_length=500)
    stationId: str = Field(default="TC-01", description="站點ID")


class BloodRequest(BaseModel):
    """血袋請求"""
    bloodType: str = Field(..., description="血型")
    quantity: int = Field(..., gt=0, description="數量(U)必須大於0")
    stationId: str = Field(default="TC-01", description="站點ID")

    @field_validator('bloodType')
    @classmethod
    def validate_blood_type(cls, v):
        """驗證血型"""
        if v not in config.BLOOD_TYPES:
            raise ValueError(f'血型必須為以下之一: {", ".join(config.BLOOD_TYPES)}')
        return v


class EquipmentCheckRequest(BaseModel):
    """設備檢查請求"""
    stationId: str = Field(default="TC-01", description="站點ID")
    status: str = Field(default="NORMAL", description="設備狀態")
    powerLevel: Optional[int] = Field(None, ge=0, le=100, description="電力等級 (0-100%)")
    remarks: Optional[str] = Field(None, description="備註", max_length=500)


class EquipmentCreateRequest(BaseModel):
    """設備新增請求"""
    name: str = Field(..., description="設備名稱", min_length=1, max_length=200)
    category: str = Field(default="其他", description="設備分類", max_length=100)
    quantity: int = Field(default=1, ge=1, description="數量")
    remarks: Optional[str] = Field(None, description="備註", max_length=500)


class EquipmentUpdateRequest(BaseModel):
    """設備更新請求"""
    name: Optional[str] = Field(None, description="設備名稱", min_length=1, max_length=200)
    category: Optional[str] = Field(None, description="設備分類", max_length=100)
    quantity: Optional[int] = Field(None, ge=0, description="數量")
    status: Optional[str] = Field(None, description="設備狀態")
    remarks: Optional[str] = Field(None, description="備註", max_length=500)


class ItemCreateRequest(BaseModel):
    """物品新增請求"""
    code: Optional[str] = Field(None, description="物品代碼(留空自動生成)", max_length=50)
    name: str = Field(..., description="物品名稱", min_length=1, max_length=200)
    unit: str = Field(default="EA", description="單位", max_length=20)
    minStock: int = Field(default=10, ge=0, description="最小庫存")
    category: str = Field(default="其他", description="分類", max_length=100)


class ItemUpdateRequest(BaseModel):
    """物品更新請求"""
    name: Optional[str] = Field(None, description="物品名稱", min_length=1, max_length=200)
    unit: Optional[str] = Field(None, description="單位", max_length=20)
    minStock: Optional[int] = Field(None, ge=0, description="最小庫存")
    category: Optional[str] = Field(None, description="分類", max_length=100)


class SurgeryConsumptionItem(BaseModel):
    """手術耗材項目"""
    itemCode: str = Field(..., description="物品代碼")
    itemName: str = Field(..., description="物品名稱")
    quantity: int = Field(..., gt=0, description="數量")
    unit: str = Field(..., description="單位")


class SurgeryRecordRequest(BaseModel):
    """手術記錄請求"""
    patientName: str = Field(..., description="病患姓名", min_length=1, max_length=100)
    surgeryType: str = Field(..., description="手術類型", min_length=1, max_length=200)
    surgeonName: str = Field(..., description="主刀醫師", min_length=1, max_length=100)
    anesthesiaType: Optional[str] = Field(None, description="麻醉方式", max_length=100)
    durationMinutes: Optional[int] = Field(None, ge=0, description="手術時長(分鐘)")
    remarks: Optional[str] = Field(None, description="手術備註", max_length=2000)
    consumptions: List[SurgeryConsumptionItem] = Field(..., description="使用耗材清單")
    stationId: str = Field(default="TC-01", description="站點ID")


# ============================================================================
# 資料庫管理器
# ============================================================================

class DatabaseManager:
    """資料庫管理器 - 處理所有資料庫操作"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        logger.info(f"初始化資料庫: {db_path}")
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """取得資料庫連接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化資料庫結構"""
        logger.info("開始初始化資料庫結構...")
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 物品主檔
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    unit TEXT DEFAULT 'EA',
                    min_stock INTEGER DEFAULT 5,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 庫存事件記錄
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    item_code TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    batch_number TEXT,
                    expiry_date TEXT,
                    remarks TEXT,
                    station_id TEXT NOT NULL,
                    operator TEXT DEFAULT 'SYSTEM',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_code) REFERENCES items(code)
                )
            """)
            
            # 為事件表建立索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_inventory_events_item 
                ON inventory_events(item_code)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_inventory_events_timestamp 
                ON inventory_events(timestamp)
            """)
            
            # 血袋庫存
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blood_inventory (
                    blood_type TEXT PRIMARY KEY,
                    quantity INTEGER DEFAULT 0,
                    station_id TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 血袋事件記錄
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blood_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    blood_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    station_id TEXT NOT NULL,
                    operator TEXT DEFAULT 'SYSTEM',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 設備主檔
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipment (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT '其他',
                    quantity INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'UNCHECKED',
                    last_check TIMESTAMP,
                    power_level INTEGER,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 設備檢查記錄
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipment_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    power_level INTEGER,
                    remarks TEXT,
                    station_id TEXT NOT NULL,
                    operator TEXT DEFAULT 'SYSTEM',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
                )
            """)
            
            # 手術記錄主檔 (新增)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS surgery_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_number TEXT UNIQUE NOT NULL,
                    record_date DATE NOT NULL,
                    patient_name TEXT NOT NULL,
                    surgery_sequence INTEGER NOT NULL,
                    surgery_type TEXT NOT NULL,
                    surgeon_name TEXT NOT NULL,
                    anesthesia_type TEXT,
                    duration_minutes INTEGER,
                    remarks TEXT,
                    station_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 手術耗材明細 (新增)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS surgery_consumptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    surgery_id INTEGER NOT NULL,
                    item_code TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    FOREIGN KEY (surgery_id) REFERENCES surgery_records(id) ON DELETE CASCADE,
                    FOREIGN KEY (item_code) REFERENCES items(code)
                )
            """)
            
            # 為手術記錄建立索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_surgery_records_date 
                ON surgery_records(record_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_surgery_records_patient 
                ON surgery_records(patient_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_surgery_consumptions_surgery 
                ON surgery_consumptions(surgery_id)
            """)
            
            # 初始化預設設備
            self._init_default_equipment(cursor)
            
            # 初始化血型庫存
            for blood_type in config.BLOOD_TYPES:
                cursor.execute("""
                    INSERT OR IGNORE INTO blood_inventory (blood_type, quantity, station_id)
                    VALUES (?, 0, ?)
                """, (blood_type, config.STATION_ID))
            
            conn.commit()
            logger.info("資料庫初始化完成")
            
        except Exception as e:
            logger.error(f"資料庫初始化失敗: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_default_equipment(self, cursor):
        """初始化預設設備"""
        default_equipment = [
            ('power-1', '行動電源站', '電力設備'),
            ('photocatalyst-1', '光觸媒', '空氣淨化'),
            ('water-1', '淨水器', '水處理'),
            ('fridge-1', '行動冰箱', '冷藏設備')
        ]
        
        for eq_id, eq_name, eq_category in default_equipment:
            cursor.execute("""
                INSERT OR IGNORE INTO equipment (id, name, category, quantity, status)
                VALUES (?, ?, ?, 1, 'UNCHECKED')
            """, (eq_id, eq_name, eq_category))
    
    def generate_item_code(self, category: str) -> str:
        """根據分類自動生成物品代碼"""
        CATEGORY_PREFIXES = {
            '手術耗材': 'SURG',
            '急救物資': 'EMER',
            '藥品': 'MED',
            '防護用品': 'PPE',
            '醫療設備': 'EQUIP',
            '其他': 'OTHER'
        }
        
        prefix = CATEGORY_PREFIXES.get(category, 'OTHER')
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT code FROM items 
                WHERE code LIKE ? 
                ORDER BY code DESC 
                LIMIT 1
            """, (f"{prefix}-%",))
            
            result = cursor.fetchone()
            
            if result:
                last_code = result['code']
                try:
                    last_number = int(last_code.split('-')[1])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = 1
            else:
                new_number = 1
            
            new_code = f"{prefix}-{new_number:03d}"
            logger.info(f"為分類 '{category}' 生成代碼: {new_code}")
            return new_code
            
        finally:
            conn.close()
    
    def generate_equipment_id(self, category: str) -> str:
        """根據分類自動生成設備ID"""
        CATEGORY_PREFIXES = {
            '電力設備': 'PWR',
            '空氣淨化': 'AIR',
            '水處理': 'WTR',
            '冷藏設備': 'COOL',
            '通訊設備': 'COMM',
            '照明設備': 'LIGHT',
            '其他': 'MISC'
        }
        
        prefix = CATEGORY_PREFIXES.get(category, 'MISC')
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id FROM equipment 
                WHERE id LIKE ? 
                ORDER BY id DESC 
                LIMIT 1
            """, (f"{prefix}-%",))
            
            result = cursor.fetchone()
            
            if result:
                last_id = result['id']
                try:
                    last_number = int(last_id.split('-')[1])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = 1
            else:
                new_number = 1
            
            new_id = f"{prefix}-{new_number:03d}"
            logger.info(f"為分類 '{category}' 生成設備ID: {new_id}")
            return new_id
            
        finally:
            conn.close()
    
    def generate_surgery_record_number(self, record_date: str, patient_name: str, sequence: int) -> str:
        """
        生成手術記錄編號
        格式: YYYYMMDD-PatientName-N
        例如: 20251104-王小明-1
        """
        date_str = record_date.replace('-', '')
        record_number = f"{date_str}-{patient_name}-{sequence}"
        return record_number
    
    def get_daily_surgery_sequence(self, record_date: str, station_id: str) -> int:
        """取得當日手術序號"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT MAX(surgery_sequence) as max_seq
                FROM surgery_records
                WHERE record_date = ? AND station_id = ?
            """, (record_date, station_id))
            
            result = cursor.fetchone()
            max_seq = result['max_seq'] if result['max_seq'] else 0
            return max_seq + 1
            
        finally:
            conn.close()
    
    def create_surgery_record(self, request: SurgeryRecordRequest) -> dict:
        """建立手術記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 取得今天日期
            record_date = datetime.now().strftime('%Y-%m-%d')
            
            # 取得當日手術序號
            sequence = self.get_daily_surgery_sequence(record_date, request.stationId)
            
            # 生成記錄編號
            record_number = self.generate_surgery_record_number(
                record_date, 
                request.patientName, 
                sequence
            )
            
            # 插入手術記錄
            cursor.execute("""
                INSERT INTO surgery_records (
                    record_number, record_date, patient_name, surgery_sequence,
                    surgery_type, surgeon_name, anesthesia_type, duration_minutes,
                    remarks, station_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_number,
                record_date,
                request.patientName,
                sequence,
                request.surgeryType,
                request.surgeonName,
                request.anesthesiaType,
                request.durationMinutes,
                request.remarks,
                request.stationId
            ))
            
            surgery_id = cursor.lastrowid
            
            # 插入耗材明細
            for item in request.consumptions:
                cursor.execute("""
                    INSERT INTO surgery_consumptions (
                        surgery_id, item_code, item_name, quantity, unit
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    surgery_id,
                    item.itemCode,
                    item.itemName,
                    item.quantity,
                    item.unit
                ))
                
                # 同時記錄庫存消耗
                cursor.execute("""
                    INSERT INTO inventory_events (
                        event_type, item_code, quantity, remarks, station_id
                    )
                    VALUES ('CONSUME', ?, ?, ?, ?)
                """, (
                    item.itemCode,
                    item.quantity,
                    f"手術使用 - {record_number}",
                    request.stationId
                ))
            
            conn.commit()
            logger.info(f"手術記錄建立成功: {record_number}")
            
            return {
                "success": True,
                "message": f"手術記錄 {record_number} 建立成功",
                "recordNumber": record_number,
                "surgeryId": surgery_id,
                "sequence": sequence
            }
        
        except Exception as e:
            conn.rollback()
            logger.error(f"建立手術記錄失敗: {e}")
            raise HTTPException(status_code=500, detail=f"建立手術記錄失敗: {str(e)}")
        finally:
            conn.close()
    
    def get_surgery_records(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        patient_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """查詢手術記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 構建查詢條件
            where_clauses = []
            params = []
            
            if start_date:
                where_clauses.append("record_date >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("record_date <= ?")
                params.append(end_date)
            
            if patient_name:
                where_clauses.append("patient_name LIKE ?")
                params.append(f"%{patient_name}%")
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            params.append(limit)
            
            # 查詢手術記錄
            cursor.execute(f"""
                SELECT 
                    id, record_number, record_date, patient_name, surgery_sequence,
                    surgery_type, surgeon_name, anesthesia_type, duration_minutes,
                    remarks, station_id, created_at
                FROM surgery_records
                WHERE {where_sql}
                ORDER BY record_date DESC, surgery_sequence DESC
                LIMIT ?
            """, params)
            
            records = []
            for row in cursor.fetchall():
                record = dict(row)
                
                # 查詢耗材明細
                cursor.execute("""
                    SELECT item_code, item_name, quantity, unit
                    FROM surgery_consumptions
                    WHERE surgery_id = ?
                """, (record['id'],))
                
                record['consumptions'] = [dict(c) for c in cursor.fetchall()]
                records.append(record)
            
            return records
            
        finally:
            conn.close()
    
    def export_surgery_records_csv(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """匯出手術記錄為 CSV"""
        records = self.get_surgery_records(start_date, end_date, limit=10000)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題
        writer.writerow([
            '記錄編號', '日期', '病患姓名', '當日第N台',
            '手術類型', '主刀醫師', '麻醉方式', '手術時長(分)',
            '耗材代碼', '耗材名稱', '數量', '單位',
            '備註', '建立時間'
        ])
        
        # 寫入資料
        for record in records:
            for consumption in record['consumptions']:
                writer.writerow([
                    record['record_number'],
                    record['record_date'],
                    record['patient_name'],
                    record['surgery_sequence'],
                    record['surgery_type'],
                    record['surgeon_name'],
                    record.get('anesthesia_type', ''),
                    record.get('duration_minutes', ''),
                    consumption['item_code'],
                    consumption['item_name'],
                    consumption['quantity'],
                    consumption['unit'],
                    record.get('remarks', ''),
                    record['created_at']
                ])
        
        return output.getvalue()
    
    def get_stats(self) -> Dict[str, int]:
        """取得系統統計"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 品項總數
            cursor.execute("SELECT COUNT(*) as count FROM items")
            total_items = cursor.fetchone()['count']
            
            # 庫存警戒數
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM (
                    SELECT 
                        i.code,
                        i.min_stock,
                        COALESCE(stock.current_stock, 0) as current_stock
                    FROM items i
                    LEFT JOIN (
                        SELECT item_code,
                               SUM(CASE WHEN event_type = 'RECEIVE' THEN quantity
                                        WHEN event_type = 'CONSUME' THEN -quantity
                                        ELSE 0 END) as current_stock
                        FROM inventory_events
                        GROUP BY item_code
                    ) stock ON i.code = stock.item_code
                ) t
                WHERE t.current_stock < t.min_stock
            """)
            low_stock = cursor.fetchone()['count']
            
            # 全血總量
            cursor.execute("SELECT SUM(quantity) as total FROM blood_inventory")
            total_blood = cursor.fetchone()['total'] or 0
            
            # 設備警戒數
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM equipment 
                WHERE status IN ('WARNING', 'ERROR')
            """)
            equipment_alerts = cursor.fetchone()['count']
            
            return {
                "totalItems": total_items,
                "lowStockItems": low_stock,
                "totalBlood": total_blood,
                "equipmentAlerts": equipment_alerts
            }
        finally:
            conn.close()
    
    def receive_item(self, request: ReceiveRequest) -> dict:
        """進貨處理"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM items WHERE code = ?", (request.itemCode,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail=f"物品代碼 {request.itemCode} 不存在")
            
            cursor.execute("""
                INSERT INTO inventory_events 
                (event_type, item_code, quantity, batch_number, expiry_date, remarks, station_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'RECEIVE',
                request.itemCode,
                request.quantity,
                request.batchNumber,
                request.expiryDate,
                request.remarks,
                request.stationId
            ))
            
            conn.commit()
            logger.info(f"進貨記錄成功: {request.itemCode} +{request.quantity}")
            
            return {
                "success": True,
                "message": f"物品 {item['name']} 進貨 {request.quantity} 已記錄"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"進貨處理失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
    
    def consume_item(self, request: ConsumeRequest) -> dict:
        """消耗處理"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM items WHERE code = ?", (request.itemCode,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail=f"物品代碼 {request.itemCode} 不存在")
            
            cursor.execute("""
                SELECT SUM(CASE WHEN event_type = 'RECEIVE' THEN quantity
                               WHEN event_type = 'CONSUME' THEN -quantity
                               ELSE 0 END) as current_stock
                FROM inventory_events
                WHERE item_code = ?
            """, (request.itemCode,))
            
            result = cursor.fetchone()
            current_stock = result['current_stock'] if result['current_stock'] else 0
            
            if current_stock < request.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"庫存不足: 目前庫存 {current_stock},需求 {request.quantity}"
                )
            
            cursor.execute("""
                INSERT INTO inventory_events 
                (event_type, item_code, quantity, remarks, station_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                'CONSUME',
                request.itemCode,
                request.quantity,
                request.purpose,
                request.stationId
            ))
            
            conn.commit()
            logger.info(f"消耗記錄成功: {request.itemCode} -{request.quantity}")
            
            return {
                "success": True,
                "message": f"物品 {item['name']} 消耗 {request.quantity} 已記錄"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"消耗處理失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
    
    def process_blood(self, action: str, request: BloodRequest) -> dict:
        """血袋處理"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT quantity FROM blood_inventory WHERE blood_type = ?",
                (request.bloodType,)
            )
            blood = cursor.fetchone()
            if not blood:
                raise HTTPException(status_code=404, detail=f"血型 {request.bloodType} 不存在")
            
            current_quantity = blood['quantity']
            
            if action == 'receive':
                new_quantity = current_quantity + request.quantity
                event_type = 'RECEIVE'
            else:
                if current_quantity < request.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"血袋庫存不足: 目前 {current_quantity}U,需求 {request.quantity}U"
                    )
                new_quantity = current_quantity - request.quantity
                event_type = 'CONSUME'
            
            cursor.execute("""
                UPDATE blood_inventory 
                SET quantity = ?, last_updated = CURRENT_TIMESTAMP
                WHERE blood_type = ?
            """, (new_quantity, request.bloodType))
            
            cursor.execute("""
                INSERT INTO blood_events 
                (event_type, blood_type, quantity, station_id)
                VALUES (?, ?, ?, ?)
            """, (event_type, request.bloodType, request.quantity, request.stationId))
            
            conn.commit()
            logger.info(f"血袋{action}記錄成功: {request.bloodType} {'+' if action=='receive' else '-'}{request.quantity}U")
            
            action_text = "入庫" if action == "receive" else "出庫"
            return {
                "success": True,
                "message": f"血袋 {request.bloodType} {action_text} {request.quantity}U 已記錄",
                "newQuantity": new_quantity
            }
        
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"血袋處理失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
    
    def get_blood_inventory(self) -> List[Dict]:
        """取得血袋庫存"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT blood_type, quantity, last_updated
                FROM blood_inventory
                ORDER BY blood_type
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def check_equipment(self, equipment_id: str, request: EquipmentCheckRequest) -> dict:
        """設備檢查"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM equipment WHERE id = ?", (equipment_id,))
            equipment = cursor.fetchone()
            if not equipment:
                raise HTTPException(status_code=404, detail=f"設備ID {equipment_id} 不存在")
            
            cursor.execute("""
                UPDATE equipment 
                SET status = ?,
                    last_check = CURRENT_TIMESTAMP,
                    power_level = ?,
                    remarks = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (request.status, request.powerLevel, request.remarks, equipment_id))
            
            cursor.execute("""
                INSERT INTO equipment_checks 
                (equipment_id, status, power_level, remarks, station_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                equipment_id,
                request.status,
                request.powerLevel,
                request.remarks,
                request.stationId
            ))
            
            conn.commit()
            logger.info(f"設備檢查記錄成功: {equipment_id} - {request.status}")
            
            return {
                "success": True,
                "message": f"設備 {equipment['name']} 檢查完成",
                "status": request.status
            }
        
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"設備檢查失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
    
    def get_equipment_status(self) -> List[Dict[str, Any]]:
        """取得所有設備狀態"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    id, name, category, quantity, status,
                    last_check, power_level, remarks
                FROM equipment
                ORDER BY name
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_inventory_items(self) -> List[Dict]:
        """取得所有物品及庫存"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    i.code, i.name, i.unit, i.min_stock, i.category,
                    COALESCE(stock.current_stock, 0) as current_stock
                FROM items i
                LEFT JOIN (
                    SELECT item_code,
                           SUM(CASE WHEN event_type = 'RECEIVE' THEN quantity
                                    WHEN event_type = 'CONSUME' THEN -quantity
                                    ELSE 0 END) as current_stock
                    FROM inventory_events
                    GROUP BY item_code
                ) stock ON i.code = stock.item_code
                ORDER BY i.category, i.name
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_inventory_events(
        self,
        event_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        item_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """查詢庫存事件記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            where_clauses = []
            params = []

            if event_type:
                where_clauses.append("e.event_type = ?")
                params.append(event_type)

            if start_date:
                where_clauses.append("DATE(e.timestamp) >= ?")
                params.append(start_date)

            if end_date:
                where_clauses.append("DATE(e.timestamp) <= ?")
                params.append(end_date)

            if item_code:
                where_clauses.append("e.item_code LIKE ?")
                params.append(f"%{item_code}%")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            params.append(limit)

            cursor.execute(f"""
                SELECT
                    e.id, e.event_type, e.item_code, i.name as item_name,
                    e.quantity, i.unit, e.batch_number, e.expiry_date,
                    e.remarks, e.station_id, e.operator, e.timestamp
                FROM inventory_events e
                LEFT JOIN items i ON e.item_code = i.code
                WHERE {where_sql}
                ORDER BY e.timestamp DESC
                LIMIT ?
            """, params)

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def export_inventory_csv(self) -> str:
        """匯出庫存資料為 CSV"""
        items = self.get_inventory_items()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            '物品代碼', '物品名稱', '分類', '單位',
            '當前庫存', '最小庫存', '庫存狀態'
        ])

        for item in items:
            status = '正常' if item['current_stock'] >= item['min_stock'] else '警戒'
            writer.writerow([
                item['code'],
                item['name'],
                item['category'],
                item['unit'],
                item['current_stock'],
                item['min_stock'],
                status
            ])

        return output.getvalue()

    def export_inventory_events_csv(
        self,
        event_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """匯出庫存事件記錄為 CSV"""
        events = self.get_inventory_events(event_type, start_date, end_date, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            '事件ID', '事件類型', '物品代碼', '物品名稱', '數量', '單位',
            '批號', '效期', '備註', '站點', '操作員', '時間'
        ])

        for event in events:
            event_type_text = '進貨' if event['event_type'] == 'RECEIVE' else '消耗'
            writer.writerow([
                event['id'],
                event_type_text,
                event['item_code'],
                event['item_name'],
                event['quantity'],
                event['unit'],
                event.get('batch_number', ''),
                event.get('expiry_date', ''),
                event.get('remarks', ''),
                event['station_id'],
                event['operator'],
                event['timestamp']
            ])

        return output.getvalue()


# ============================================================================
# FastAPI 應用
# ============================================================================

app = FastAPI(
    title="醫療站庫存管理系統 API",
    version=config.VERSION,
    description="醫療站物資、血袋、設備、手術記錄管理系統"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager(config.DATABASE_PATH)


# ============================================================================
# API 端點
# ============================================================================

@app.get("/")
async def root():
    """根端點"""
    return {
        "name": "醫療站庫存管理系統 API",
        "version": config.VERSION,
        "station": config.STATION_ID,
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "version": config.VERSION,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/stats")
async def get_stats():
    """取得系統統計"""
    try:
        stats = db.get_stats()
        return stats
    except Exception as e:
        logger.error(f"取得統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 物品管理 API ==========

@app.get("/api/items")
async def get_items():
    """取得所有物品"""
    try:
        items = db.get_inventory_items()
        return {"items": items, "count": len(items)}
    except Exception as e:
        logger.error(f"取得物品列表失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/items")
async def create_item(request: ItemCreateRequest):
    """新增物品"""
    logger.info(f"新增物品: {request.name}")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        if not request.code or request.code.strip() == '':
            item_code = db.generate_item_code(request.category)
        else:
            item_code = request.code
            cursor.execute("SELECT code FROM items WHERE code = ?", (item_code,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"物品代碼 {item_code} 已存在")
        
        cursor.execute("""
            INSERT INTO items (code, name, unit, min_stock, category)
            VALUES (?, ?, ?, ?, ?)
        """, (item_code, request.name, request.unit, request.minStock, request.category))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"物品 {request.name} 新增成功",
            "item": {
                "code": item_code,
                "name": request.name,
                "unit": request.unit,
                "minStock": request.minStock,
                "category": request.category
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.put("/api/items/{code}")
async def update_item(code: str, request: ItemUpdateRequest):
    """更新物品"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT code FROM items WHERE code = ?", (code,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"物品代碼 {code} 不存在")
        
        update_fields = []
        update_values = []
        
        if request.name: update_fields.append("name = ?"); update_values.append(request.name)
        if request.unit: update_fields.append("unit = ?"); update_values.append(request.unit)
        if request.minStock is not None: update_fields.append("min_stock = ?"); update_values.append(request.minStock)
        if request.category: update_fields.append("category = ?"); update_values.append(request.category)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="沒有提供要更新的欄位")
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(code)
        
        cursor.execute(f"UPDATE items SET {', '.join(update_fields)} WHERE code = ?", update_values)
        conn.commit()
        
        return {"success": True, "message": f"物品 {code} 更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.delete("/api/items/{code}")
async def delete_item(code: str):
    """刪除物品"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM items WHERE code = ?", (code,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail=f"物品代碼 {code} 不存在")
        
        cursor.execute("DELETE FROM items WHERE code = ?", (code,))
        conn.commit()
        
        return {"success": True, "message": f"物品 {item['name']} 已刪除"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ========== 庫存操作 API ==========

@app.post("/api/receive")
async def receive_item(request: ReceiveRequest):
    """進貨"""
    return db.receive_item(request)


@app.post("/api/consume")
async def consume_item(request: ConsumeRequest):
    """消耗"""
    return db.consume_item(request)


# ========== 血袋管理 API ==========

@app.get("/api/blood/inventory")
async def get_blood_inventory():
    """取得血袋庫存"""
    try:
        inventory = db.get_blood_inventory()
        return {"bloodInventory": inventory}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/blood/receive")
async def receive_blood(request: BloodRequest):
    """血袋入庫"""
    return db.process_blood('receive', request)


@app.post("/api/blood/consume")
async def consume_blood(request: BloodRequest):
    """血袋出庫"""
    return db.process_blood('consume', request)


# ========== 設備管理 API ==========

@app.get("/api/equipment/status")
async def get_equipment_status():
    """取得所有設備狀態"""
    try:
        status = db.get_equipment_status()
        return {"equipment": status, "count": len(status)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/equipment")
async def get_equipment():
    """取得所有設備"""
    return await get_equipment_status()


@app.post("/api/equipment/check/{equipment_id}")
async def check_equipment(equipment_id: str, request: EquipmentCheckRequest):
    """設備檢查"""
    return db.check_equipment(equipment_id, request)


@app.post("/api/equipment")
async def create_equipment(request: EquipmentCreateRequest):
    """新增設備"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        equipment_id = db.generate_equipment_id(request.category)
        
        cursor.execute("""
            INSERT INTO equipment (id, name, category, quantity, status, remarks)
            VALUES (?, ?, ?, ?, 'UNCHECKED', ?)
        """, (equipment_id, request.name, request.category, request.quantity, request.remarks))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"設備 {request.name} 新增成功",
            "equipment": {
                "id": equipment_id,
                "name": request.name,
                "category": request.category,
                "quantity": request.quantity
            }
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.put("/api/equipment/{equipment_id}")
async def update_equipment(equipment_id: str, request: EquipmentUpdateRequest):
    """更新設備"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM equipment WHERE id = ?", (equipment_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"設備ID {equipment_id} 不存在")
        
        update_fields = []
        update_values = []
        
        if request.name: update_fields.append("name = ?"); update_values.append(request.name)
        if request.category: update_fields.append("category = ?"); update_values.append(request.category)
        if request.quantity is not None: update_fields.append("quantity = ?"); update_values.append(request.quantity)
        if request.status: update_fields.append("status = ?"); update_values.append(request.status)
        if request.remarks: update_fields.append("remarks = ?"); update_values.append(request.remarks)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="沒有提供要更新的欄位")
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(equipment_id)
        
        cursor.execute(f"UPDATE equipment SET {', '.join(update_fields)} WHERE id = ?", update_values)
        conn.commit()
        
        return {"success": True, "message": f"設備 {equipment_id} 更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.delete("/api/equipment/{equipment_id}")
async def delete_equipment(equipment_id: str):
    """刪除設備"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM equipment WHERE id = ?", (equipment_id,))
        equipment = cursor.fetchone()
        if not equipment:
            raise HTTPException(status_code=404, detail=f"設備ID {equipment_id} 不存在")
        
        cursor.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
        conn.commit()
        
        return {"success": True, "message": f"設備 {equipment['name']} 已刪除"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ========== 手術記錄 API (新增) ==========

@app.post("/api/surgery/record")
async def create_surgery_record(request: SurgeryRecordRequest):
    """建立手術記錄"""
    return db.create_surgery_record(request)


@app.get("/api/surgery/records")
async def get_surgery_records(
    start_date: Optional[str] = Query(None, description="開始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="結束日期 YYYY-MM-DD"),
    patient_name: Optional[str] = Query(None, description="病患姓名"),
    limit: int = Query(50, ge=1, le=1000, description="最大回傳筆數")
):
    """查詢手術記錄"""
    try:
        records = db.get_surgery_records(start_date, end_date, patient_name, limit)
        return {"records": records, "count": len(records)}
    except Exception as e:
        logger.error(f"查詢手術記錄失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/surgery/export/csv")
async def export_surgery_csv(
    start_date: Optional[str] = Query(None, description="開始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="結束日期 YYYY-MM-DD")
):
    """匯出手術記錄 CSV"""
    try:
        csv_content = db.export_surgery_records_csv(start_date, end_date)

        filename = f"surgery_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"匯出 CSV 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 庫存事件查詢與匯出 API (新增) ==========

@app.get("/api/inventory/events")
async def get_inventory_events(
    event_type: Optional[str] = Query(None, description="事件類型 RECEIVE/CONSUME"),
    start_date: Optional[str] = Query(None, description="開始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="結束日期 YYYY-MM-DD"),
    item_code: Optional[str] = Query(None, description="物品代碼(模糊搜尋)"),
    limit: int = Query(100, ge=1, le=1000, description="最大回傳筆數")
):
    """查詢庫存事件記錄（進貨/消耗）"""
    try:
        events = db.get_inventory_events(event_type, start_date, end_date, item_code, limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"查詢庫存事件失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inventory/export/csv")
async def export_inventory_csv():
    """匯出庫存清單 CSV"""
    try:
        csv_content = db.export_inventory_csv()

        filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv;charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"匯出庫存 CSV 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inventory/export/json")
async def export_inventory_json():
    """匯出庫存清單 JSON"""
    try:
        items = db.get_inventory_items()

        filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return StreamingResponse(
            iter([json.dumps(items, ensure_ascii=False, indent=2)]),
            media_type="application/json;charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"匯出庫存 JSON 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inventory/events/export/csv")
async def export_inventory_events_csv(
    event_type: Optional[str] = Query(None, description="事件類型 RECEIVE/CONSUME"),
    start_date: Optional[str] = Query(None, description="開始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="結束日期 YYYY-MM-DD")
):
    """匯出庫存事件記錄 CSV"""
    try:
        csv_content = db.export_inventory_events_csv(event_type, start_date, end_date)

        filename = f"inventory_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv;charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"匯出事件記錄 CSV 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 緊急功能 API (v1.4.5新增)
# ============================================================================

@app.get("/api/emergency/quick-backup")
async def emergency_quick_backup():
    """
    緊急快速備份 - 直接下載資料庫檔案

    戰時緊急撤離使用：最快速的資料保全方式
    """
    try:
        db_path = Path(config.DATABASE_PATH)

        if not db_path.exists():
            raise HTTPException(status_code=404, detail="資料庫檔案不存在")

        # 生成檔名: {STATION_ID}_{TIMESTAMP}.db
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{config.STATION_ID}_{timestamp}.db"

        logger.info(f"緊急快速備份: {filename}")

        return FileResponse(
            path=str(db_path),
            media_type="application/octet-stream",
            filename=filename
        )

    except Exception as e:
        logger.error(f"快速備份失敗: {e}")
        raise HTTPException(status_code=500, detail=f"備份失敗: {str(e)}")


@app.get("/api/emergency/download-all")
async def emergency_download_all():
    """
    緊急完整備份 - 生成包含所有資料的ZIP包

    包含內容：
    - database/: 完整資料庫
    - exports/: CSV + JSON 分類資料
    - config/: 站點設定檔
    - README.txt: 使用說明
    - manifest.json: 檔案清單與檢查碼
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"emergency_backup_{config.STATION_ID}_{timestamp}.zip"
        zip_path = Path("exports") / zip_filename

        # 確保exports目錄存在
        zip_path.parent.mkdir(exist_ok=True)

        logger.info(f"開始生成完整備份包: {zip_filename}")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. 加入資料庫
            db_path = Path(config.DATABASE_PATH)
            if db_path.exists():
                zipf.write(db_path, f"database/{db_path.name}")
                logger.info("✓ 資料庫已加入")

            # 2. 導出CSV資料
            exports_dir = Path("exports/temp")
            exports_dir.mkdir(exist_ok=True, parents=True)

            try:
                # 導出庫存清單
                inventory_data = db.get_all_items()
                if inventory_data:
                    csv_path = exports_dir / "inventory.csv"
                    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=inventory_data[0].keys())
                        writer.writeheader()
                        writer.writerows([dict(item) for item in inventory_data])
                    zipf.write(csv_path, "exports/inventory.csv")
                    logger.info("✓ 庫存清單已導出")

                # 導出血袋庫存
                blood_data = db.get_blood_inventory()
                if blood_data:
                    csv_path = exports_dir / "blood_inventory.csv"
                    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=['blood_type', 'quantity', 'station_id'])
                        writer.writeheader()
                        writer.writerows([dict(b) for b in blood_data])
                    zipf.write(csv_path, "exports/blood_inventory.csv")
                    logger.info("✓ 血袋庫存已導出")

                # 導出設備清單
                conn = db.get_connection()
                cursor = conn.cursor()
                equipment = cursor.execute("SELECT * FROM equipment").fetchall()
                if equipment:
                    csv_path = exports_dir / "equipment.csv"
                    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=[desc[0] for desc in cursor.description])
                        writer.writeheader()
                        writer.writerows([dict(zip([desc[0] for desc in cursor.description], row)) for row in equipment])
                    zipf.write(csv_path, "exports/equipment.csv")
                    logger.info("✓ 設備清單已導出")

            except Exception as e:
                logger.warning(f"部分資料導出失敗: {e}")

            # 3. 加入配置文件
            config_path = Path("config/station_config.json")
            if config_path.exists():
                zipf.write(config_path, "config/station_config.json")
                logger.info("✓ 配置文件已加入")

            # 4. 生成README
            readme_content = f"""
==============================================
醫療站庫存系統 - 緊急備份包
==============================================

備份時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
站點ID: {config.STATION_ID}
系統版本: {config.VERSION}

目錄結構:
-----------------------
database/          完整資料庫檔案
exports/           CSV格式資料
  - inventory.csv     庫存清單
  - blood_inventory.csv  血袋庫存
  - equipment.csv     設備清單
config/            站點設定檔
README.txt         本說明文件
manifest.json      檔案清單與檢查碼

使用方式:
-----------------------
1. 恢復資料庫:
   將database/*.db複製到新系統的database目錄

2. 查看資料:
   使用Excel或文字編輯器開啟exports/*.csv

3. 重新部署:
   參考config/station_config.json設定新系統

緊急聯絡:
-----------------------
如有問題請聯繫系統管理員

==============================================
此為自動生成的緊急備份包
請妥善保管並定期更新
==============================================
"""
            zipf.writestr("README.txt", readme_content.encode('utf-8'))
            logger.info("✓ README已生成")

            # 5. 生成manifest
            manifest = {
                "backup_time": datetime.now().isoformat(),
                "station_id": config.STATION_ID,
                "version": config.VERSION,
                "files": {},
                "statistics": {
                    "total_items": len(inventory_data) if inventory_data else 0,
                    "total_blood_types": len(blood_data) if blood_data else 0,
                    "total_equipment": len(equipment) if equipment else 0
                }
            }

            # 計算檔案檢查碼
            for item in zipf.filelist:
                if item.filename != "manifest.json":
                    manifest["files"][item.filename] = {
                        "size": item.file_size,
                        "compressed_size": item.compress_size
                    }

            zipf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            logger.info("✓ Manifest已生成")

        # 清理臨時目錄
        if exports_dir.exists():
            shutil.rmtree(exports_dir)

        logger.info(f"完整備份包生成成功: {zip_filename}")

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=zip_filename
        )

    except Exception as e:
        logger.error(f"完整備份失敗: {e}")
        raise HTTPException(status_code=500, detail=f"備份失敗: {str(e)}")


@app.get("/api/emergency/qr-code")
async def emergency_qr_code():
    """
    生成緊急QR Code - 包含關鍵資訊

    掃描QR Code可快速獲得:
    - 站點代碼
    - 時間戳記
    - 關鍵物資統計
    - 血袋庫存統計
    """
    try:
        # 收集關鍵資訊
        stats = db.get_stats()
        blood_inventory = db.get_blood_inventory()

        # 計算血袋總量
        total_blood = sum(b['quantity'] for b in blood_inventory)

        # 構建QR Code內容
        qr_data = {
            "station_id": config.STATION_ID,
            "timestamp": datetime.now().isoformat(),
            "version": config.VERSION,
            "stats": {
                "total_items": stats.get('total_items', 0),
                "low_stock_items": stats.get('low_stock_items', 0),
                "total_blood_units": total_blood,
                "equipment_alerts": stats.get('equipment_alerts', 0)
            },
            "blood_inventory": {b['blood_type']: b['quantity'] for b in blood_inventory}
        }

        # 生成QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data, ensure_ascii=False))
        qr.make(fit=True)

        # 生成圖片
        img = qr.make_image(fill_color="black", back_color="white")

        # 保存到BytesIO
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        logger.info("緊急QR Code已生成")

        # 返回圖片
        return StreamingResponse(
            img_io,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename=emergency_qr_{config.STATION_ID}.png"}
        )

    except Exception as e:
        logger.error(f"QR Code生成失敗: {e}")
        raise HTTPException(status_code=500, detail=f"QR Code生成失敗: {str(e)}")


# ============================================================================
# 啟動
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(f"🏥 醫療站庫存管理系統 API v{config.VERSION}")
    print("=" * 70)
    print(f"📁 資料庫: {config.DATABASE_PATH}")
    print(f"🏢 站點ID: {config.STATION_ID}")
    print(f"🌐 服務位址: http://0.0.0.0:8000")
    print(f"📖 API文件: http://localhost:8000/docs")
    print(f"📊 健康檢查: http://localhost:8000/api/health")
    print("=" * 70)
    print("✨ v1.4.5 新功能:")
    print("   - UI 全面重構（Heroicons + 新色系）")
    print("   - 處置標籤頁整合（手術記錄 + 一般消耗）")
    print("   - 血庫管理增強（病患資訊 + 歷史記錄）")
    print("   - 設備自動刷新機制（每日 07:00am）")
    print("   - 響應式設計優化")
    print("=" * 70)
    print("按 Ctrl+C 停止服務")
    print("=" * 70)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
