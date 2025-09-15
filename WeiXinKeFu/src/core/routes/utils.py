# routes/utils.py
"""
工具类和监控相关路由
包括测试端点、状态监控、用户统计等功能
"""

from fastapi import APIRouter, Request, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sqlite3
import logging
import time

from .auth import verify_user_token, get_query_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# 数据库导入（与main.py保持一致）
try:
    from ...database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("Utils模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("Utils模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


# Pydantic模型
class UserStatsResponse(BaseModel):
    total_profiles: int
    unique_names: int
    today_profiles: int
    last_profile_at: Optional[str]
    max_profiles: int
    used_profiles: int
    max_daily_messages: int


# 基础测试和监控路由
@router.get("/")
async def root():
    """根路径测试接口"""
    return {"message": "服务器正常运行"}


@router.post("/test")
async def test_endpoint(request: Request):
    """测试接口"""
    return {"status": "success", "message": "测试成功"}


@router.get("/sync/status")
async def get_sync_status():
    """查看消息同步状态"""
    try:
        return {
            "status": "success",
            "message": "消息同步功能已简化，直接获取最新消息",
            "sync_method": "简化版 - 每次仅获取最新1条消息"
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ASR Token相关接口
@router.get("/api/asr/token/status")
async def get_asr_token_status():
    """获取ASR Token状态"""
    try:
        from ...services.media_processor import asr_processor

        token_status = asr_processor.get_token_status()

        return {
            "status": "success",
            "data": token_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取ASR Token状态失败: {e}")
        return {
            "status": "error",
            "message": f"获取ASR Token状态失败: {str(e)}"
        }


@router.post("/api/asr/token/refresh")
async def refresh_asr_token():
    """强制刷新ASR Token"""
    try:
        from ...services.asr_token_manager import force_refresh_asr_token, get_asr_token_info

        # 尝试强制刷新
        refresh_success = force_refresh_asr_token()

        if refresh_success:
            # 获取最新状态
            token_info = get_asr_token_info()
            return {
                "status": "success",
                "message": "ASR Token刷新成功",
                "data": token_info,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "ASR Token刷新失败，请检查配置和网络连接"
            }
    except Exception as e:
        logger.error(f"刷新ASR Token失败: {e}")
        return {
            "status": "error",
            "message": f"刷新ASR Token失败: {str(e)}"
        }


# 用户相关统计和查询接口
@router.get("/api/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: str = Depends(verify_user_token)):
    """获取用户统计信息"""
    try:
        query_user_id = get_query_user_id(current_user)
        stats = db.get_user_stats(query_user_id)
        return UserStatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )


@router.get("/api/search")
async def search_profiles(
    q: str,
    limit: int = 20,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    gender: Optional[str] = None,
    location: Optional[str] = None,
    current_user: str = Depends(verify_user_token)
):
    """智能搜索用户画像 - 支持多维度条件"""
    try:
        if not q or len(q.strip()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="搜索关键词不能为空"
            )

        query_user_id = get_query_user_id(current_user)
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            search=q.strip(),
            limit=limit,
            offset=0,
            age_min=age_min,
            age_max=age_max,
            gender=gender,
            location=location
        )

        return {
            "success": True,
            "total": total,
            "profiles": profiles,
            "query": q.strip(),
            "filters": {
                "age_min": age_min,
                "age_max": age_max,
                "gender": gender,
                "location": location
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智能搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索失败"
        )


@router.get("/api/recent")
async def get_recent_profiles(
    limit: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取最近的用户画像"""
    try:
        if limit < 1 or limit > 50:
            limit = 10

        query_user_id = get_query_user_id(current_user)
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            limit=limit,
            offset=0
        )

        return {
            "success": True,
            "profiles": profiles,
            "total": total
        }

    except Exception as e:
        logger.error(f"获取最近画像失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取最近画像失败"
        )


@router.get("/api/user/info")
async def get_user_info(current_user: str = Depends(verify_user_token)):
    """获取当前用户信息"""
    try:
        query_user_id = get_query_user_id(current_user)
        stats = db.get_user_stats(query_user_id)
        table_name = db._get_user_table_name(query_user_id)

        return {
            "success": True,
            "wechat_user_id": current_user,
            "table_name": table_name,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.get("/api/updates/check")
async def check_for_updates(
    last_check: Optional[str] = None,
    current_user: str = Depends(verify_user_token)
):
    """检查是否有新的画像数据"""
    try:
        # 获取最新的画像（最近1分钟内）
        query_user_id = get_query_user_id(current_user)
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            limit=5,
            offset=0
        )

        # 简单检查是否有更新（生产环境可以用更精确的时间戳对比）
        has_updates = total > 0

        return {
            "success": True,
            "has_updates": has_updates,
            "latest_profiles": profiles[:3] if has_updates else [],
            "total_profiles": total,
            "check_time": "2025-08-04T" + str(time.time())
        }

    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查更新失败"
        )


@router.get("/api/feedback/stats")
async def get_feedback_stats(
    current_user: str = Depends(verify_user_token)
):
    """获取用户反馈统计"""
    try:
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)

        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 统计反馈数据
        cursor.execute("""
            SELECT
                COUNT(*) as total_matches,
                COUNT(user_feedback) as total_feedback,
                COUNT(CASE WHEN user_feedback = 'positive' THEN 1 END) as positive_count,
                COUNT(CASE WHEN user_feedback = 'negative' THEN 1 END) as negative_count,
                COUNT(CASE WHEN user_feedback = 'ignored' THEN 1 END) as ignored_count,
                AVG(CASE WHEN user_feedback = 'positive' THEN match_score END) as positive_avg_score,
                AVG(CASE WHEN user_feedback = 'negative' THEN match_score END) as negative_avg_score
            FROM intent_matches
            WHERE user_id = ?
        """, (query_user_id,))

        result = cursor.fetchone()

        # 获取最近反馈
        cursor.execute("""
            SELECT
                im.id,
                im.match_score,
                im.user_feedback,
                im.feedback_at,
                ui.name as intent_name,
                im.profile_id
            FROM intent_matches im
            JOIN user_intents ui ON im.intent_id = ui.id
            WHERE im.user_id = ? AND im.user_feedback IS NOT NULL
            ORDER BY im.feedback_at DESC
            LIMIT 10
        """, (query_user_id,))

        recent_feedback = []
        for row in cursor.fetchall():
            recent_feedback.append({
                'id': row[0],
                'match_score': row[1],
                'feedback': row[2],
                'feedback_at': row[3],
                'intent_name': row[4],
                'profile_id': row[5]
            })

        conn.close()

        # 计算统计指标
        feedback_rate = result[1] / result[0] * 100 if result[0] > 0 else 0
        positive_rate = result[2] / result[1] * 100 if result[1] > 0 else 0
        negative_rate = result[3] / result[1] * 100 if result[1] > 0 else 0

        stats = {
            'total_matches': result[0],
            'total_feedback': result[1],
            'feedback_rate': round(feedback_rate, 1),
            'positive_count': result[2],
            'negative_count': result[3],
            'ignored_count': result[4],
            'positive_rate': round(positive_rate, 1),
            'negative_rate': round(negative_rate, 1),
            'positive_avg_score': round(result[5], 3) if result[5] else 0,
            'negative_avg_score': round(result[6], 3) if result[6] else 0,
            'score_separation': round(abs((result[5] or 0) - (result[6] or 0)), 3),
            'recent_feedback': recent_feedback,
            'collection_status': '数据收集中' if result[1] < 50 else '可以分析',
            'recommendation': '继续收集反馈' if result[1] < 50 else '已有足够数据，可以进行人工分析'
        }

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"获取反馈统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取反馈统计失败: {str(e)}"
        )