# routes/intents.py
"""
意图管理相关路由
处理用户意图的创建、读取、更新、删除等操作
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional
import logging
import json
import sqlite3

from .auth import verify_user_token, get_query_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# 数据库导入（与main.py保持一致）
try:
    from ...database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("Intents模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("Intents模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


# Pydantic模型
class CreateIntentRequest(BaseModel):
    """创建意图请求模型"""
    name: str
    description: str
    type: Optional[str] = "general"
    conditions: Optional[dict] = {}
    threshold: Optional[float] = 0.7
    priority: Optional[int] = 5
    max_push_per_day: Optional[int] = 5


class UpdateIntentRequest(BaseModel):
    """更新意图请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict] = None
    threshold: Optional[float] = None
    priority: Optional[int] = None
    max_push_per_day: Optional[int] = None
    status: Optional[str] = None


@router.post("/api/intents")
async def create_intent(
    request: CreateIntentRequest,
    current_user: str = Depends(verify_user_token)
):
    """创建新的用户意图"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        # 验证必填字段
        if not request.name or not request.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="意图名称不能为空"
            )

        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 插入意图
        cursor.execute("""
            INSERT INTO user_intents (
                user_id, name, description, type, conditions,
                threshold, priority, max_push_per_day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query_user_id,
            request.name.strip(),
            request.description,
            request.type,
            json.dumps(request.conditions, ensure_ascii=False),
            request.threshold,
            request.priority,
            request.max_push_per_day
        ))

        intent_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"成功创建意图：{intent_id}")

        return {
            "success": True,
            "message": "意图创建成功",
            "data": {
                "intentId": intent_id,
                "message": "意图创建成功，正在进行匹配分析"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建意图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建意图失败: {str(e)}"
        )


@router.get("/api/intents")
async def get_intents(
    intent_status: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取用户意图列表"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 查询意图
        offset = (page - 1) * size

        if intent_status:
            cursor.execute("""
                SELECT * FROM user_intents
                WHERE user_id = ? AND status = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """, (query_user_id, intent_status, size, offset))
        else:
            cursor.execute("""
                SELECT * FROM user_intents
                WHERE user_id = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """, (query_user_id, size, offset))

        columns = [desc[0] for desc in cursor.description]
        intents = []

        for row in cursor.fetchall():
            intent = dict(zip(columns, row))
            # 解析JSON字段
            if intent.get('conditions'):
                try:
                    intent['conditions'] = json.loads(intent['conditions'])
                except:
                    intent['conditions'] = {}

            # 获取该意图的匹配数量
            cursor.execute("""
                SELECT COUNT(*) FROM intent_matches
                WHERE intent_id = ? AND user_id = ?
            """, (intent['id'], query_user_id))
            match_count = cursor.fetchone()[0]
            intent['match_count'] = match_count

            intents.append(intent)

        # 获取总数
        if intent_status:
            cursor.execute("""
                SELECT COUNT(*) FROM user_intents
                WHERE user_id = ? AND status = ?
            """, (query_user_id, intent_status))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM user_intents
                WHERE user_id = ?
            """, (query_user_id,))

        total = cursor.fetchone()[0]
        conn.close()

        return {
            "success": True,
            "data": {
                "intents": intents,
                "total": total,
                "page": page,
                "size": size
            }
        }

    except Exception as e:
        logger.error(f"获取意图列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取意图列表失败: {str(e)}"
        )


@router.get("/api/intents/{intent_id}")
async def get_intent(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """获取意图详情"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 查询意图
        cursor.execute("""
            SELECT * FROM user_intents
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))

        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )

        columns = [desc[0] for desc in cursor.description]
        intent = dict(zip(columns, row))

        # 解析JSON字段
        if intent.get('conditions'):
            try:
                intent['conditions'] = json.loads(intent['conditions'])
            except:
                intent['conditions'] = {}

        # 获取最近的匹配记录
        cursor.execute("""
            SELECT im.*, ui.name as intent_name
            FROM intent_matches im
            LEFT JOIN user_intents ui ON im.intent_id = ui.id
            WHERE im.intent_id = ? AND im.user_id = ?
            ORDER BY im.created_at DESC
            LIMIT 10
        """, (intent_id, query_user_id))

        matches = []
        for match_row in cursor.fetchall():
            match_columns = [desc[0] for desc in cursor.description]
            match = dict(zip(match_columns, match_row))
            matches.append(match)

        intent['recent_matches'] = matches
        conn.close()

        return {
            "success": True,
            "data": intent
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取意图详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取意图详情失败: {str(e)}"
        )


@router.put("/api/intents/{intent_id}")
async def update_intent(
    intent_id: int,
    request: UpdateIntentRequest,
    current_user: str = Depends(verify_user_token)
):
    """更新意图"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 检查意图是否存在
        cursor.execute("""
            SELECT id FROM user_intents
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))

        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )

        # 构建更新语句
        update_fields = []
        params = []

        if request.name is not None:
            update_fields.append("name = ?")
            params.append(request.name.strip())

        if request.description is not None:
            update_fields.append("description = ?")
            params.append(request.description)

        if request.conditions is not None:
            update_fields.append("conditions = ?")
            params.append(json.dumps(request.conditions, ensure_ascii=False))

        if request.threshold is not None:
            update_fields.append("threshold = ?")
            params.append(request.threshold)

        if request.priority is not None:
            update_fields.append("priority = ?")
            params.append(request.priority)

        if request.max_push_per_day is not None:
            update_fields.append("max_push_per_day = ?")
            params.append(request.max_push_per_day)

        if request.status is not None:
            update_fields.append("status = ?")
            params.append(request.status)

        if not update_fields:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有要更新的字段"
            )

        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([intent_id, query_user_id])

        # 执行更新
        sql = f"""
            UPDATE user_intents
            SET {', '.join(update_fields)}
            WHERE id = ? AND user_id = ?
        """

        cursor.execute(sql, params)
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在或更新失败"
            )

        conn.close()

        logger.info(f"成功更新意图：{intent_id}")

        return {
            "success": True,
            "message": "意图更新成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新意图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新意图失败: {str(e)}"
        )


@router.delete("/api/intents/{intent_id}")
async def delete_intent(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """删除意图"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 检查意图是否存在
        cursor.execute("""
            SELECT id FROM user_intents
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))

        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )

        # 删除相关的匹配记录
        cursor.execute("""
            DELETE FROM intent_matches
            WHERE intent_id = ? AND user_id = ?
        """, (intent_id, query_user_id))

        # 删除意图
        cursor.execute("""
            DELETE FROM user_intents
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))

        conn.commit()
        conn.close()

        logger.info(f"成功删除意图：{intent_id}")

        return {
            "success": True,
            "message": "意图删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除意图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除意图失败: {str(e)}"
        )


@router.post("/api/intents/{intent_id}/match")
async def trigger_intent_match(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """手动触发意图匹配"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()

        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 检查意图是否存在
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name FROM user_intents
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))

        intent = cursor.fetchone()
        if not intent:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )

        conn.close()

        # 触发匹配（异步执行）
        try:
            from ...services.intent_matcher import intent_matcher
            match_results = await intent_matcher.match_single_intent(intent_id, query_user_id)

            return {
                "success": True,
                "message": "匹配触发成功",
                "data": {
                    "intent_id": intent_id,
                    "intent_name": intent[1],
                    "new_matches": len(match_results) if match_results else 0
                }
            }
        except Exception as match_error:
            logger.error(f"意图匹配失败: {match_error}")
            return {
                "success": False,
                "message": f"匹配执行失败: {str(match_error)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发意图匹配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发匹配失败: {str(e)}"
        )