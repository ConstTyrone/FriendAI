#!/bin/bash
# 从远程服务器完全同步代码和数据库

# 配置
REMOTE_SERVER="root@product-mcp-server"  # 修改为你的服务器地址
REMOTE_PATH="/path/to/FriendAI"          # 修改为服务器上的项目路径
LOCAL_PATH="/Users/wzy668/Projects/FriendAI"

echo "🔄 开始从远程服务器同步..."
echo "================================================"

# 1. 备份本地当前状态
echo "📦 备份本地当前状态..."
cd $LOCAL_PATH
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p ../$BACKUP_DIR

# 备份数据库
if [ -f "WeiXinKeFu/user_profiles.db" ]; then
    cp WeiXinKeFu/user_profiles.db ../$BACKUP_DIR/
    echo "  ✅ 数据库已备份到 ../$BACKUP_DIR/"
fi

# 保存本地git状态
git stash push -m "Backup before sync $(date +%Y%m%d_%H%M%S)"
echo "  ✅ Git更改已暂存"

# 2. 从GitHub拉取最新代码
echo ""
echo "📥 从GitHub拉取最新代码..."
git fetch origin main
git reset --hard origin/main
echo "  ✅ 代码已更新到最新版本"

# 3. 从服务器同步数据库
echo ""
echo "💾 从服务器同步数据库..."
scp $REMOTE_SERVER:$REMOTE_PATH/WeiXinKeFu/user_profiles.db WeiXinKeFu/user_profiles.db
if [ $? -eq 0 ]; then
    echo "  ✅ 数据库同步成功"
else
    echo "  ❌ 数据库同步失败"
fi

# 4. 同步.env配置文件
echo ""
echo "⚙️ 从服务器同步配置文件..."
scp $REMOTE_SERVER:$REMOTE_PATH/WeiXinKeFu/.env WeiXinKeFu/.env
if [ $? -eq 0 ]; then
    echo "  ✅ 配置文件同步成功"
else
    echo "  ⚠️ 配置文件同步失败（可能不存在）"
fi

# 5. 同步日志文件（可选）
echo ""
read -p "是否同步日志文件？(y/n): " sync_logs
if [ "$sync_logs" = "y" ]; then
    echo "📝 同步日志文件..."
    rsync -avz $REMOTE_SERVER:$REMOTE_PATH/WeiXinKeFu/logs/ WeiXinKeFu/logs/
    echo "  ✅ 日志文件同步完成"
fi

# 6. 显示同步结果
echo ""
echo "================================================"
echo "✨ 同步完成！"
echo ""
echo "📊 当前状态："
echo "  - Git版本："
git log --oneline -3
echo ""
echo "  - 数据库信息："
if [ -f "WeiXinKeFu/user_profiles.db" ]; then
    echo "    文件大小: $(ls -lh WeiXinKeFu/user_profiles.db | awk '{print $5}')"
    echo "    修改时间: $(ls -l WeiXinKeFu/user_profiles.db | awk '{print $6, $7, $8}')"
fi

echo ""
echo "💡 提示："
echo "  - 本地备份保存在: ../$BACKUP_DIR/"
echo "  - 如需恢复备份: cp ../$BACKUP_DIR/user_profiles.db WeiXinKeFu/"
echo "  - 查看暂存的更改: git stash list"
echo "  - 恢复暂存的更改: git stash pop"