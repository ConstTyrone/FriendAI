# ai_service.py
"""
AI对话服务 - 使用通义千问提供智能对话回复
对话历史通过Redis持久化存储，支持服务重启后恢复上下文
"""
import requests
import json
from ..config.config import config
import logging

logger = logging.getLogger(__name__)

class ChatService:
    """AI对话服务 - 基于通义千问的智能对话"""

    def __init__(self):
        self.api_key = config.qwen_api_key
        self.api_endpoint = config.qwen_api_endpoint
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def chat(self, user_message: str, user_id: str = None, system_prompt: str = None) -> dict:
        """
        AI对话回复

        Args:
            user_message (str): 用户消息文本
            user_id (str): 用户ID（可选，用于维护对话上下文）
            system_prompt (str): 系统提示词（可选）

        Returns:
            dict: {
                'success': bool,
                'reply': str,  # AI回复内容
                'error': str   # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"收到用户消息: {user_message[:100]}...")

            # 构建对话消息列表
            messages = []

            # 添加系统提示词（如果有）
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            else:
                # 默认系统提示词
                messages.append({
                    "role": "system",
                    "content": "你是一个友好、专业的AI助手，请用简洁、清晰的语言回答用户的问题。"
                })

            # 从Redis获取历史对话（如果有用户ID）
            if user_id:
                try:
                    from .redis_state_manager import state_manager
                    # 获取最近10轮对话（20条消息）
                    history = state_manager.get_conversation_history(user_id, max_messages=20)
                    if history:
                        messages.extend(history)
                        logger.info(f"从Redis加载对话历史: user_id={user_id}, count={len(history)}")
                except Exception as e:
                    logger.warning(f"获取对话历史失败，将不使用历史上下文: {e}")

            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": user_message
            })

            # 调用通义千问API
            payload = {
                "model": "qwen-plus",  # 或 qwen-turbo, qwen-max
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.8,
                "max_tokens": 1500
            }

            logger.info(f"调用AI API，消息数: {len(messages)}")

            response = requests.post(
                f"{self.api_endpoint}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            result = response.json()
            # 记录响应状态和摘要信息
            choices_count = len(result.get('choices', []))
            logger.info(f"AI API响应: status_code={response.status_code}, choices_count={choices_count}")

            # 提取AI回复
            if 'choices' in result and len(result['choices']) > 0:
                ai_reply = result['choices'][0]['message']['content']

                # 保存对话历史到Redis（如果有用户ID）
                if user_id:
                    try:
                        from .redis_state_manager import state_manager
                        # 保存用户消息
                        state_manager.add_conversation_message(user_id, "user", user_message)
                        # 保存AI回复
                        state_manager.add_conversation_message(user_id, "assistant", ai_reply)
                        logger.info(f"对话历史已保存到Redis: user_id={user_id}")
                    except Exception as e:
                        logger.warning(f"保存对话历史失败: {e}")

                logger.info(f"AI回复成功: {ai_reply[:100]}...")

                return {
                    'success': True,
                    'reply': ai_reply
                }
            else:
                error_msg = "API返回格式错误，未找到回复内容"
                logger.error(f"{error_msg}: {result}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except requests.Timeout:
            error_msg = "AI API请求超时"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"AI对话处理异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }

    def clear_history(self, user_id: str):
        """清除指定用户的对话历史"""
        try:
            from .redis_state_manager import state_manager
            state_manager.clear_conversation_history(user_id)
            logger.info(f"已清除用户 {user_id} 的对话历史")
        except Exception as e:
            logger.error(f"清除对话历史失败: {e}")

# 创建全局对话服务实例
chat_service = ChatService()
