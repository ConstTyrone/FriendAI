# media_processor.py
import os
import requests
import base64
import logging
import time
import json
from typing import Dict, List, Optional, Tuple
from ..config.config import config

logger = logging.getLogger(__name__)

class ETLProcessor:
    """ETL4LM接口处理器 - 支持图片OCR和PDF文档解析"""
    
    def __init__(self):
        # ETL接口配置
        self.etl_base_url = "http://110.16.193.170:50103"
        self.predict_url = f"{self.etl_base_url}/v1/etl4llm/predict"
        self.markdown_url = f"{self.etl_base_url}/v1/etl4llm/for_gradio"
        
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        # 支持的文件类型
        self.supported_image_types = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_doc_types = ['.pdf', '.doc', '.docx']
    
    def process_image_ocr(self, image_data: bytes, filename: str) -> Dict:
        """
        处理图片OCR识别
        
        Args:
            image_data: 图片二进制数据
            filename: 文件名
            
        Returns:
            dict: 包含OCR结果的字典
        """
        try:
            logger.info(f"🖼️ 开始处理图片OCR: {filename}")
            
            # 编码为base64
            b64_data = base64.b64encode(image_data).decode('utf-8')
            
            # 构造请求参数
            payload = {
                "filename": filename,
                "b64_data": [b64_data],
                "force_ocr": True,  # 强制OCR
                "enable_formula": False,  # 图片不需要公式识别
                "for_gradio": False
            }
            
            logger.info(f"📤 发送OCR请求到ETL接口")
            
            # 发送请求 - 图片OCR相对较快，3分钟应该足够
            logger.info("⏳ 图片OCR识别中，预计1-3分钟...")
            start_time = time.time()
            response = requests.post(self.predict_url, json=payload, headers=self.headers, timeout=180)
            processing_time = time.time() - start_time
            logger.info(f"✅ 图片OCR完成，耗时: {processing_time:.2f}秒")
            
            if response.status_code != 200:
                raise Exception(f"ETL接口调用失败，状态码: {response.status_code}")
            
            result = response.json()
            
            if result.get('status_code') != 200:
                raise Exception(f"ETL处理失败: {result.get('status_message', 'Unknown error')}")
            
            # 提取文本内容
            extracted_text = self._extract_text_from_partitions(result.get('partitions', []))
            
            logger.info(f"✅ 图片OCR完成，提取文本长度: {len(extracted_text)}")
            
            return {
                "success": True,
                "text": extracted_text,
                "raw_partitions": result.get('partitions', []),
                "metadata": {
                    "filename": filename,
                    "processing_type": "image_ocr",
                    "text_length": len(extracted_text)
                }
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"图片OCR超时（超过3分钟）- 图片可能过于复杂或网络较慢"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "text": "",
                "error": error_msg,
                "metadata": {
                    "filename": filename,
                    "processing_type": "image_ocr",
                    "error_type": "timeout",
                    "suggestions": [
                        "尝试发送分辨率较低的图片",
                        "检查网络连接是否稳定",
                        "稍后重试"
                    ]
                }
            }
        except requests.exceptions.ConnectionError as e:
            error_msg = f"ETL服务连接失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "text": "",
                "error": error_msg,
                "metadata": {
                    "filename": filename,
                    "processing_type": "image_ocr",
                    "error_type": "connection_error"
                }
            }
        except Exception as e:
            logger.error(f"❌ 图片OCR处理失败: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "metadata": {
                    "filename": filename,
                    "processing_type": "image_ocr",
                    "error_type": "general_error"
                }
            }
    
    def process_pdf_document(self, pdf_data: bytes, filename: str, use_markdown: bool = True, progress_callback=None) -> Dict:
        """
        处理PDF文档解析
        
        Args:
            pdf_data: PDF二进制数据
            filename: 文件名
            use_markdown: 是否使用Markdown格式输出
            progress_callback: 进度回调函数（可选）
            
        Returns:
            dict: 包含文档解析结果的字典
        """
        try:
            logger.info(f"📄 开始处理PDF文档: {filename}")
            
            # 估算文件大小和预期处理时间
            file_size_mb = len(pdf_data) / (1024 * 1024)
            estimated_time = min(max(file_size_mb * 30, 30), 300)  # 每MB约30秒，最少30秒，最多300秒
            logger.info(f"📊 PDF文件大小: {file_size_mb:.2f}MB，预计处理时间: {estimated_time:.0f}秒")
            
            if progress_callback:
                progress_callback(f"正在处理{file_size_mb:.1f}MB的PDF文档，预计需要{estimated_time:.0f}秒...")
            
            # 编码为base64
            logger.info("🔄 正在编码PDF文件...")
            b64_data = base64.b64encode(pdf_data).decode('utf-8')
            
            # 构造请求参数
            payload = {
                "filename": filename,
                "b64_data": [b64_data],
                "force_ocr": False,  # 优先提取PDF文字层
                "enable_formula": True,  # 启用公式识别
                "for_gradio": False
            }
            
            logger.info(f"📤 发送PDF解析请求到ETL接口")
            
            # 发送请求 - PDF处理通常需要更长时间，特别是复杂文档
            logger.info("⏳ PDF解析可能需要较长时间（最多5分钟），请耐心等待...")
            start_time = time.time()
            response = requests.post(self.predict_url, json=payload, headers=self.headers, timeout=300)
            processing_time = time.time() - start_time
            logger.info(f"✅ PDF解析完成，耗时: {processing_time:.2f}秒")
            
            if response.status_code != 200:
                raise Exception(f"ETL接口调用失败，状态码: {response.status_code}")
            
            result = response.json()
            
            if result.get('status_code') != 200:
                raise Exception(f"ETL处理失败: {result.get('status_message', 'Unknown error')}")
            
            # 提取文本内容
            extracted_text = self._extract_text_from_partitions(result.get('partitions', []))
            
            # 分析文档结构
            structure_info = self._analyze_document_structure(result.get('partitions', []))
            
            logger.info(f"✅ PDF解析完成，提取文本长度: {len(extracted_text)}")
            
            return {
                "success": True,
                "text": extracted_text,
                "raw_partitions": result.get('partitions', []),
                "structure": structure_info,
                "metadata": {
                    "filename": filename,
                    "processing_type": "pdf_document",
                    "text_length": len(extracted_text),
                    "total_elements": len(result.get('partitions', []))
                }
            }
                
        except requests.exceptions.Timeout:
            error_msg = f"PDF解析超时（超过5分钟）- 文档可能过于复杂"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "text": "",
                "error": error_msg,
                "metadata": {
                    "filename": filename,
                    "processing_type": "pdf_document",
                    "error_type": "timeout",
                    "suggestions": [
                        "尝试发送页数较少的PDF文件",
                        "或将PDF拆分成多个小文件",
                        "也可以直接描述文档内容",
                        "检查网络连接稳定性"
                    ]
                }
            }
        except requests.exceptions.ConnectionError as e:
            error_msg = f"ETL服务连接失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "text": "",
                "error": error_msg,
                "metadata": {
                    "filename": filename,
                    "processing_type": "pdf_document",
                    "error_type": "connection_error"
                }
            }
        except Exception as e:
            logger.error(f"❌ PDF文档处理失败: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "metadata": {
                    "filename": filename,
                    "processing_type": "pdf_document",
                    "error_type": "general_error"
                }
            }
    
    def _extract_text_from_partitions(self, partitions: List[Dict]) -> str:
        """从分段结果中提取纯文本"""
        extracted_texts = []
        
        for partition in partitions:
            text = partition.get('text', '').strip()
            if text:
                element_type = partition.get('type', '')
                
                # 根据元素类型添加格式
                if element_type == 'Title':
                    extracted_texts.append(f"## {text}")
                elif element_type == 'NarrativeText':
                    extracted_texts.append(text)
                elif element_type == 'Table':
                    extracted_texts.append(f"[表格内容] {text}")
                elif element_type == 'Image':
                    extracted_texts.append(f"[图片描述] {text}")
                elif element_type == 'Equation':
                    extracted_texts.append(f"[公式] {text}")
                else:
                    extracted_texts.append(text)
        
        return '\n\n'.join(extracted_texts)
    
    def _analyze_document_structure(self, partitions: List[Dict]) -> Dict:
        """分析文档结构"""
        structure = {
            "total_elements": len(partitions),
            "element_types": {},
            "has_tables": False,
            "has_images": False,
            "has_formulas": False,
            "title_count": 0,
            "text_blocks": 0
        }
        
        for partition in partitions:
            element_type = partition.get('type', 'Unknown')
            
            # 统计元素类型
            if element_type in structure["element_types"]:
                structure["element_types"][element_type] += 1
            else:
                structure["element_types"][element_type] = 1
            
            # 特殊元素标记
            if element_type == 'Table':
                structure["has_tables"] = True
            elif element_type == 'Image':
                structure["has_images"] = True
            elif element_type == 'Equation':
                structure["has_formulas"] = True
            elif element_type == 'Title':
                structure["title_count"] += 1
            elif element_type == 'NarrativeText':
                structure["text_blocks"] += 1
        
        return structure

# 全局ETL处理器实例
etl_processor = ETLProcessor()

class AliyunASRProcessor:
    """阿里云ASR语音识别处理器"""
    
    def __init__(self):
        self.appkey = config.asr_appkey
        self.token = config.asr_token
        self.url = config.asr_url
        self._recognition_result = None
        self._recognition_complete = False
        self._recognition_error = None
        self._connection_active = False
    
    def _reset_state(self):
        """重置识别状态"""
        self._recognition_result = None
        self._recognition_complete = False
        self._recognition_error = None
        self._connection_active = False
        # 清除启动确认标志
        if hasattr(self, '_start_confirmed'):
            delattr(self, '_start_confirmed')
        
    def _on_start(self, message, *args):
        """识别开始回调"""
        logger.info("🎤 ASR识别开始")
        self._start_confirmed = True  # 标记启动确认
        self._recognition_complete = False
        self._recognition_error = None
        self._connection_active = True  # 标记连接活跃
        
    def _on_result_changed(self, message, *args):
        """中间结果回调"""
        # logger.info(f"🔄 ASR中间结果: {message}")
        try:
            result = json.loads(message)
            if result.get('header', {}).get('status') == 20000000:
                self._recognition_result = result.get('payload', {}).get('result', '')
        except:
            pass
            
    def _on_completed(self, message, *args):
        """识别完成回调"""
        logger.info("✅ ASR识别完成")
        try:
            result = json.loads(message)
            if result.get('header', {}).get('status') == 20000000:
                self._recognition_result = result.get('payload', {}).get('result', '')
                if self._recognition_result:
                    logger.info(f"📝 识别结果: {self._recognition_result}")
                self._recognition_complete = True
            else:
                self._recognition_error = f"ASR错误: {result.get('header', {}).get('status_text', '未知错误')}"
        except Exception as e:
            self._recognition_error = f"解析ASR结果失败: {str(e)}"
            
    def _on_error(self, message, *args):
        """错误回调"""
        logger.error(f"❌ ASR错误: {message}")
        self._recognition_error = f"ASR服务错误: {message}"
        
    def _on_close(self, *args):
        """连接关闭回调"""
        logger.info("🔚 ASR连接关闭")
        self._connection_active = False  # 标记连接断开
        self._recognition_complete = True
        
    def recognize_speech(self, audio_file_path: str) -> Optional[str]:
        """
        识别语音文件
        
        Args:
            audio_file_path: 音频文件路径
            
        Returns:
            str: 识别的文本内容，失败返回None
        """
        try:
            # 检查nls模块是否可用
            try:
                import nls
            except ImportError:
                logger.error("阿里云ASR SDK未安装，请运行: pip install alibabacloud-nls")
                return "[语音识别失败: ASR SDK未安装]"
            
            logger.info(f"🎤 开始语音识别: {audio_file_path}")
            
            # 读取音频文件
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            
            # 重置识别状态
            self._reset_state()
            
            # 启用NLS SDK调试日志（可选）
            # nls.enableTrace(True)
            
            # 创建识别器
            sr = nls.NlsSpeechRecognizer(
                url=self.url,
                token=self.token,
                appkey=self.appkey,
                on_start=self._on_start,
                on_result_changed=self._on_result_changed,
                on_completed=self._on_completed,
                on_error=self._on_error,
                on_close=self._on_close,
                callback_args=["voice_recognition"]  # 添加回调参数
            )
            
            # 开始识别
            logger.info("📡 正在启动ASR识别...")
            start_result = sr.start(aformat="pcm", 
                                  sample_rate=16000,
                                  ch=1,
                                  enable_intermediate_result=False,  # 先关闭中间结果
                                  enable_punctuation_prediction=True,
                                  enable_inverse_text_normalization=True,
                                  timeout=10)
            
            if start_result is False:  # 只有明确返回False才是失败
                logger.error("调用start()失败")
                return "[语音识别失败: 调用启动方法失败]"
            
            # 等待识别真正开始（等待on_start回调）
            start_wait = 0
            while not hasattr(self, '_start_confirmed') and start_wait < 10:
                time.sleep(0.1)
                start_wait += 0.1
            
            if not hasattr(self, '_start_confirmed'):
                logger.error("等待ASR启动超时")
                sr.shutdown()  # 确保关闭连接
                return "[语音识别失败: 启动超时]"
            
            logger.info("✅ ASR识别启动成功")
            
            # 再次检查连接是否仍然活跃
            if not self._connection_active:
                logger.error("ASR连接未激活，无法发送音频数据")
                sr.shutdown()
                return "[语音识别失败: 连接未激活]"
            
            # 发送音频数据（每次发送640字节）
            try:
                slices = zip(*(iter(audio_data),) * 640)
                chunk_count = 0
                total_chunks = len(audio_data) // 640
                
                for chunk in slices:
                    # 在每次发送前检查连接状态
                    if not self._connection_active:
                        logger.warning(f"连接在发送第{chunk_count}块时断开")
                        break
                        
                    try:
                        sr.send_audio(bytes(chunk))
                        chunk_count += 1
                        time.sleep(0.01)  # 模拟实时发送
                    except Exception as send_error:
                        logger.error(f"发送音频数据失败: {send_error}")
                        # 如果是连接问题，停止发送
                        if "Need start before send" in str(send_error):
                            return "[语音识别失败: 连接问题]"
                        raise send_error
                
                logger.info(f"📊 音频数据发送完成 ({chunk_count} 块)")
                
                if chunk_count == 0:
                    logger.error("未能发送任何音频数据")
                    sr.shutdown()
                    return "[语音识别失败: 未能发送音频数据]"
                    
            except Exception as send_exception:
                logger.error(f"发送音频数据时发生异常: {send_exception}")
                sr.shutdown()
                return f"[语音识别失败: 发送异常 - {str(send_exception)}]"
            
            # 停止识别
            logger.info("🛑 等待识别结果...")
            stop_result = sr.stop(timeout=10)
            
            # 等待识别完成（最多等待30秒）
            wait_time = 0
            while not self._recognition_complete and not self._recognition_error and wait_time < 30:
                time.sleep(0.1)
                wait_time += 0.1
                
            logger.info(f"🔍 识别等待结束 ({wait_time:.1f}秒)")
            
            # 关闭连接
            sr.shutdown()
            
            # 返回结果
            if self._recognition_error:
                logger.error(f"语音识别出错: {self._recognition_error}")
                return f"[语音识别失败: {self._recognition_error}]"
            elif self._recognition_result:
                logger.info(f"✅ 语音识别成功: {self._recognition_result}")
                return self._recognition_result
            else:
                logger.warning("语音识别未返回结果")
                return "[语音识别失败: 未识别到内容]"
                
        except Exception as e:
            logger.error(f"语音识别异常: {e}")
            return f"[语音识别异常: {str(e)}]"

# 全局ASR处理器实例
asr_processor = AliyunASRProcessor()

class MediaProcessor:
    """多媒体处理器 - 处理语音转文字和文件内容提取"""
    
    def __init__(self):
        self.temp_dir = "temp_media"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def download_media(self, media_id: str) -> Optional[str]:
        """
        通过MediaID下载媒体文件
        
        Args:
            media_id: 媒体文件ID
            
        Returns:
            str: 下载后的本地文件路径，失败返回None
        """
        try:
            from wework_client import wework_client
            
            # 获取access_token
            access_token = wework_client.get_access_token()
            
            # 下载媒体文件
            download_url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"
            
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                # 根据Content-Type确定文件扩展名
                content_type = response.headers.get('Content-Type', '')
                if 'audio' in content_type.lower():
                    ext = '.amr'  # 微信语音通常是amr格式
                elif 'image' in content_type.lower():
                    ext = '.jpg'
                elif 'application/pdf' in content_type.lower():
                    ext = '.pdf'
                elif 'application/msword' in content_type.lower():
                    ext = '.doc'
                elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type.lower():
                    ext = '.docx'
                elif 'application/vnd.ms-excel' in content_type.lower():
                    ext = '.xls'
                elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type.lower():
                    ext = '.xlsx'
                else:
                    ext = '.tmp'
                
                # 保存文件
                file_path = os.path.join(self.temp_dir, f"{media_id}{ext}")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # 如果Content-Type识别失败（扩展名为.tmp），尝试通过文件头识别
                if ext == '.tmp':
                    actual_ext = self._detect_file_type_by_header(response.content)
                    if actual_ext and actual_ext != '.tmp':
                        # 重命名文件
                        new_file_path = os.path.join(self.temp_dir, f"{media_id}{actual_ext}")
                        try:
                            os.rename(file_path, new_file_path)
                            file_path = new_file_path
                            logger.info(f"通过文件头识别文件类型: {actual_ext}")
                        except:
                            pass
                
                logger.info(f"媒体文件下载成功: {file_path}")
                return file_path
            else:
                logger.error(f"媒体文件下载失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"下载媒体文件时发生错误: {e}")
            return None
    
    def _detect_file_type_by_header(self, file_data: bytes) -> str:
        """通过文件头部魔术数字检测文件类型"""
        if not file_data or len(file_data) < 4:
            return '.tmp'
        
        # 获取文件头部字节
        header = file_data[:16] if len(file_data) >= 16 else file_data
        
        # PDF文件检测
        if file_data.startswith(b'%PDF'):
            logger.info("🔍 检测到PDF文件头部")
            return '.pdf'
        
        # JPG/JPEG文件检测
        if header.startswith(b'\xff\xd8\xff'):
            return '.jpg'
        
        # PNG文件检测
        if header.startswith(b'\x89PNG\r\n\x1a\n'):
            return '.png'
        
        # Word文档检测 (.docx)
        if header.startswith(b'PK\x03\x04') and b'word/' in file_data[:1024]:
            return '.docx'
        
        # Excel文档检测 (.xlsx)
        if header.startswith(b'PK\x03\x04') and b'xl/' in file_data[:1024]:
            return '.xlsx'
        
        # 老版本Word文档 (.doc)
        if header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            return '.doc'
        
        # TXT文件检测（简单检测是否为纯文本）
        try:
            file_data[:1024].decode('utf-8')
            return '.txt'
        except:
            try:
                file_data[:1024].decode('gbk')
                return '.txt'
            except:
                pass
        
        logger.warning(f"无法识别文件类型，文件头部: {header.hex()}")
        return '.tmp'
    
    def speech_to_text(self, media_id: str) -> Optional[str]:
        """
        语音转文字
        
        Args:
            media_id: 语音文件的MediaID
            
        Returns:
            str: 识别出的文字内容，失败返回None
        """
        try:
            # 1. 下载语音文件
            voice_file = self.download_media(media_id)
            if not voice_file:
                logger.error("语音文件下载失败")
                return None
            
            # 2. 调用语音识别服务
            # TODO: 这里需要集成具体的语音识别服务
            # 可选方案：
            # - 阿里云语音识别
            # - 腾讯云语音识别  
            # - 百度语音识别
            # - OpenAI Whisper本地部署
            
            logger.info(f"开始语音识别: {voice_file}")
            
            # 示例：使用阿里云语音识别（需要配置相关API密钥）
            text_result = self._call_speech_recognition_api(voice_file)
            
            # 3. 清理临时文件
            try:
                os.remove(voice_file)
            except:
                pass
            
            return text_result
            
        except Exception as e:
            logger.error(f"语音转文字失败: {e}")
            return None
    
    def _call_speech_recognition_api(self, voice_file_path: str) -> Optional[str]:
        """
        调用语音识别API
        
        Args:
            voice_file_path: 语音文件路径
            
        Returns:
            str: 识别结果
        """
        try:
            # 检查文件扩展名
            file_ext = os.path.splitext(voice_file_path)[1].lower()
            
            # 如果是AMR格式，需要先转换为PCM
            if file_ext == '.amr':
                logger.info("检测到AMR格式，正在转换为PCM格式...")
                
                # 转换AMR到PCM
                pcm_file_path = voice_file_path.replace('.amr', '.pcm')
                
                if self._convert_amr_to_pcm(voice_file_path, pcm_file_path):
                    logger.info(f"✅ AMR转PCM成功: {pcm_file_path}")
                    
                    # 使用转换后的PCM文件进行识别
                    result = asr_processor.recognize_speech(pcm_file_path)
                    
                    # 清理临时PCM文件
                    try:
                        os.remove(pcm_file_path)
                    except:
                        pass
                    
                    return result
                else:
                    return "[语音格式转换失败，请检查ffmpeg是否正确安装]"
            
            # 使用阿里云ASR进行识别
            logger.info(f"使用阿里云ASR识别语音: {voice_file_path}")
            result = asr_processor.recognize_speech(voice_file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"语音识别API调用失败: {e}")
            return f"[语音识别失败: {str(e)}]"
    
    def _convert_amr_to_pcm(self, amr_file: str, pcm_file: str) -> bool:
        """
        使用ffmpeg将AMR格式转换为PCM格式
        
        Args:
            amr_file: AMR音频文件路径
            pcm_file: 输出的PCM文件路径
            
        Returns:
            bool: 转换是否成功
        """
        try:
            import subprocess
            
            # ffmpeg命令：AMR转PCM，16000Hz采样率，16位，单声道
            # 临时硬编码路径解决方案
            ffmpeg_cmd = r'D:\software\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'
            
            # 检查文件是否存在
            if not os.path.exists(ffmpeg_cmd):
                # 如果硬编码路径不存在，尝试使用配置
                ffmpeg_cmd = config.ffmpeg_path
                if not os.path.exists(ffmpeg_cmd):
                    # 最后尝试PATH中的ffmpeg
                    ffmpeg_cmd = 'ffmpeg'
            cmd = [
                ffmpeg_cmd,
                '-i', amr_file,              # 输入文件
                '-f', 'wav',                 # 指定输出格式为WAV
                '-acodec', 'pcm_s16le',      # PCM 16位小端编码
                '-ar', '16000',              # 采样率16000Hz
                '-ac', '1',                  # 单声道
                '-y',                        # 覆盖输出文件
                pcm_file                     # 输出文件
            ]
            
            logger.info(f"执行ffmpeg命令: {' '.join(cmd)}")
            
            # 执行转换
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=30)  # 移除shell=True，避免路径解析问题
            
            if result.returncode == 0:
                logger.info(f"✅ ffmpeg转换成功")
                return True
            else:
                logger.error(f"ffmpeg转换失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg转换超时（30秒）")
            return False
        except FileNotFoundError:
            logger.error("ffmpeg未找到，请按以下步骤安装:")
            logger.error("1. 下载ffmpeg: https://ffmpeg.org/download.html")
            logger.error("2. 解压到某个目录，如: C:\\ffmpeg")
            logger.error("3. 将 C:\\ffmpeg\\bin 添加到系统PATH环境变量")
            logger.error("4. 重启命令行或应用程序")
            return False
        except Exception as e:
            logger.error(f"音频格式转换异常: {e}")
            return False
    
    def extract_file_content(self, media_id: str, filename: str) -> Optional[str]:
        """
        提取文件内容
        
        Args:
            media_id: 文件的MediaID
            filename: 文件名
            
        Returns:
            str: 文件文本内容，失败返回None
        """
        try:
            # 1. 下载文件
            file_path = self.download_media(media_id)
            if not file_path:
                logger.error("文件下载失败")
                return None
            
            # 2. 根据文件类型提取内容
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            content = None
            if file_ext == 'txt':
                content = self._extract_txt_content(file_path)
            elif file_ext in ['doc', 'docx']:
                content = self._extract_word_content(file_path)
            elif file_ext == 'pdf':
                content = self._extract_pdf_content(file_path)
            elif file_ext in ['xls', 'xlsx']:
                content = self._extract_excel_content(file_path)
            else:
                logger.warning(f"不支持的文件格式: {file_ext}")
            
            # 3. 清理临时文件
            try:
                os.remove(file_path)
            except:
                pass
            
            return content
            
        except Exception as e:
            logger.error(f"文件内容提取失败: {e}")
            return None
    
    def process_image_ocr(self, media_id: str, filename: str = None) -> Optional[str]:
        """
        处理图片OCR识别 - 使用ETL4LM接口
        
        Args:
            media_id: 图片的MediaID
            filename: 图片文件名（可选）
            
        Returns:
            str: OCR识别出的文字内容，失败返回None
        """
        try:
            # 1. 下载图片文件
            image_file = self.download_media(media_id)
            if not image_file:
                logger.error("图片文件下载失败")
                return None
            
            logger.info(f"🖼️ 开始OCR识别: {image_file}")
            
            # 2. 读取图片数据
            with open(image_file, 'rb') as f:
                image_data = f.read()
            
            # 3. 使用ETL处理器进行OCR
            result = etl_processor.process_image_ocr(image_data, filename or os.path.basename(image_file))
            
            # 4. 清理临时文件
            try:
                os.remove(image_file)
            except:
                pass
            
            if result['success']:
                logger.info(f"✅ 图片OCR成功，提取文本长度: {len(result['text'])}")
                return result['text']
            else:
                logger.error(f"❌ ETL图片OCR失败: {result.get('error', 'Unknown error')}")
                return f"[图片OCR失败: {result.get('error', 'Unknown error')}]"
                
        except Exception as e:
            logger.error(f"图片OCR处理失败: {e}")
            return f"[图片OCR异常: {str(e)}]"
    
    def _extract_txt_content(self, file_path: str) -> Optional[str]:
        """提取TXT文件内容"""
        try:
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"TXT文件读取成功，使用编码: {encoding}")
                    return content
                except UnicodeDecodeError:
                    continue
            
            logger.error("TXT文件读取失败：无法确定文件编码")
            return None
            
        except Exception as e:
            logger.error(f"TXT文件处理失败: {e}")
            return None
    
    def _extract_word_content(self, file_path: str) -> Optional[str]:
        """提取Word文档内容"""
        try:
            # TODO: 需要安装python-docx库
            # pip install python-docx
            
            # from docx import Document
            # doc = Document(file_path)
            # text_content = []
            # for paragraph in doc.paragraphs:
            #     text_content.append(paragraph.text)
            # return '\n'.join(text_content)
            
            logger.info("Word文档解析功能待实现（需要安装python-docx）")
            return "[Word文档解析功能待实现]"
            
        except Exception as e:
            logger.error(f"Word文档处理失败: {e}")
            return None
    
    def _extract_pdf_content(self, file_path: str) -> Optional[str]:
        """提取PDF文档内容 - 使用ETL4LM接口"""
        try:
            logger.info(f"📄 使用ETL接口解析PDF: {file_path}")
            
            # 读取PDF文件
            with open(file_path, 'rb') as f:
                pdf_data = f.read()
            
            # 使用ETL处理器
            result = etl_processor.process_pdf_document(pdf_data, os.path.basename(file_path))
            
            if result['success']:
                logger.info(f"✅ PDF解析成功，提取文本长度: {len(result['text'])}")
                return result['text']
            else:
                logger.error(f"❌ ETL PDF解析失败: {result.get('error', 'Unknown error')}")
                return f"[PDF解析失败: {result.get('error', 'Unknown error')}]"
            
        except Exception as e:
            logger.error(f"PDF文档处理失败: {e}")
            return f"[PDF处理异常: {str(e)}]"
    
    def _extract_excel_content(self, file_path: str) -> Optional[str]:
        """提取Excel文档内容"""
        try:
            # TODO: 需要安装openpyxl或xlrd库
            # pip install openpyxl xlrd
            
            # import openpyxl
            # workbook = openpyxl.load_workbook(file_path)
            # text_content = []
            # for sheet_name in workbook.sheetnames:
            #     sheet = workbook[sheet_name]
            #     text_content.append(f"=== {sheet_name} ===")
            #     for row in sheet.iter_rows(values_only=True):
            #         row_text = '\t'.join([str(cell) if cell is not None else '' for cell in row])
            #         if row_text.strip():
            #             text_content.append(row_text)
            # return '\n'.join(text_content)
            
            logger.info("Excel文档解析功能待实现（需要安装openpyxl）")
            return "[Excel文档解析功能待实现]"
            
        except Exception as e:
            logger.error(f"Excel文档处理失败: {e}")
            return None

# 全局多媒体处理器实例
media_processor = MediaProcessor()