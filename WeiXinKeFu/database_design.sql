-- PostgreSQL 用户画像存储系统数据库设计
-- 版本: 1.0
-- 说明: 以用户为单位存储他们收集的用户画像数据

-- 创建数据库
-- CREATE DATABASE user_profiles_db;

-- 1. 用户表 (记录使用客服系统的用户)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    wechat_user_id VARCHAR(255) UNIQUE NOT NULL, -- 微信用户ID (如: wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q)
    nickname VARCHAR(100), -- 用户昵称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}' -- 存储额外的用户信息
);

-- 2. 用户画像表 (存储每个用户收集的用户画像)
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- 所属用户
    profile_name VARCHAR(100) NOT NULL, -- 画像人物姓名
    gender VARCHAR(10), -- 性别
    age VARCHAR(50), -- 年龄
    phone VARCHAR(50), -- 电话
    location VARCHAR(100), -- 所在地
    marital_status VARCHAR(50), -- 婚育状况
    education VARCHAR(200), -- 学历（学校）
    company VARCHAR(200), -- 公司（行业）
    position VARCHAR(100), -- 职位
    asset_level VARCHAR(20), -- 资产水平
    personality TEXT, -- 性格描述
    
    -- AI分析元数据
    ai_summary TEXT, -- AI总结
    confidence_score DECIMAL(3,2), -- 置信度分数 (0.00-1.00)
    source_type VARCHAR(50), -- 来源类型 (text/voice/image/file/chat_record)
    
    -- 原始数据
    raw_message_content TEXT, -- 原始消息内容
    raw_ai_response JSONB, -- AI原始响应
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引优化
    CONSTRAINT unique_user_profile UNIQUE (user_id, profile_name)
);

-- 3. 消息记录表 (记录每次消息处理)
CREATE TABLE IF NOT EXISTS message_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id VARCHAR(100), -- 微信消息ID
    message_type VARCHAR(50), -- 消息类型
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    processing_time_ms INTEGER, -- 处理耗时（毫秒）
    
    -- 关联的用户画像
    profile_id INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL
);

-- 4. 画像标签表 (为用户画像添加标签，便于分类和搜索)
CREATE TABLE IF NOT EXISTS profile_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 画像标签关联表
CREATE TABLE IF NOT EXISTS profile_tag_mappings (
    profile_id INTEGER NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES profile_tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (profile_id, tag_id)
);

-- 6. 用户配额表 (限制每个用户的使用量)
CREATE TABLE IF NOT EXISTS user_quotas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    max_profiles INTEGER DEFAULT 1000, -- 最大画像数量
    used_profiles INTEGER DEFAULT 0, -- 已使用画像数量
    max_daily_messages INTEGER DEFAULT 100, -- 每日最大消息数
    reset_at DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以优化查询性能
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_name ON user_profiles(profile_name);
CREATE INDEX idx_user_profiles_created_at ON user_profiles(created_at DESC);
CREATE INDEX idx_message_logs_user_id ON message_logs(user_id);
CREATE INDEX idx_message_logs_processed_at ON message_logs(processed_at DESC);

-- 创建全文搜索索引
CREATE INDEX idx_user_profiles_fulltext ON user_profiles 
USING gin(to_tsvector('chinese', 
    COALESCE(profile_name, '') || ' ' || 
    COALESCE(company, '') || ' ' || 
    COALESCE(position, '') || ' ' || 
    COALESCE(personality, '')
));

-- 创建触发器：自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_quotas_updated_at BEFORE UPDATE ON user_quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建视图：用户画像统计
CREATE VIEW user_profile_stats AS
SELECT 
    u.id as user_id,
    u.wechat_user_id,
    u.nickname,
    COUNT(DISTINCT up.id) as total_profiles,
    COUNT(DISTINCT up.profile_name) as unique_names,
    COUNT(DISTINCT CASE WHEN up.created_at >= CURRENT_DATE THEN up.id END) as today_profiles,
    MAX(up.created_at) as last_profile_at
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
GROUP BY u.id, u.wechat_user_id, u.nickname;

-- 创建视图：每日使用统计
CREATE VIEW daily_usage_stats AS
SELECT 
    DATE(ml.processed_at) as date,
    u.wechat_user_id,
    COUNT(*) as message_count,
    COUNT(DISTINCT ml.profile_id) as profile_count,
    AVG(ml.processing_time_ms) as avg_processing_time_ms
FROM message_logs ml
JOIN users u ON ml.user_id = u.id
WHERE ml.success = TRUE
GROUP BY DATE(ml.processed_at), u.wechat_user_id;

-- 示例查询

-- 1. 获取某用户的所有画像
-- SELECT * FROM user_profiles 
-- WHERE user_id = (SELECT id FROM users WHERE wechat_user_id = 'xxx')
-- ORDER BY created_at DESC;

-- 2. 搜索用户画像
-- SELECT * FROM user_profiles 
-- WHERE user_id = ? 
-- AND to_tsvector('chinese', profile_name || ' ' || company || ' ' || position) @@ to_tsquery('chinese', '软件工程师');

-- 3. 获取用户统计信息
-- SELECT * FROM user_profile_stats WHERE wechat_user_id = 'xxx';

-- 4. 检查用户配额
-- SELECT * FROM user_quotas WHERE user_id = ?;