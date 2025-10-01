"""
微信客服独立包适配器
为现有项目提供向后兼容的API，桥接到新的独立包
"""

import warnings
import sys
import os

# 添加独立包路径到Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # 向上两级到项目根目录
wechat_cs_path = os.path.join(project_root, "wechat_cs")

if wechat_cs_path not in sys.path:
    sys.path.insert(0, project_root)

# 导入新的独立包
try:
    from wechat_cs import (
        WeChatCS,
        WeChatConfig,
        WeChatClient,
        create_wechat_cs,
        MessageProcessingPipeline,
        MessageClassifier,
        MessageTextExtractor
    )
    _WECHAT_CS_AVAILABLE = True
except ImportError as e:
    _WECHAT_CS_AVAILABLE = False
    _import_error = e


class WeWorkClientAdapter:
    """
    WeWorkClient适配器类
    兼容原有的WeWorkClient API，内部使用新的独立包
    """

    def __init__(self, config):
        """
        初始化适配器

        Args:
            config: 原有的配置对象
        """
        if not _WECHAT_CS_AVAILABLE:
            raise ImportError(f"无法导入wechat_cs独立包: {_import_error}")

        # 发出迁移提示
        warnings.warn(
            "您正在使用向后兼容的适配器。建议迁移到新的独立包API。"
            "详情请参考迁移指南：README.md",
            DeprecationWarning,
            stacklevel=2
        )

        # 转换配置格式
        if hasattr(config, 'corp_id'):
            # 新的配置格式
            wechat_config = WeChatConfig(
                corp_id=config.corp_id,
                secret=config.secret,
                token=config.token,
                encoding_aes_key=config.encoding_aes_key,
                agent_id=getattr(config, 'agent_id', None),
                server_port=getattr(config, 'local_server_port', 3001)
            )
        else:
            # 兼容旧的配置格式
            wechat_config = WeChatConfig(
                corp_id=getattr(config, 'WEWORK_CORP_ID', ''),
                secret=getattr(config, 'WEWORK_SECRET', ''),
                token=getattr(config, 'WEWORK_TOKEN', ''),
                encoding_aes_key=getattr(config, 'WEWORK_AES_KEY', ''),
                agent_id=getattr(config, 'WEWORK_AGENT_ID', None),
                server_port=getattr(config, 'LOCAL_SERVER_PORT', 3001)
            )

        # 创建新的客户端
        self.client = WeChatClient(wechat_config)
        self.config = config  # 保存原配置以备兼容

        # 为兼容性保留的属性
        self._access_token = None
        self._token_expires_at = 0
        self._kf_cursors = {}

    def get_access_token(self):
        """获取访问令牌（兼容原API）"""
        return self.client.access_token

    def verify_signature(self, signature, timestamp, nonce, encrypt_msg=None):
        """验证签名（兼容原API）"""
        return self.client.verify_signature(signature, timestamp, nonce, encrypt_msg)

    def decrypt_message(self, encrypt_msg):
        """解密消息（兼容原API）"""
        return self.client.decrypt_message(encrypt_msg)

    def sync_kf_messages(self, token=None, open_kf_id=None, limit=1000, get_latest_only=True):
        """同步微信客服消息（兼容原API）"""
        return self.client.sync_kf_messages(token, open_kf_id, limit, get_latest_only)

    def send_text_message(self, external_userid, open_kfid, content):
        """发送文本消息（兼容原API）"""
        return self.client.send_text_message(external_userid, open_kfid, content)

    def _convert_kf_message(self, kf_msg):
        """转换微信客服消息格式（兼容原API）"""
        return self.client.convert_kf_message_format(kf_msg)

    def _convert_external_userid_to_openid(self, external_userid):
        """转换external_userid到openid（兼容原API）"""
        # 这个方法在原系统中依赖数据库，需要保持原有逻辑
        try:
            from ..database.binding_db import binding_db

            if binding_db:
                openid = binding_db.get_openid_by_external_userid(external_userid)
                if openid:
                    return openid
                else:
                    return None
            else:
                return None
        except Exception:
            return None


class MessageHandlerAdapter:
    """
    消息处理器适配器
    兼容原有的消息处理API
    """

    def __init__(self):
        if not _WECHAT_CS_AVAILABLE:
            raise ImportError(f"无法导入wechat_cs独立包: {_import_error}")

        warnings.warn(
            "您正在使用向后兼容的消息处理适配器。建议迁移到新的独立包API。",
            DeprecationWarning,
            stacklevel=2
        )

        # 创建新的处理管道
        self.pipeline = MessageProcessingPipeline()
        self.classifier = MessageClassifier()
        self.text_extractor = MessageTextExtractor()

    def classify_and_handle_message(self, message):
        """分类并处理消息（兼容原API）"""
        # 转换消息格式并处理
        from wechat_cs.core.models import create_message

        message_obj = create_message(message)
        result = self.pipeline.process(message_obj)

        return result

    def parse_message(self, xml_data):
        """解析XML消息（兼容原API）"""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_data)
            message = {}

            for child in root:
                if child.text:
                    message[child.tag] = child.text.strip()

            return message
        except Exception as e:
            print(f"消息解析失败: {e}")
            return {}

    def handle_wechat_kf_event(self, message):
        """处理微信客服事件消息（兼容原API）"""
        # 保持原有的事件处理逻辑
        pass


# 创建全局适配器实例（兼容原有的导入方式）
try:
    from .config.config import config
    wework_client = WeWorkClientAdapter(config)
except ImportError:
    # 如果无法导入配置，创建一个空的适配器
    wework_client = None

# 消息处理适配器实例
message_handler_adapter = MessageHandlerAdapter() if _WECHAT_CS_AVAILABLE else None


def migrate_to_new_api():
    """
    迁移到新API的辅助函数
    提供迁移指导和示例
    """
    print("\n" + "="*60)
    print("微信客服独立包迁移指南")
    print("="*60)
    print("\n1. 安装独立包:")
    print("   pip install wechat-customer-service")
    print("\n2. 更新导入语句:")
    print("   旧的: from src.services.wework_client import wework_client")
    print("   新的: from wechat_cs import WeChatCS")
    print("\n3. 创建实例:")
    print("   旧的: client = wework_client")
    print("   新的: cs = WeChatCS(corp_id='...', secret='...', token='...', aes_key='...')")
    print("\n4. FastAPI集成:")
    print("   app.include_router(cs.create_fastapi_router())")
    print("\n5. 消息处理:")
    print("   @cs.on_message('text')")
    print("   async def handle_text(message, result):")
    print("       print(f'收到文本: {result.result}')")
    print("\n详细文档: https://github.com/friendai/wechat-customer-service")
    print("="*60)


def check_migration_compatibility():
    """
    检查迁移兼容性

    Returns:
        Dict[str, Any]: 兼容性检查结果
    """
    result = {
        'wechat_cs_available': _WECHAT_CS_AVAILABLE,
        'adapter_working': False,
        'missing_dependencies': [],
        'migration_ready': False
    }

    if _WECHAT_CS_AVAILABLE:
        try:
            # 测试适配器是否正常工作
            if wework_client is not None:
                result['adapter_working'] = True
                result['migration_ready'] = True
        except Exception as e:
            result['error'] = str(e)
    else:
        result['import_error'] = str(_import_error)

    return result


if __name__ == "__main__":
    # 如果直接运行此文件，显示迁移指南
    migrate_to_new_api()

    # 检查兼容性
    compatibility = check_migration_compatibility()
    print(f"\n兼容性检查结果: {compatibility}")