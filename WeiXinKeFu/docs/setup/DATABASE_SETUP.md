# 数据库配置说明

## 🚀 快速开始（无需PostgreSQL）

如果你不想安装PostgreSQL，系统会**自动使用SQLite数据库**，无需任何配置！

```bash
# 直接运行即可
python run.py
```

## 📊 PostgreSQL配置（可选）

如果你想使用更强大的PostgreSQL数据库，请按以下步骤操作：

### 1. 安装PostgreSQL

- Windows: 下载 [PostgreSQL安装程序](https://www.postgresql.org/download/windows/)
- Mac: `brew install postgresql`
- Linux: `sudo apt-get install postgresql`

### 2. 创建数据库

```bash
# 登录PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE user_profiles_db;

# 创建用户（可选）
CREATE USER myuser WITH PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE user_profiles_db TO myuser;

# 退出
\q
```

### 3. 配置环境变量

在 `.env` 文件中添加：

```bash
DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/user_profiles_db
```

或者使用默认配置：
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/user_profiles_db
```

### 4. 安装Python依赖

```bash
pip install psycopg2-binary
```

## ✨ 自动功能

- **自动选择数据库**：如果PostgreSQL不可用，自动切换到SQLite
- **自动创建表结构**：首次运行时自动创建所需的数据表
- **无缝切换**：两种数据库使用相同的接口，代码无需修改

## 🔍 查看数据

### PostgreSQL版本：
```bash
python db_viewer_pg.py
```

### SQLite版本：
```bash
# 数据存储在 user_profiles.db 文件中
# 可以使用任何SQLite工具查看
```

## ❓ 常见问题

**Q: 必须使用PostgreSQL吗？**
A: 不需要！SQLite完全够用，PostgreSQL只是提供更多高级功能。

**Q: 如何知道正在使用哪个数据库？**
A: 启动时会显示：
- `✅ 使用PostgreSQL数据库` 
- `✅ 使用SQLite数据库（备用方案）`

**Q: 可以从SQLite迁移到PostgreSQL吗？**
A: 可以，但需要手动导出导入数据。

**Q: PostgreSQL连接失败怎么办？**
A: 系统会自动切换到SQLite，不影响使用。