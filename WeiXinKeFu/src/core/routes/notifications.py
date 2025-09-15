# routes/notifications.py
"""
通知管理相关路由
处理匹配通知的查看、标记已读等操作
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List
import logging
import sqlite3

from .auth import verify_user_token, get_query_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# 数据库导入（与main.py保持一致）
try:
    from ...database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("Notifications模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("Notifications模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


@router.get("/api/notifications/matches")
async def get_match_notifications(
    unread_only: bool = True,
    limit: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取匹配通知（供小程序轮询）"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        query_user_id = get_query_user_id(current_user)

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 查询最新的匹配记录
        if unread_only:
            # 只获取未读的（24小时内的新匹配）
            cursor.execute("""
                SELECT
                    m.id,
                    m.intent_id,
                    m.profile_id,
                    m.match_score,
                    m.explanation,
                    m.created_at,
                    i.name as intent_name,
                    i.type as intent_type
                FROM intent_matches m
                LEFT JOIN user_intents i ON m.intent_id = i.id
                WHERE m.user_id = ?
                AND datetime(m.created_at) > datetime('now', '-24 hours')
                AND (m.is_read IS NULL OR m.is_read = 0)
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (query_user_id, limit))
        else:
            # 获取所有最近的匹配
            cursor.execute("""
                SELECT
                    m.id,
                    m.intent_id,
                    m.profile_id,
                    m.match_score,
                    m.explanation,
                    m.created_at,
                    i.name as intent_name,
                    i.type as intent_type
                FROM intent_matches m
                LEFT JOIN user_intents i ON m.intent_id = i.id
                WHERE m.user_id = ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (query_user_id, limit))

        matches = []
        columns = [desc[0] for desc in cursor.description]

        for row in cursor.fetchall():
            match = dict(zip(columns, row))

            # 获取联系人信息
            user_table = f"profiles_{query_user_id.replace('-', '_')}"
            cursor.execute(f"""
                SELECT profile_name, company, position, phone
                FROM {user_table}
                WHERE id = ?
            """, (match['profile_id'],))

            profile_row = cursor.fetchone()
            if profile_row:
                match['profile_name'] = profile_row[0]
                match['company'] = profile_row[1]
                match['position'] = profile_row[2]
                match['phone'] = profile_row[3]

            matches.append(match)

        # 获取未读数量
        cursor.execute("""
            SELECT COUNT(*) FROM intent_matches
            WHERE user_id = ?
            AND datetime(created_at) > datetime('now', '-24 hours')
            AND (is_read IS NULL OR is_read = 0)
        """, (query_user_id,))

        unread_count = cursor.fetchone()[0]

        conn.close()

        return {
            "success": True,
            "matches": matches,
            "unread_count": unread_count,
            "has_new": unread_count > 0
        }

    except Exception as e:
        logger.error(f"获取匹配通知失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取匹配通知失败"
        )


@router.post("/api/notifications/matches/{match_id}/read")
async def mark_match_as_read(
    match_id: int,
    current_user: str = Depends(verify_user_token)
):
    """标记匹配通知为已读"""
    try:
        query_user_id = get_query_user_id(current_user)

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 更新已读状态
        cursor.execute("""
            UPDATE intent_matches
            SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (match_id, query_user_id))

        conn.commit()
        conn.close()

        return {"success": True, "message": "已标记为已读"}

    except Exception as e:
        logger.error(f"标记已读失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标记已读失败"
        )