# message_classifier.py
import re
from typing import Dict, Any

class MessageClassifier:
    def __init__(self):
        # 命令关键词
        self.command_keywords = ['帮助', 'help', '开始', 'start', '状态', 'status']
    
    def classify_message(self, message: Dict[str, Any]) -> str:
        """消息分类主函数"""
        msg_type = message.get('MsgType', '').lower()
        content = message.get('Content', '')
        
        
        if msg_type == 'text':
            return self.classify_text_message(content)
        elif msg_type == 'image':
            return 'image'
        elif msg_type == 'file':
            return 'file'
        elif msg_type == 'voice':
            return 'voice'
        elif msg_type == 'video':
            return 'video'
        elif msg_type == 'location':
            return 'location'
        elif msg_type == 'link':
            return 'link'
        elif msg_type == 'miniprogram':
            return 'miniprogram'
        elif msg_type == 'merged_msg':
            return 'chat_record'
        elif msg_type == 'event':
            return 'event'
        else:
            return 'unknown'
    
    def classify_text_message(self, content: str) -> str:
        """文本消息分类"""
        content = content.strip()
        
        # 1. 检查是否为命令
        if self.is_command(content):
            return 'command'
        
        # 2. 其他文本（不再区分聊天记录和联系人信息）
        return 'general_text'
    
    def is_command(self, content: str) -> bool:
        """判断是否为命令"""
        content_lower = content.lower()
        return any(cmd in content_lower for cmd in self.command_keywords)

# 全局分类器实例
classifier = MessageClassifier()