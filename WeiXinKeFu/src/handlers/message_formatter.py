# message_formatter_v2.py
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class MessageTextExtractor:
    """消息文本提取器 - 将各种类型的消息转换为纯文本，用于用户画像提取"""
    
    def __init__(self):
        pass
    
    def extract_text(self, message: Dict[str, Any], message_type: str) -> str:
        """
        从消息中提取纯文本内容，用于用户画像分析
        
        Args:
            message: 消息对象
            message_type: 消息类型
            
        Returns:
            str: 提取的纯文本内容
        """
        extractor_map = {
            'general_text': self._extract_text_content,
            'image': self._extract_image_content,
            'file': self._extract_file_content,
            'voice': self._extract_voice_content,
            'video': self._extract_video_content,
            'location': self._extract_location_content,
            'link': self._extract_link_content,
            'miniprogram': self._extract_miniprogram_content,
            'chat_record': self._extract_chat_record_content,
            'event': self._extract_event_content,
            'command': self._extract_command_content
        }
        
        extractor = extractor_map.get(message_type, self._extract_unknown_content)
        return extractor(message)
    
    def _get_user_context(self, message: Dict[str, Any]) -> str:
        """获取用户上下文信息"""
        user_id = message.get('FromUserName', '未知用户')
        timestamp = message.get('CreateTime', '')
        
        if timestamp:
            try:
                dt = datetime.fromtimestamp(int(timestamp))
                time_str = dt.strftime('%Y年%m月%d日 %H:%M')
            except:
                time_str = '未知时间'
        else:
            time_str = '未知时间'
        
        return f"用户{user_id}在{time_str}"
    
    def _extract_text_content(self, message: Dict[str, Any]) -> str:
        """提取文本消息内容"""
        context = self._get_user_context(message)
        content = message.get('Content', '')
        
        return f"{context}发送了以下文本消息：\n{content}"
    
    def _extract_image_content(self, message: Dict[str, Any]) -> str:
        """提取图片消息信息并进行OCR识别"""
        context = self._get_user_context(message)
        media_id = message.get('MediaId', '')
        
        # 使用ETL4LM接口进行图片OCR识别
        try:
            from ..services.media_processor import media_processor
            
            logger.info(f"🖼️ 开始图片OCR识别: {media_id}")
            ocr_text = media_processor.process_image_ocr(media_id)
            
            if ocr_text and not ocr_text.startswith('[图片OCR'):
                return f"{context}发送了一张图片，通过OCR识别出以下文字内容：\n{ocr_text}"
            else:
                # 检查是否是超时错误，提供更友好的提示
                if "超时" in str(ocr_text):
                    return f"{context}发送了一张图片。OCR识别超时，建议：\n1. 尝试发送分辨率较低的图片\n2. 检查网络连接稳定性\n3. 稍后重试"
                else:
                    return f"{context}发送了一张图片（MediaID: {media_id}）。OCR识别结果：{ocr_text or '未能识别出文字内容'}"
        except Exception as e:
            logger.error(f"图片OCR处理失败: {e}")
            return f"{context}发送了一张图片（MediaID: {media_id}）。OCR识别失败：{str(e)}"
    
    def _extract_file_content(self, message: Dict[str, Any]) -> str:
        """提取文件内容"""
        context = self._get_user_context(message)
        media_id = message.get('MediaId', '')
        filename = message.get('Title', '')
        
        logger.info(f"📁 处理文件消息: MediaId={media_id}, Title='{filename}'")
        
        # 微信客服的文件消息可能没有文件名，我们需要先下载文件来识别类型
        if not filename or filename.strip() == '':
            # 没有文件名，先尝试下载文件来识别类型
            logger.info("📁 文件名为空，尝试下载文件识别类型")
            return self._process_file_without_name(context, media_id)
        
        # 有文件名的情况，按原逻辑处理
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if file_ext in ['txt', 'doc', 'docx', 'pdf', 'xls', 'xlsx']:
            # 使用多媒体处理器提取文件内容
            from ..services.media_processor import media_processor
            file_content = media_processor.extract_file_content(media_id, filename)
            
            if file_content and not any(placeholder in file_content for placeholder in ["功能待实现", "解析失败", "处理异常"]):
                return f"{context}发送了文件《{filename}》，通过ETL接口解析出以下内容：\n{file_content}"
            else:
                return f"{context}发送了文件《{filename}》（{file_ext.upper()}格式）。文件解析结果：{file_content or '解析失败'}"
        else:
            return f"{context}发送了文件《{filename}》，文件格式为{file_ext}，暂不支持内容提取。"
    
    def _process_file_without_name(self, context: str, media_id: str) -> str:
        """处理没有文件名的文件消息（微信客服特有情况）"""
        try:
            from ..services.media_processor import media_processor
            
            # 先下载文件
            file_path = media_processor.download_media(media_id)
            if not file_path:
                return f"{context}发送了一个文件，但下载失败。"
            
            logger.info(f"📁 下载的文件路径: {file_path}")
            
            # 根据文件扩展名判断类型
            file_ext = os.path.splitext(file_path)[1].lower()
            logger.info(f"📁 识别文件扩展名: {file_ext}")
            
            # 生成默认文件名
            filename = f"文件{media_id[:8]}{file_ext}"
            
            if file_ext in ['.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx']:
                # 直接使用本地文件路径处理
                if file_ext == '.pdf':
                    # PDF使用ETL接口处理
                    with open(file_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    from media_processor import etl_processor
                    result = etl_processor.process_pdf_document(pdf_data, filename)
                    
                    # 清理临时文件
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    
                    if result['success']:
                        return f"{context}发送了一个PDF文件，通过ETL接口解析出以下内容：\n{result['text']}"
                    else:
                        error_type = result.get('metadata', {}).get('error_type', 'general_error')
                        suggestions = result.get('metadata', {}).get('suggestions', [])
                        
                        if error_type == 'timeout':
                            suggestion_text = '\n'.join([f"{i+1}. {s}" for i, s in enumerate(suggestions)]) if suggestions else "建议尝试发送较小的PDF文件"
                            return f"{context}发送了一个PDF文件。由于文档复杂，解析超时（超过5分钟）。建议：\n{suggestion_text}"
                        elif error_type == 'connection_error':
                            return f"{context}发送了一个PDF文件。ETL服务暂时不可用，请稍后重试。"
                        else:
                            return f"{context}发送了一个PDF文件。解析失败：{result.get('error', '未知错误')}"
                else:
                    # 其他文件类型使用原有逻辑
                    file_content = media_processor.extract_file_content(media_id, filename)
                    
                    if file_content and not any(placeholder in file_content for placeholder in ["功能待实现", "解析失败", "处理异常"]):
                        return f"{context}发送了一个{file_ext.upper()}文件，解析出以下内容：\n{file_content}"
                    else:
                        return f"{context}发送了一个{file_ext.upper()}文件。解析结果：{file_content or '解析失败'}"
            else:
                # 清理临时文件
                try:
                    os.remove(file_path)
                except:
                    pass
                
                return f"{context}发送了一个{file_ext.upper()}格式的文件，暂不支持内容提取。"
                
        except Exception as e:
            logger.error(f"处理无文件名文件时发生错误: {e}")
            return f"{context}发送了一个文件，但处理时发生错误：{str(e)}"
    
    
    def _extract_voice_content(self, message: Dict[str, Any]) -> str:
        """提取语音消息内容（通过语音识别转文字）"""
        context = self._get_user_context(message)
        media_id = message.get('MediaId', '')
        
        # 使用多媒体处理器进行语音转文字
        from ..services.media_processor import media_processor
        logger.info(f"🎤 开始处理语音消息: {media_id}")
        voice_text = media_processor.speech_to_text(media_id)
        
        if voice_text and not any(keyword in voice_text for keyword in ["[语音", "失败", "错误", "异常"]):
            return f"{context}发送了语音消息，语音内容为：\n{voice_text}"
        elif "ASR SDK未安装" in str(voice_text):
            return f"{context}发送了语音消息（MediaID: {media_id}）。语音识别服务未启用，请安装阿里云ASR SDK。"
        elif "格式转换失败" in str(voice_text):
            return f"{context}发送了语音消息（MediaID: {media_id}）。音频格式转换失败，请检查ffmpeg是否正确安装。"
        elif "ffmpeg未找到" in str(voice_text):
            return f"{context}发送了语音消息（MediaID: {media_id}）。\n\n🔧 需要安装音频转换工具:\n1. 下载ffmpeg: https://ffmpeg.org/download.html\n2. 添加到系统PATH环境变量\n3. 重启应用后即可识别语音"
        else:
            return f"{context}发送了语音消息（MediaID: {media_id}）。{voice_text or '语音识别服务暂时不可用'}"
    
    
    def _extract_video_content(self, message: Dict[str, Any]) -> str:
        """提取视频消息信息"""
        context = self._get_user_context(message)
        media_id = message.get('MediaId', '')
        
        # TODO: 实现视频内容分析（可选功能）
        return f"{context}发送了一个视频（MediaID: {media_id}）。注：视频内容分析功能待实现。"
    
    def _extract_location_content(self, message: Dict[str, Any]) -> str:
        """提取位置信息"""
        context = self._get_user_context(message)
        location_x = message.get('Location_X', '')
        location_y = message.get('Location_Y', '')
        label = message.get('Label', '未知位置')
        
        return f"{context}分享了位置信息：{label}（经度:{location_x}, 纬度:{location_y}）"
    
    def _extract_link_content(self, message: Dict[str, Any]) -> str:
        """提取链接信息"""
        context = self._get_user_context(message)
        title = message.get('Title', '无标题')
        description = message.get('Description', '无描述')
        url = message.get('Url', '')
        
        return f"{context}分享了链接：《{title}》\n描述：{description}\n链接地址：{url}"
    
    def _extract_miniprogram_content(self, message: Dict[str, Any]) -> str:
        """提取小程序信息"""
        context = self._get_user_context(message)
        title = message.get('Title', '无标题')
        app_id = message.get('AppId', '')
        
        return f"{context}分享了小程序：《{title}》（AppID: {app_id}）"
    
    def _extract_chat_record_content(self, message: Dict[str, Any]) -> str:
        """提取聊天记录内容 - 这是最重要的功能"""
        context = self._get_user_context(message)
        merged_msg = message.get('merged_msg', {})
        title = merged_msg.get('title', '无标题')
        items = merged_msg.get('item', [])
        
        text_content = f"{context}转发了聊天记录：《{title}》\n\n聊天记录内容：\n"
        
        for i, item in enumerate(items, 1):
            sender_name = item.get('sender_name', '未知')
            msg_content = item.get('msg_content', '')
            send_time = item.get('send_time', '')
            
            # 格式化时间
            if send_time:
                try:
                    dt = datetime.fromtimestamp(int(send_time))
                    time_formatted = dt.strftime('%H:%M')
                except:
                    time_formatted = '未知时间'
            else:
                time_formatted = '未知时间'
            
            # 解析消息内容
            try:
                content_json = json.loads(msg_content)
                msg_type = content_json.get('msgtype', '')
                
                # 调试：记录聊天记录中的消息结构
                if msg_type in ['image', 'voice', 'file']:
                    logger.info(f"🔍 聊天记录中的{msg_type}消息结构: {content_json}")
                
                if msg_type == 'text':
                    actual_content = content_json.get('text', {}).get('content', msg_content)
                elif msg_type == 'image':
                    # 处理聊天记录中的图片
                    actual_content = self._process_chat_record_image(content_json)
                elif msg_type == 'voice':
                    # 处理聊天记录中的语音
                    actual_content = self._process_chat_record_voice(content_json)
                elif msg_type == 'video':
                    actual_content = "[发送了视频]" 
                elif msg_type == 'file':
                    # 处理聊天记录中的文件
                    actual_content = self._process_chat_record_file(content_json)
                elif msg_type == 'location':
                    # 处理聊天记录中的位置信息
                    actual_content = self._process_chat_record_location(content_json)
                elif msg_type == 'link':
                    # 处理聊天记录中的链接
                    actual_content = self._process_chat_record_link(content_json)
                elif msg_type == 'miniprogram':
                    actual_content = "[分享了小程序]"
                else:
                    actual_content = f"[{msg_type}消息]"
            except:
                actual_content = msg_content
            
            text_content += f"{i}. {sender_name}（{time_formatted}）：{actual_content}\n"
        
        return text_content
    
    def _process_chat_record_image(self, content_json: Dict[str, Any]) -> str:
        """处理聊天记录中的图片消息"""
        try:
            image_data = content_json.get('image', {})
            media_id = image_data.get('media_id', '')
            
            if media_id:
                logger.info(f"🖼️ 处理聊天记录中的图片: {media_id}")
                
                try:
                    # 使用ETL4LM接口进行图片OCR识别
                    from ..services.media_processor import media_processor
                    ocr_text = media_processor.process_image_ocr(media_id)
                    
                    if ocr_text and not ocr_text.startswith('[图片OCR'):
                        return f"[发送了图片，OCR识别内容：{ocr_text}]"
                    else:
                        return f"[发送了图片，OCR识别失败]"
                except Exception as ocr_error:
                    logger.warning(f"聊天记录图片OCR处理失败: {ocr_error}")
                    return "[发送了图片，OCR处理异常]"
            else:
                return "[发送了图片]"
        except Exception as e:
            logger.error(f"处理聊天记录图片失败: {e}")
            return "[发送了图片]"
    
    def _process_chat_record_voice(self, content_json: Dict[str, Any]) -> str:
        """处理聊天记录中的语音消息"""
        try:
            voice_data = content_json.get('voice', {})
            media_id = voice_data.get('media_id', '')
            
            if media_id:
                logger.info(f"🎤 处理聊天记录中的语音: {media_id}")
                
                try:
                    # 使用语音识别处理
                    from ..services.media_processor import media_processor
                    voice_text = media_processor.speech_to_text(media_id)
                    
                    if voice_text and not any(keyword in voice_text for keyword in ["[语音", "失败", "错误", "异常"]):
                        return f"[发送了语音，识别内容：{voice_text}]"
                    else:
                        return "[发送了语音，识别失败]"
                except Exception as voice_error:
                    logger.warning(f"聊天记录语音处理失败: {voice_error}")
                    return "[发送了语音，处理异常]"
            else:
                return "[发送了语音]"
        except Exception as e:
            logger.error(f"处理聊天记录语音失败: {e}")
            return "[发送了语音]"
    
    def _process_chat_record_file(self, content_json: Dict[str, Any]) -> str:
        """处理聊天记录中的文件消息"""
        try:
            file_data = content_json.get('file', {})
            media_id = file_data.get('media_id', '')
            filename = file_data.get('filename', '') or file_data.get('title', '') or '文件'
            
            if media_id:
                logger.info(f"📁 处理聊天记录中的文件: {filename} ({media_id})")
                
                try:
                    # 使用文件内容提取
                    from ..services.media_processor import media_processor
                    file_content = media_processor.extract_file_content(media_id, filename)
                    
                    if file_content and not any(placeholder in file_content for placeholder in ["功能待实现", "解析失败", "处理异常"]):
                        return f"[发送了文件《{filename}》，内容：{file_content[:200]}{'...' if len(file_content) > 200 else ''}]"
                    else:
                        return f"[发送了文件《{filename}》，解析失败]"
                except Exception as file_error:
                    logger.warning(f"聊天记录文件处理失败: {file_error}")
                    return f"[发送了文件《{filename}》，处理异常]"
            else:
                return f"[发送了文件《{filename}》]"
        except Exception as e:
            logger.error(f"处理聊天记录文件失败: {e}")
            return "[发送了文件]"
    
    def _process_chat_record_location(self, content_json: Dict[str, Any]) -> str:
        """处理聊天记录中的位置消息"""
        try:
            location_data = content_json.get('location', {})
            name = location_data.get('name', '未知位置')
            address = location_data.get('address', '')
            lat = location_data.get('lat', '')
            lng = location_data.get('lng', '')
            
            location_info = f"位置：{name}"
            if address:
                location_info += f"（{address}）"
            if lat and lng:
                location_info += f"，坐标：{lat},{lng}"
                
            return f"[分享了{location_info}]"
        except Exception as e:
            logger.error(f"处理聊天记录位置失败: {e}")
            return "[分享了位置，解析失败]"
    
    def _process_chat_record_link(self, content_json: Dict[str, Any]) -> str:
        """处理聊天记录中的链接消息"""
        try:
            link_data = content_json.get('link', {})
            title = link_data.get('title', '无标题')
            description = link_data.get('description', '')
            url = link_data.get('url', '')
            
            link_info = f"链接：《{title}》"
            if description:
                link_info += f"，描述：{description}"
            if url:
                link_info += f"，地址：{url}"
                
            return f"[分享了{link_info}]"
        except Exception as e:
            logger.error(f"处理聊天记录链接失败: {e}")
            return "[分享了链接，解析失败]"
    
    def _extract_event_content(self, message: Dict[str, Any]) -> str:
        """提取事件信息"""
        context = self._get_user_context(message)
        event = message.get('Event', '未知事件')
        
        return f"{context}触发了系统事件：{event}"
    
    def _extract_command_content(self, message: Dict[str, Any]) -> str:
        """提取命令内容"""
        context = self._get_user_context(message)
        content = message.get('Content', '')
        
        return f"{context}发送了命令：{content}"
    
    def _extract_unknown_content(self, message: Dict[str, Any]) -> str:
        """提取未知类型消息"""
        context = self._get_user_context(message)
        msg_type = message.get('MsgType', '未知')
        
        return f"{context}发送了未知类型的消息（类型：{msg_type}）"

# 全局文本提取器实例
text_extractor = MessageTextExtractor()