-- 创建小程序用户与企业微信用户的映射表
CREATE TABLE IF NOT EXISTS wechat_user_mapping (
    id SERIAL PRIMARY KEY,
    mini_program_openid VARCHAR(255) UNIQUE NOT NULL,  -- 小程序OpenID (o开头)
    enterprise_wechat_id VARCHAR(255) NOT NULL,        -- 企业微信ID (wm开头)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (enterprise_wechat_id) REFERENCES users(wechat_user_id)
);

-- 示例：添加映射
-- INSERT INTO wechat_user_mapping (mini_program_openid, enterprise_wechat_id) 
-- VALUES ('oXXXXXXXXXXXXXXXXXXXXXXX', 'wm0gZOdQAAZMXhfFKa9kZRMNdRwEVZYQ');