# routes/relationships.py
"""
关系管理相关路由
处理用户关系网络的分析、确认、忽略等操作
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List
import logging

from .auth import verify_user_token, get_query_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# 数据库导入（与main.py保持一致）
try:
    from ...database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("Relationships模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("Relationships模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


def validate_relationship_data(relationships):
    """验证和标准化关系数据，确保前后端数据一致性"""
    if not relationships:
        return []

    def normalize_confidence_score(value):
        """标准化置信度分数"""
        if value is None or value == '' or value == 'null':
            return 0.5
        try:
            score = float(value)
            if score > 1:
                score = score / 100
            return max(0.0, min(1.0, score))
        except (ValueError, TypeError):
            logger.warning(f"无法解析置信度值: {value}, 使用默认值0.5")
            return 0.5

    validated_relationships = []
    for rel in relationships:
        # 标准化置信度分数
        if 'confidence_score' in rel:
            rel['confidence_score'] = normalize_confidence_score(rel['confidence_score'])
        elif 'confidence' in rel:
            rel['confidence_score'] = normalize_confidence_score(rel['confidence'])
            del rel['confidence']

        if 'confidence_score' not in rel:
            rel['confidence_score'] = 0.5

        validated_relationships.append(rel)

    return validated_relationships


@router.get("/api/relationships/{profile_id}")
async def get_profile_relationships(
    profile_id: int,
    current_user: str = Depends(verify_user_token)
):
    """获取指定画像的关系网络"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 获取关系网络数据
        relationships = relationship_service.get_relationships_for_profile(query_user_id, profile_id)

        # 验证和标准化数据
        validated_relationships = validate_relationship_data(relationships)

        return {
            "success": True,
            "profile_id": profile_id,
            "relationships": validated_relationships,
            "total": len(validated_relationships)
        }

    except Exception as e:
        logger.error(f"获取关系网络失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取关系网络失败: {str(e)}"
        )


@router.get("/api/relationships/stats")
async def get_relationships_stats(
    current_user: str = Depends(verify_user_token)
):
    """获取关系网络统计信息"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 获取统计数据
        stats = relationship_service.get_relationship_stats(query_user_id)

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"获取关系统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取关系统计失败: {str(e)}"
        )


@router.get("/api/relationships")
async def get_all_relationships(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: str = Depends(verify_user_token)
):
    """获取所有关系列表"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 获取关系列表
        relationships = relationship_service.get_all_relationships(
            query_user_id,
            status_filter=status_filter,
            limit=limit
        )

        # 验证和标准化数据
        validated_relationships = validate_relationship_data(relationships)

        return {
            "success": True,
            "relationships": validated_relationships,
            "total": len(validated_relationships),
            "filter": status_filter
        }

    except Exception as e:
        logger.error(f"获取关系列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取关系列表失败: {str(e)}"
        )


@router.post("/api/relationships/{relationship_id}/confirm")
async def confirm_relationship(
    relationship_id: int,
    current_user: str = Depends(verify_user_token)
):
    """确认关系"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 确认关系
        success = relationship_service.confirm_relationship(query_user_id, relationship_id)

        if success:
            return {
                "success": True,
                "message": "关系确认成功",
                "relationship_id": relationship_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="关系不存在或操作失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认关系失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"确认关系失败: {str(e)}"
        )


@router.post("/api/relationships/{relationship_id}/ignore")
async def ignore_relationship(
    relationship_id: int,
    current_user: str = Depends(verify_user_token)
):
    """忽略关系"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 忽略关系
        success = relationship_service.ignore_relationship(query_user_id, relationship_id)

        if success:
            return {
                "success": True,
                "message": "关系已忽略",
                "relationship_id": relationship_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="关系不存在或操作失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"忽略关系失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"忽略关系失败: {str(e)}"
        )


@router.post("/api/relationships/{contact_id}/reanalyze")
async def reanalyze_contact_relationships(
    contact_id: int,
    current_user: str = Depends(verify_user_token)
):
    """重新分析联系人关系"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 重新分析关系
        result = relationship_service.reanalyze_contact(query_user_id, contact_id)

        return {
            "success": True,
            "message": "重新分析完成",
            "contact_id": contact_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"重新分析关系失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新分析失败: {str(e)}"
        )


@router.get("/api/relationships/detail/{relationship_id}")
async def get_relationship_detail(
    relationship_id: int,
    current_user: str = Depends(verify_user_token)
):
    """获取关系详情"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取关系网络服务
        from ...services.relationship_service import get_relationship_service
        relationship_service = get_relationship_service()

        # 获取关系详情
        relationship = relationship_service.get_relationship_detail(query_user_id, relationship_id)

        if relationship:
            # 验证和标准化数据
            validated_relationship = validate_relationship_data([relationship])[0]

            return {
                "success": True,
                "relationship": validated_relationship
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="关系不存在"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取关系详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取关系详情失败: {str(e)}"
        )


@router.post("/api/relationships/{contact_id}/ai-analyze")
async def ai_analyze_contact_relationships(
    contact_id: int,
    current_user: str = Depends(verify_user_token)
):
    """AI分析联系人关系"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 获取AI关系分析服务
        from ...services.ai_relationship_analyzer import ai_relationship_analyzer

        # 执行AI分析
        result = await ai_relationship_analyzer.analyze_contact(query_user_id, contact_id)

        return {
            "success": True,
            "message": "AI分析完成",
            "contact_id": contact_id,
            "analysis_result": result
        }

    except Exception as e:
        logger.error(f"AI分析关系失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI分析失败: {str(e)}"
        )