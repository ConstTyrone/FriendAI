# routes/ai_services.py
"""
AI服务相关路由
处理语音解析、用户画像提取、智能分析等AI功能
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import tempfile
import os

from .auth import verify_user_token, get_query_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# 数据库导入（与main.py保持一致）
try:
    from ...database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("AI Services模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("AI Services模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


# Pydantic模型
class ParseVoiceTextRequest(BaseModel):
    """解析语音文本请求模型"""
    text: str  # 语音识别后的文本内容
    merge_mode: bool = False  # 是否为合并模式（用于编辑现有联系人）


class ParseVoiceTextResponse(BaseModel):
    """解析语音文本响应模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.post("/api/profiles/parse-voice")
async def parse_voice_text(
    request: ParseVoiceTextRequest,
    current_user: str = Depends(verify_user_token)
):
    """解析语音文本，提取用户画像信息"""
    try:
        # 初始化AI服务
        from ...services.ai_service import UserProfileExtractor
        ai_service = UserProfileExtractor()

        # 使用AI服务解析文本
        result = ai_service.extract_user_profile(request.text, is_chat_record=False)

        # AI服务返回的格式是 {"success": True, "data": {"user_profiles": [...]}, "error": None}
        # 需要从嵌套的data字段中获取user_profiles
        if not result or not result.get("data"):
            return ParseVoiceTextResponse(
                success=False,
                message="无法从文本中提取有效信息"
            )

        ai_data = result.get("data", {})
        if "user_profiles" not in ai_data:
            return ParseVoiceTextResponse(
                success=False,
                message="无法从文本中提取有效信息"
            )

        user_profiles = ai_data.get("user_profiles", [])

        if not user_profiles:
            return ParseVoiceTextResponse(
                success=False,
                message="未能识别出联系人信息"
            )

        # 取第一个识别到的用户画像
        profile = user_profiles[0]

        # 转换字段名以匹配前端表单
        parsed_data = {
            "name": profile.get("name", "") if profile.get("name") != "未知" else "",
            "gender": profile.get("gender", "") if profile.get("gender") != "未知" else "",
            "age": profile.get("age", "") if profile.get("age") != "未知" else "",
            "phone": profile.get("phone", "") if profile.get("phone") != "未知" else "",
            "wechat_id": "",  # AI通常不能识别微信号
            "email": "",  # AI通常不能识别邮箱
            "location": profile.get("location", "") if profile.get("location") != "未知" else "",
            "address": profile.get("location", "") if profile.get("location") != "未知" else "",
            "marital_status": profile.get("marital_status", "") if profile.get("marital_status") != "未知" else "",
            "education": profile.get("education", "") if profile.get("education") != "未知" else "",
            "company": profile.get("company", "") if profile.get("company") != "未知" else "",
            "position": profile.get("position", "") if profile.get("position") != "未知" else "",
            "asset_level": profile.get("asset_level", "") if profile.get("asset_level") != "未知" else "",
            "personality": profile.get("personality", "") if profile.get("personality") != "未知" else "",
            "notes": result.get("summary", "")  # 使用AI的总结作为备注
        }

        # 如果是合并模式，只返回非空字段
        if request.merge_mode:
            parsed_data = {k: v for k, v in parsed_data.items() if v and v != ""}

        return ParseVoiceTextResponse(
            success=True,
            data=parsed_data,
            message="解析成功"
        )

    except Exception as e:
        logger.error(f"解析语音文本失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return ParseVoiceTextResponse(
            success=False,
            message=f"解析失败: {str(e)}"
        )


@router.post("/api/profiles/parse-voice-audio")
async def parse_voice_audio(
    audio_file: UploadFile = File(...),
    merge_mode: str = Form("false"),  # 接收字符串形式的布尔值
    contact_id: Optional[str] = Form(None),  # 编辑模式下的联系人ID
    current_user: str = Depends(verify_user_token)
):
    """接收音频文件，进行ASR识别后解析用户画像"""
    logger.info(f"收到语音上传请求，用户: {current_user}")
    logger.info(f"音频文件名: {audio_file.filename}, 大小: {audio_file.size if hasattr(audio_file, 'size') else '未知'}")
    logger.info(f"合并模式: {merge_mode}")
    logger.info(f"联系人ID: {contact_id}")

    # 将字符串转换为布尔值
    merge_mode = merge_mode.lower() == "true"

    temp_file_path = None
    try:
        # 保存上传的音频文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_file_path = tmp_file.name
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_file.flush()

        logger.info(f"音频文件已保存到: {temp_file_path}")

        # 初始化媒体处理器
        from ...services.media_processor import MediaProcessor
        media_processor = MediaProcessor()

        # 使用ASR进行语音识别
        logger.info("开始语音识别...")
        recognized_text = None
        intermediate_results = []

        try:
            # 尝试使用阿里云ASR
            from ...services.media_processor import AliyunASRProcessor
            asr_processor = AliyunASRProcessor()
            # 请求返回中间结果
            asr_result = asr_processor.recognize_speech(temp_file_path, return_intermediate=True)

            if isinstance(asr_result, dict):
                recognized_text = asr_result.get('final_text')
                intermediate_results = asr_result.get('intermediate_results', [])
                logger.info(f"ASR识别成功: {recognized_text[:100] if recognized_text else '无内容'}...")
                logger.info(f"中间结果数量: {len(intermediate_results)}")
            else:
                # 兼容旧版本返回格式
                recognized_text = asr_result
                logger.info(f"ASR识别成功: {recognized_text[:100] if recognized_text else '无内容'}...")
        except Exception as asr_error:
            logger.error(f"ASR识别出错: {str(asr_error)}")
            recognized_text = None

        if not recognized_text:
            logger.warning("ASR识别失败，返回错误提示")
            # 如果ASR失败，可以返回错误或使用其他备用方案
            return ParseVoiceTextResponse(
                success=False,
                message="语音识别失败，请重试或使用文字输入"
            )

        logger.info(f"语音识别结果: {recognized_text}")

        # 如果是编辑模式且有contact_id，获取现有联系人数据并与新识别的文本合并
        if merge_mode and contact_id:
            logger.info(f"编辑模式，获取现有联系人数据: {contact_id}")
            try:
                # 获取查询用户ID
                query_user_id = get_query_user_id(current_user)

                # 获取现有联系人数据 - 使用统一的数据库实例
                existing_profile = db.get_user_profile_detail(query_user_id, int(contact_id))

                if existing_profile:
                    logger.info(f"找到现有联系人: {existing_profile.get('profile_name', '')}")

                    # 构建合并提示，让AI整合新旧数据 - 使用正确的字段访问方式
                    merge_prompt = f"""你需要智能整合以下两部分信息：

【现有联系人信息】
姓名: {existing_profile.get('profile_name', '未知')}
性别: {existing_profile.get('gender', '未知')}
年龄: {existing_profile.get('age', '未知')}
电话: {existing_profile.get('phone', '未知')}
微信号: {existing_profile.get('wechat_id', '未知')}
邮箱: {existing_profile.get('email', '未知')}
所在地: {existing_profile.get('location', '未知')}
婚育: {existing_profile.get('marital_status', '未知')}
学历: {existing_profile.get('education', '未知')}
公司: {existing_profile.get('company', '未知')}
职位: {existing_profile.get('position', '未知')}
资产水平: {existing_profile.get('asset_level', '未知')}
性格: {existing_profile.get('personality', '未知')}
备注: {existing_profile.get('ai_summary', '无')}

【新语音输入的信息】
{recognized_text}

请智能整合上述信息，生成一个更完整的用户画像。整合规则：
1. 如果新信息中有更具体、更准确的数据，使用新信息替换旧信息
2. 如果新信息是对现有信息的补充，将两者合并
3. 如果新信息中没有提到某个字段，保留现有的有效信息（不要输出"未知"）
4. 如果旧信息为"未知"而新信息有值，使用新信息
5. 对于备注字段，如果两者都有内容，将新的备注追加到原有备注后
6. 输出完整的用户画像，所有有效字段都要包含"""

                    # 使用AI服务解析整合后的文本
                    from ...services.ai_service import UserProfileExtractor
                    ai_service = UserProfileExtractor()
                    result = ai_service.extract_user_profile(merge_prompt, is_chat_record=False)
                else:
                    logger.warning(f"未找到联系人: {contact_id}")
                    # 如果没找到现有联系人，直接使用新识别的文本
                    from ...services.ai_service import UserProfileExtractor
                    ai_service = UserProfileExtractor()
                    result = ai_service.extract_user_profile(recognized_text, is_chat_record=False)
            except Exception as e:
                logger.error(f"获取现有联系人数据失败: {e}")
                logger.error(f"错误详情: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # 出错时直接使用新识别的文本
                from ...services.ai_service import UserProfileExtractor
                ai_service = UserProfileExtractor()
                result = ai_service.extract_user_profile(recognized_text, is_chat_record=False)
        else:
            # 新建模式，直接使用识别的文本
            from ...services.ai_service import UserProfileExtractor
            ai_service = UserProfileExtractor()
            result = ai_service.extract_user_profile(recognized_text, is_chat_record=False)

        if not result:
            logger.warning(f"AI解析失败，无返回结果。识别文本: {recognized_text}")
            return ParseVoiceTextResponse(
                success=False,
                message="AI解析失败，请重试",
                data={"recognized_text": recognized_text}  # 返回识别的原始文本
            )

        # AI服务返回的格式是 {"success": True, "data": {"user_profiles": [...]}, "error": None}
        # 需要从嵌套的data字段中获取user_profiles
        ai_data = result.get("data", {})
        if "user_profiles" not in ai_data or not ai_data.get("user_profiles"):
            logger.warning(f"AI解析返回但无有效用户画像。结果: {result}")
            return ParseVoiceTextResponse(
                success=False,
                message="AI无法从语音内容中提取出有效的联系人信息",
                data={"recognized_text": recognized_text}  # 返回识别的原始文本
            )

        user_profiles = ai_data.get("user_profiles", [])

        # 取第一个识别到的用户画像
        profile = user_profiles[0]

        # 转换字段名以匹配前端表单
        parsed_data = {
            "name": profile.get("name", "") if profile.get("name") != "未知" else "",
            "gender": profile.get("gender", "") if profile.get("gender") != "未知" else "",
            "age": profile.get("age", "") if profile.get("age") != "未知" else "",
            "phone": profile.get("phone", "") if profile.get("phone") != "未知" else "",
            "wechat_id": "",  # AI通常不能识别微信号
            "email": "",  # AI通常不能识别邮箱
            "location": profile.get("location", "") if profile.get("location") != "未知" else "",
            "address": profile.get("location", "") if profile.get("location") != "未知" else "",
            "marital_status": profile.get("marital_status", "") if profile.get("marital_status") != "未知" else "",
            "education": profile.get("education", "") if profile.get("education") != "未知" else "",
            "company": profile.get("company", "") if profile.get("company") != "未知" else "",
            "position": profile.get("position", "") if profile.get("position") != "未知" else "",
            "asset_level": profile.get("asset_level", "") if profile.get("asset_level") != "未知" else "",
            "personality": profile.get("personality", "") if profile.get("personality") != "未知" else "",
            "notes": result.get("summary", "")  # 使用AI的总结作为备注
        }

        # 如果是合并模式，只返回非空字段
        if merge_mode:
            parsed_data = {k: v for k, v in parsed_data.items() if v and v != ""}

        logger.info(f"AI解析音频成功，提取字段数: {len([k for k, v in parsed_data.items() if v])}")

        return ParseVoiceTextResponse(
            success=True,
            data=parsed_data,
            message="语音解析成功",
        )

    except Exception as e:
        logger.error(f"解析语音音频失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return ParseVoiceTextResponse(
            success=False,
            message=f"处理失败: {str(e)}"
        )

    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info("临时音频文件已清理")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")