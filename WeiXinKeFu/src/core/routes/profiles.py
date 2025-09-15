# routes/profiles.py
"""
用户画像CRUD相关路由
处理用户画像的创建、读取、更新、删除等操作
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
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
        logger.info("Profiles模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("Profiles模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


# Pydantic模型
class SourceMessage(BaseModel):
    id: str
    timestamp: str
    message_type: str
    wechat_msg_id: Optional[str] = None
    raw_content: Optional[str] = None
    processed_content: Optional[str] = None
    media_url: Optional[str] = None
    action: str


class UserProfile(BaseModel):
    id: int
    profile_name: str
    gender: Optional[str] = None
    age: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    asset_level: Optional[str] = None
    personality: Optional[str] = None
    ai_summary: Optional[str] = None
    confidence_score: Optional[float] = None
    source_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    source: Optional[str] = None
    source_messages: Optional[List[SourceMessage]] = None
    source_timestamp: Optional[str] = None


class UserProfilesResponse(BaseModel):
    total: int
    profiles: List[UserProfile]
    page: int
    page_size: int
    total_pages: int


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


# 基础CRUD路由
@router.get("/api/profiles", response_model=UserProfilesResponse)
async def get_user_profiles(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    current_user: str = Depends(verify_user_token)
):
    """获取用户的画像列表（分页）"""
    try:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        offset = (page - 1) * page_size

        # 获取查询用户ID（优先使用external_userid）
        query_user_id = get_query_user_id(current_user)

        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            limit=page_size,
            offset=offset,
            search=search
        )

        total_pages = (total + page_size - 1) // page_size

        return UserProfilesResponse(
            total=total,
            profiles=profiles,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"获取用户画像列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取画像列表失败"
        )


@router.get("/api/profiles/{profile_id}")
async def get_user_profile(
    profile_id: int,
    current_user: str = Depends(verify_user_token)
):
    """获取单个用户画像详情"""
    try:
        query_user_id = get_query_user_id(current_user)
        profile = db.get_user_profile_by_id(query_user_id, profile_id)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="画像不存在"
            )

        return {
            "success": True,
            "profile": profile
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户画像详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取画像详情失败"
        )


@router.delete("/api/profiles/{profile_id}")
async def delete_user_profile(
    profile_id: int,
    current_user: str = Depends(verify_user_token)
):
    """删除用户画像"""
    try:
        query_user_id = get_query_user_id(current_user)

        # 检查画像是否存在
        profile = db.get_user_profile_by_id(query_user_id, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="画像不存在"
            )

        # 删除画像
        success = db.delete_user_profile(query_user_id, profile_id)

        if success:
            return {
                "success": True,
                "message": "画像删除成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="画像删除失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户画像失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除画像失败"
        )