# ai_service.py
"""
AI对话服务 - 使用通义千问提供智能对话回复
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
        # 对话历史（可选，用于上下文记忆）
        self.conversation_history = {}

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

            # 添加历史对话（如果有用户ID且有历史记录）
            if user_id and user_id in self.conversation_history:
                # 只保留最近5轮对话
                history = self.conversation_history[user_id][-10:]  # 5轮对话=10条消息
                messages.extend(history)

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
            logger.info(f"AI API响应: {result}")

            # 提取AI回复
            if 'choices' in result and len(result['choices']) > 0:
                ai_reply = result['choices'][0]['message']['content']

                # 保存对话历史（如果有用户ID）
                if user_id:
                    if user_id not in self.conversation_history:
                        self.conversation_history[user_id] = []

                    # 添加本轮对话
                    self.conversation_history[user_id].append({
                        "role": "user",
                        "content": user_message
                    })
                    self.conversation_history[user_id].append({
                        "role": "assistant",
                        "content": ai_reply
                    })

                    # 限制历史长度（最多保留10轮对话=20条消息）
                    if len(self.conversation_history[user_id]) > 20:
                        self.conversation_history[user_id] = self.conversation_history[user_id][-20:]

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
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"已清除用户 {user_id} 的对话历史")

# 创建全局对话服务实例
chat_service = ChatService()
