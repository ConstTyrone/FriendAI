#!/usr/bin/env python3
"""
创建关系发现系统所需的数据表
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database_sqlite_v2 import SQLiteDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_relationship_tables(db):
    """创建关系发现系统的核心表"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 创建关系记录表 (全局表，所有用户共享)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    
                    -- 关系双方
                    source_profile_id INTEGER NOT NULL,
                    source_profile_name TEXT NOT NULL,
                    target_profile_id INTEGER NOT NULL, 
                    target_profile_name TEXT NOT NULL,
                    
                    -- 关系信息
                    relationship_type TEXT NOT NULL,  -- colleague/investor/client/competitor/partner等
                    relationship_subtype TEXT,         -- 更细分的类型
                    relationship_direction TEXT,       -- bidirectional/source_to_target/target_to_source
                    
                    -- 关系强度和置信度
                    confidence_score REAL DEFAULT 0.5, -- 0-1的置信度分数
                    relationship_strength TEXT,        -- strong/medium/weak
                    
                    -- 证据和推理
                    evidence JSON DEFAULT '{}',        -- 支持这个关系的证据
                    evidence_fields TEXT,              -- 匹配的字段列表
                    matching_method TEXT,              -- exact/fuzzy/ai_inference
                    
                    -- 状态管理
                    status TEXT DEFAULT 'discovered',  -- discovered/confirmed/ignored/deleted
                    confirmed_by TEXT,                 -- 确认人
                    confirmed_at TIMESTAMP,
                    
                    -- 元数据
                    metadata JSON DEFAULT '{}',        -- 额外的元数据
                    tags TEXT,                         -- 关系标签
                    
                    -- 时间戳
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- 唯一约束，防止重复关系
                    UNIQUE(user_id, source_profile_id, target_profile_id, relationship_type)
                )
            """)
            
            # 创建关系表的索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_user ON relationships(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_profile_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_profile_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_status ON relationships(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_confidence ON relationships(confidence_score DESC)")
            
            # 2. 创建关系检测规则表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationship_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL UNIQUE,
                    rule_type TEXT NOT NULL,              -- field_match/pattern_match/ai_inference
                    relationship_type TEXT NOT NULL,       -- 这个规则检测的关系类型
                    
                    -- 规则配置
                    field_mappings JSON DEFAULT '{}',      -- 需要比较的字段映射
                    matching_logic TEXT,                   -- exact/fuzzy/contains/regex
                    matching_threshold REAL DEFAULT 0.8,   -- 匹配阈值
                    
                    -- 权重和优先级
                    weight REAL DEFAULT 1.0,               -- 规则权重
                    priority INTEGER DEFAULT 5,            -- 优先级(1-10)
                    
                    -- 规则条件
                    conditions JSON DEFAULT '{}',          -- 额外的条件
                    exclusions JSON DEFAULT '[]',          -- 排除条件
                    
                    -- 状态
                    is_active BOOLEAN DEFAULT 1,
                    is_system BOOLEAN DEFAULT 0,          -- 是否系统内置规则
                    
                    -- 统计
                    match_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    
                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建规则表的索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rules_type ON relationship_rules(relationship_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rules_active ON relationship_rules(is_active)")
            
            # 3. 创建公司信息扩展表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- 公司基础信息
                    company_name TEXT NOT NULL UNIQUE,
                    company_full_name TEXT,
                    company_english_name TEXT,
                    
                    -- 公司别名和变体
                    aliases JSON DEFAULT '[]',            -- 公司的其他名称
                    abbreviations JSON DEFAULT '[]',      -- 缩写
                    
                    -- 公司结构
                    parent_company TEXT,                  -- 母公司
                    parent_company_id INTEGER,
                    subsidiaries JSON DEFAULT '[]',       -- 子公司列表
                    affiliated_companies JSON DEFAULT '[]', -- 关联公司
                    
                    -- 行业和业务
                    industry TEXT,                        -- 行业
                    sub_industry TEXT,                    -- 子行业
                    business_scope TEXT,                  -- 业务范围
                    main_products JSON DEFAULT '[]',      -- 主要产品
                    
                    -- 地理位置
                    headquarters_location TEXT,           -- 总部位置
                    office_locations JSON DEFAULT '[]',   -- 办公地点
                    
                    -- 规模信息
                    company_size TEXT,                    -- 公司规模
                    employee_count_range TEXT,            -- 员工数量范围
                    
                    -- 股权和投资
                    shareholders JSON DEFAULT '[]',        -- 股东信息
                    investors JSON DEFAULT '[]',          -- 投资方
                    portfolio_companies JSON DEFAULT '[]', -- 投资组合（如果是投资公司）
                    
                    -- 数据来源
                    data_source TEXT,                     -- manual/api/crawled
                    external_id TEXT,                     -- 外部数据源ID
                    verified BOOLEAN DEFAULT 0,           -- 是否已验证
                    
                    -- 元数据
                    metadata JSON DEFAULT '{}',
                    tags TEXT,
                    
                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_verified_at TIMESTAMP
                )
            """)
            
            # 创建公司表的索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON company_info(company_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_parent ON company_info(parent_company)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_industry ON company_info(industry)")
            
            # 4. 创建关系发现日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationship_discovery_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    
                    -- 触发信息
                    trigger_type TEXT NOT NULL,           -- profile_create/profile_update/manual_scan
                    trigger_profile_id INTEGER,
                    trigger_profile_name TEXT,
                    
                    -- 发现结果
                    relationships_found INTEGER DEFAULT 0,
                    relationships_confirmed INTEGER DEFAULT 0,
                    
                    -- 性能指标
                    scan_duration_ms INTEGER,
                    profiles_scanned INTEGER,
                    rules_applied INTEGER,
                    
                    -- 详细结果
                    results JSON DEFAULT '[]',
                    errors JSON DEFAULT '[]',
                    
                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建日志表的索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_logs_user ON relationship_discovery_logs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_logs_trigger ON relationship_discovery_logs(trigger_type)")
            
            conn.commit()
            logger.info("✅ 关系发现系统表创建成功")
            
            # 插入默认的关系检测规则
            insert_default_rules(cursor)
            conn.commit()
            logger.info("✅ 默认关系检测规则已插入")
            
            return True
            
    except Exception as e:
        logger.error(f"创建关系表失败: {e}")
        return False

def insert_default_rules(cursor):
    """插入默认的关系检测规则"""
    
    default_rules = [
        # 同事关系规则
        {
            'rule_name': 'same_company_exact',
            'rule_type': 'field_match',
            'relationship_type': 'colleague',
            'field_mappings': '{"source": "company", "target": "company"}',
            'matching_logic': 'exact',
            'matching_threshold': 1.0,
            'weight': 1.0,
            'priority': 9,
            'is_system': 1
        },
        {
            'rule_name': 'same_company_fuzzy',
            'rule_type': 'field_match',
            'relationship_type': 'colleague',
            'field_mappings': '{"source": "company", "target": "company"}',
            'matching_logic': 'fuzzy',
            'matching_threshold': 0.85,
            'weight': 0.8,
            'priority': 7,
            'is_system': 1
        },
        # 同一地区规则
        {
            'rule_name': 'same_location',
            'rule_type': 'field_match',
            'relationship_type': 'same_location',
            'field_mappings': '{"source": "location", "target": "location"}',
            'matching_logic': 'contains',
            'matching_threshold': 0.8,
            'weight': 0.5,
            'priority': 5,
            'is_system': 1
        },
        # 同一学校规则
        {
            'rule_name': 'same_education',
            'rule_type': 'field_match',
            'relationship_type': 'alumni',
            'field_mappings': '{"source": "education", "target": "education"}',
            'matching_logic': 'contains',
            'matching_threshold': 0.7,
            'weight': 0.6,
            'priority': 6,
            'is_system': 1
        }
    ]
    
    for rule in default_rules:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO relationship_rules (
                    rule_name, rule_type, relationship_type, field_mappings,
                    matching_logic, matching_threshold, weight, priority, is_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule['rule_name'], rule['rule_type'], rule['relationship_type'],
                rule['field_mappings'], rule['matching_logic'], rule['matching_threshold'],
                rule['weight'], rule['priority'], rule['is_system']
            ))
        except Exception as e:
            logger.warning(f"插入规则 {rule['rule_name']} 失败: {e}")

def main():
    """主函数"""
    logger.info("开始创建关系发现系统表...")
    
    # 初始化数据库
    db = SQLiteDatabase()
    
    # 创建关系表
    success = create_relationship_tables(db)
    
    if success:
        logger.info("✅ 所有关系表创建成功！")
        
        # 显示创建的表
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'relationship%' OR name LIKE 'company%'")
            tables = cursor.fetchall()
            
            logger.info("创建的关系相关表：")
            for table in tables:
                logger.info(f"  - {table[0]}")
                
            # 显示规则数量
            cursor.execute("SELECT COUNT(*) FROM relationship_rules WHERE is_active=1")
            rule_count = cursor.fetchone()[0]
            logger.info(f"激活的关系检测规则数: {rule_count}")
            
    else:
        logger.error("❌ 关系表创建失败")
        sys.exit(1)

if __name__ == "__main__":
    main()