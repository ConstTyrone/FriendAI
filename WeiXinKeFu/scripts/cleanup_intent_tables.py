#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理/删除意图系统相关的表
"""

import sqlite3
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def cleanup_intent_tables():
    """删除所有意图相关的表"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🗑️ 开始清理意图系统表...")
        print("=" * 50)
        
        # 获取所有表名
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        all_tables = cursor.fetchall()
        
        tables_to_drop = []
        
        for (table_name,) in all_tables:
            # 收集需要删除的表
            if any(prefix in table_name for prefix in [
                'user_intents_',
                'intent_matches_',
                'push_history_',
                'user_push_preferences_'
            ]):
                tables_to_drop.append(table_name)
        
        # 全局表
        global_tables = [
            'wechat_kf_sessions',
            'push_templates'
        ]
        
        for table in global_tables:
            if (table,) in all_tables:
                tables_to_drop.append(table)
        
        if not tables_to_drop:
            print("ℹ️ 没有找到需要删除的意图系统表")
            return True
        
        print(f"找到 {len(tables_to_drop)} 个表需要删除：")
        for table in tables_to_drop:
            print(f"  - {table}")
        
        # 确认删除
        print("\n⚠️ 警告：这将永久删除上述表及其所有数据！")
        confirm = input("确认删除？(yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ 取消删除操作")
            return False
        
        # 执行删除
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  ✅ 删除表: {table}")
            except Exception as e:
                print(f"  ❌ 删除表 {table} 失败: {e}")
        
        conn.commit()
        print("\n✅ 清理完成！")
        
        # 显示剩余的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        remaining_tables = cursor.fetchall()
        
        print(f"\n📊 剩余表数量: {len(remaining_tables)}")
        if remaining_tables:
            print("剩余的表：")
            for (table,) in remaining_tables:
                print(f"  - {table}")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def show_current_structure():
    """显示当前的表结构"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n📋 当前数据库结构：")
        print("=" * 50)
        
        # 获取所有表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        if not tables:
            print("数据库中没有表")
            return
        
        for (table_name,) in tables:
            print(f"\n表: {table_name}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns[:5]:  # 只显示前5个字段
                print(f"  - {col[1]} ({col[2]})")
            
            if len(columns) > 5:
                print(f"  ... 还有 {len(columns) - 5} 个字段")
            
            # 获取记录数
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  记录数: {count}")
            except:
                pass
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--show':
            show_current_structure()
        elif sys.argv[1] == '--force':
            # 强制删除，不需要确认
            print("🗑️ 强制清理模式...")
            cleanup_intent_tables()
    else:
        # 先显示当前结构
        show_current_structure()
        
        print("\n" + "=" * 50)
        print("🗑️ 准备清理意图系统表...")
        print("=" * 50)
        
        cleanup_intent_tables()