/**
 * 主应用逻辑
 */
class App {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 12;
        this.currentProfiles = [];
        this.autoRefreshInterval = null;
        this.selectedProfileId = null;
        
        this.init();
    }

    /**
     * 初始化应用
     */
    init() {
        // 监听API日志事件
        window.addEventListener('apiLog', (event) => {
            this.addLogEntry(event.detail);
        });

        // 检查是否已登录
        if (apiClient.isLoggedIn()) {
            this.updateLoginStatus(true);
            this.loadUserStats();
            this.loadProfiles();
        }

        // 绑定搜索框回车事件
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // 初始化时测试连接
        this.testConnection();
    }

    /**
     * 测试服务器连接
     */
    async testConnection() {
        const serverUrlInput = document.getElementById('serverUrl');
        const serverUrl = serverUrlInput.value.trim();
        
        if (serverUrl !== apiClient.baseURL) {
            apiClient.baseURL = serverUrl;
        }

        this.showLoading('正在测试连接...');
        const result = await apiClient.testConnection();
        this.hideLoading();

        const statusElement = document.getElementById('serverStatus');
        if (result.success) {
            statusElement.innerHTML = '<i class="fas fa-circle"></i> 在线';
            statusElement.className = 'status-online';
            this.showAlert('服务器连接成功！', 'success');
        } else {
            statusElement.innerHTML = '<i class="fas fa-circle"></i> 离线';
            statusElement.className = 'status-offline';
            this.showAlert(`服务器连接失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 用户登录
     */
    async login() {
        const wechatUserId = document.getElementById('wechatUserId').value.trim();
        
        if (!wechatUserId) {
            this.showAlert('请输入微信用户ID', 'warning');
            return;
        }

        this.showLoading('正在登录...');
        const result = await apiClient.login(wechatUserId);
        this.hideLoading();

        const loginResult = document.getElementById('loginResult');
        
        if (result.success) {
            loginResult.innerHTML = `
                <div class="alert alert-success alert-sm mt-2">
                    <i class="fas fa-check-circle me-2"></i>登录成功！
                </div>
            `;
            
            this.updateLoginStatus(true);
            this.loadUserStats();
            this.loadProfiles();
            
        } else {
            loginResult.innerHTML = `
                <div class="alert alert-danger alert-sm mt-2">
                    <i class="fas fa-exclamation-circle me-2"></i>登录失败: ${result.error}
                </div>
            `;
        }
    }

    /**
     * 更新登录状态显示
     */
    updateLoginStatus(isLoggedIn) {
        const userInfo = document.getElementById('userInfo');
        const currentUser = document.getElementById('currentUser');
        const searchCard = document.getElementById('searchCard');
        
        if (isLoggedIn) {
            userInfo.style.display = 'block';
            currentUser.textContent = apiClient.getCurrentUserId();
            searchCard.style.display = 'block';
        } else {
            userInfo.style.display = 'none';
            searchCard.style.display = 'none';
        }
    }

    /**
     * 加载用户统计信息
     */
    async loadUserStats() {
        const result = await apiClient.getStats();
        
        if (result.success) {
            const stats = result.data;
            
            document.getElementById('totalProfiles').textContent = stats.total_profiles || 0;
            document.getElementById('uniqueNames').textContent = stats.unique_names || 0;
            document.getElementById('todayProfiles').textContent = stats.today_profiles || 0;
            
            const usagePercent = stats.max_profiles ? 
                Math.round((stats.used_profiles / stats.max_profiles) * 100) : 0;
            document.getElementById('usagePercent').textContent = `${usagePercent}%`;
            
            document.getElementById('statsCards').style.display = 'block';
        }
    }

    /**
     * 加载用户画像列表
     */
    async loadProfiles(page = 1, search = '') {
        this.showLoading('正在加载画像列表...');
        
        const result = await apiClient.getProfiles(page, this.pageSize, search);
        this.hideLoading();

        if (result.success) {
            this.currentProfiles = result.data.profiles;
            this.renderProfiles(result.data.profiles);
            this.renderPagination(result.data);
            
            document.getElementById('profileCount').textContent = result.data.total;
        } else {
            this.showAlert(`加载失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 渲染画像列表
     */
    renderProfiles(profiles) {
        const container = document.getElementById('profilesList');
        
        if (!profiles || profiles.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center text-muted py-5">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>暂无用户画像数据</p>
                </div>
            `;
            return;
        }

        const profilesHTML = profiles.map(profile => `
            <div class="col-md-4 mb-3">
                <div class="card profile-card h-100" onclick="app.showProfileDetail(${profile.id})">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-title mb-0">
                                <i class="fas fa-user me-2"></i>${profile.profile_name || '未知'}
                            </h6>
                            <span class="badge bg-${this.getSourceTypeBadge(profile.source_type)}">
                                ${profile.source_type || '未知'}
                            </span>
                        </div>
                        
                        <div class="mb-2">
                            ${profile.gender ? `<small class="me-2"><i class="fas fa-venus-mars me-1"></i>${profile.gender}</small>` : ''}
                            ${profile.age ? `<small class="me-2"><i class="fas fa-birthday-cake me-1"></i>${profile.age}</small>` : ''}
                        </div>
                        
                        ${profile.company ? `<p class="card-text text-muted mb-1"><i class="fas fa-building me-1"></i>${profile.company}</p>` : ''}
                        ${profile.position ? `<p class="card-text text-muted mb-1"><i class="fas fa-briefcase me-1"></i>${profile.position}</p>` : ''}
                        ${profile.location ? `<p class="card-text text-muted mb-2"><i class="fas fa-map-marker-alt me-1"></i>${profile.location}</p>` : ''}
                        
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                ${profile.confidence_score ? `置信度: ${Math.round(profile.confidence_score * 100)}%` : ''}
                            </small>
                            <small class="text-muted">
                                ${profile.created_at ? new Date(profile.created_at).toLocaleDateString() : ''}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = profilesHTML;
    }

    /**
     * 获取消息类型对应的徽章颜色
     */
    getSourceTypeBadge(sourceType) {
        const badgeMap = {
            'text': 'primary',
            'voice': 'success',
            'image': 'info',
            'file': 'warning',
            'chat_record': 'secondary',
            'video': 'dark'
        };
        return badgeMap[sourceType] || 'light';
    }

    /**
     * 渲染分页
     */
    renderPagination(data) {
        const pagination = document.getElementById('pagination');
        const paginationUl = pagination.querySelector('ul');
        
        if (data.total_pages <= 1) {
            pagination.style.display = 'none';
            return;
        }
        
        pagination.style.display = 'block';
        
        let paginationHTML = '';
        
        // 上一页
        paginationHTML += `
            <li class="page-item ${data.page <= 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.changePage(${data.page - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
        
        // 页码
        const startPage = Math.max(1, data.page - 2);
        const endPage = Math.min(data.total_pages, data.page + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === data.page ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="app.changePage(${i})">${i}</a>
                </li>
            `;
        }
        
        // 下一页
        paginationHTML += `
            <li class="page-item ${data.page >= data.total_pages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.changePage(${data.page + 1})">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
        
        paginationUl.innerHTML = paginationHTML;
    }

    /**
     * 切换页面
     */
    changePage(page) {
        this.currentPage = page;
        const search = document.getElementById('searchInput').value.trim();
        this.loadProfiles(page, search);
    }

    /**
     * 执行搜索
     */
    performSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();
        
        this.currentPage = 1;
        this.loadProfiles(1, query);
    }

    /**
     * 显示画像详情
     */
    async showProfileDetail(profileId) {
        this.selectedProfileId = profileId;
        this.showLoading('正在加载详情...');
        
        const result = await apiClient.getProfileDetail(profileId);
        this.hideLoading();

        if (result.success) {
            const profile = result.data.profile;
            this.renderProfileDetail(profile);
            
            const modal = new bootstrap.Modal(document.getElementById('profileModal'));
            modal.show();
        } else {
            this.showAlert(`加载详情失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 渲染画像详情
     */
    renderProfileDetail(profile) {
        const detailContainer = document.getElementById('profileDetail');
        
        const fields = [
            { key: 'profile_name', label: '姓名', icon: 'user' },
            { key: 'gender', label: '性别', icon: 'venus-mars' },
            { key: 'age', label: '年龄', icon: 'birthday-cake' },
            { key: 'phone', label: '电话', icon: 'phone' },
            { key: 'location', label: '所在地', icon: 'map-marker-alt' },
            { key: 'marital_status', label: '婚育状况', icon: 'heart' },
            { key: 'education', label: '学历', icon: 'graduation-cap' },
            { key: 'company', label: '公司', icon: 'building' },
            { key: 'position', label: '职位', icon: 'briefcase' },
            { key: 'asset_level', label: '资产水平', icon: 'coins' },
            { key: 'personality', label: '性格', icon: 'smile' }
        ];

        let detailHTML = `
            <div class="row">
                <div class="col-md-8">
                    <h5 class="mb-3">基本信息</h5>
                    <div class="row">
        `;

        fields.forEach(field => {
            const value = profile[field.key];
            if (value && value !== '未知') {
                detailHTML += `
                    <div class="col-md-6 mb-2">
                        <strong><i class="fas fa-${field.icon} me-2"></i>${field.label}:</strong>
                        <span class="ms-2">${value}</span>
                    </div>
                `;
            }
        });

        detailHTML += `
                    </div>
                </div>
                <div class="col-md-4">
                    <h6>AI分析信息</h6>
                    <div class="card">
                        <div class="card-body">
                            <p><strong>消息类型:</strong> ${profile.source_type || '未知'}</p>
                            <p><strong>置信度:</strong> ${profile.confidence_score ? Math.round(profile.confidence_score * 100) + '%' : '未知'}</p>
                            <p><strong>创建时间:</strong> ${profile.created_at ? new Date(profile.created_at).toLocaleString() : '未知'}</p>
                            <p><strong>更新时间:</strong> ${profile.updated_at ? new Date(profile.updated_at).toLocaleString() : '未知'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (profile.ai_summary) {
            detailHTML += `
                <div class="mt-3">
                    <h6>AI总结</h6>
                    <div class="alert alert-info">
                        ${profile.ai_summary}
                    </div>
                </div>
            `;
        }

        if (profile.raw_message_content) {
            detailHTML += `
                <div class="mt-3">
                    <h6>原始消息内容</h6>
                    <div class="card">
                        <div class="card-body">
                            <pre class="mb-0">${profile.raw_message_content.substring(0, 500)}${profile.raw_message_content.length > 500 ? '...' : ''}</pre>
                        </div>
                    </div>
                </div>
            `;
        }

        detailContainer.innerHTML = detailHTML;

        // 绑定删除按钮事件
        document.getElementById('deleteProfileBtn').onclick = () => this.deleteProfile();
    }

    /**
     * 删除画像
     */
    async deleteProfile() {
        if (!this.selectedProfileId) return;

        if (!confirm('确定要删除这个用户画像吗？此操作不可恢复。')) {
            return;
        }

        this.showLoading('正在删除...');
        const result = await apiClient.deleteProfile(this.selectedProfileId);
        this.hideLoading();

        if (result.success) {
            this.showAlert('画像删除成功！', 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('profileModal'));
            modal.hide();
            
            // 刷新列表
            this.loadProfiles(this.currentPage);
            this.loadUserStats();
        } else {
            this.showAlert(`删除失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 获取统计信息
     */
    async getStats() {
        await this.loadUserStats();
        this.showAlert('统计信息已刷新', 'info');
    }

    /**
     * 搜索画像
     */
    async searchProfiles() {
        const query = prompt('请输入搜索关键词（姓名、公司、职位等）:');
        if (!query) return;

        document.getElementById('searchInput').value = query;
        this.performSearch();
    }

    /**
     * 获取最近画像
     */
    async getRecent() {
        this.showLoading('正在加载最近画像...');
        const result = await apiClient.getRecent(10);
        this.hideLoading();

        if (result.success) {
            this.renderProfiles(result.data.profiles);
            document.getElementById('profileCount').textContent = result.data.total;
            
            // 隐藏分页
            document.getElementById('pagination').style.display = 'none';
            
            this.showAlert(`加载了最近的 ${result.data.profiles.length} 个画像`, 'info');
        } else {
            this.showAlert(`加载失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 获取用户信息
     */
    async getUserInfo() {
        const result = await apiClient.getUserInfo();
        
        if (result.success) {
            const info = result.data;
            const infoHTML = `
                <div class="alert alert-info">
                    <h6>用户信息</h6>
                    <p><strong>微信用户ID:</strong> ${info.wechat_user_id}</p>
                    <p><strong>数据表名:</strong> ${info.table_name}</p>
                    <p><strong>总画像数:</strong> ${info.stats.total_profiles}</p>
                    <p><strong>唯一姓名数:</strong> ${info.stats.unique_names}</p>
                </div>
            `;
            
            this.showAlert(infoHTML, '', true);
        } else {
            this.showAlert(`获取用户信息失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 检查更新
     */
    async checkUpdates() {
        const result = await apiClient.checkUpdates();
        
        if (result.success) {
            const data = result.data;
            if (data.has_updates) {
                this.showAlert('发现新的画像数据！正在刷新列表...', 'success');
                setTimeout(() => {
                    this.loadProfiles();
                    this.loadUserStats();
                }, 1000);
            } else {
                this.showAlert('暂无新的画像数据', 'info');
            }
        } else {
            this.showAlert(`检查更新失败: ${result.error}`, 'danger');
        }
    }

    /**
     * 切换自动刷新
     */
    toggleAutoRefresh() {
        const checkbox = document.getElementById('autoRefresh');
        const button = document.querySelector('[onclick="toggleAutoRefresh()"]');
        const status = document.getElementById('autoRefreshStatus');

        if (this.autoRefreshInterval) {
            // 停止自动刷新
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            
            checkbox.checked = false;
            button.innerHTML = '<i class="fas fa-play me-2"></i>开始监听';
            status.textContent = '';
        } else {
            // 开始自动刷新
            this.autoRefreshInterval = setInterval(async () => {
                const result = await apiClient.checkUpdates();
                if (result.success && result.data.has_updates) {
                    this.loadProfiles();
                    this.loadUserStats();
                    status.textContent = `检测到更新 - ${new Date().toLocaleTimeString()}`;
                }
            }, 30000);
            
            checkbox.checked = true;
            button.innerHTML = '<i class="fas fa-stop me-2"></i>停止监听';
            status.textContent = '正在监听更新...';
        }
    }

    /**
     * 显示加载状态
     */
    showLoading(message = '加载中...') {
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        overlay.style.backgroundColor = 'rgba(0,0,0,0.5)';
        overlay.style.zIndex = '9999';
        overlay.innerHTML = `
            <div class="card">
                <div class="card-body text-center">
                    <div class="spinner-border text-primary mb-2" role="status"></div>
                    <div>${message}</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
    }

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * 显示提示消息
     */
    showAlert(message, type = 'info', isHTML = false) {
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '9999';
        alertContainer.style.minWidth = '300px';
        
        alertContainer.innerHTML = `
            ${isHTML ? message : `<i class="fas fa-info-circle me-2"></i>${message}`}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertContainer);
        
        // 自动消失
        setTimeout(() => {
            if (alertContainer.parentNode) {
                alertContainer.remove();
            }
        }, 5000);
    }

    /**
     * 添加API日志条目
     */
    addLogEntry(logEntry) {
        const logsContainer = document.getElementById('apiLogs');
        const logElement = document.createElement('div');
        logElement.className = 'api-response mb-2';
        
        const statusClass = logEntry.status === 'ERROR' ? 'danger' : 
                           logEntry.status >= 400 ? 'warning' : 'success';
        
        logElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <span class="badge bg-${statusClass}">${logEntry.method}</span>
                    <code class="ms-2">${logEntry.url}</code>
                </div>
                <div class="timestamp">
                    ${logEntry.timestamp} (${logEntry.duration}ms)
                </div>
            </div>
            <details>
                <summary class="text-muted">查看响应数据</summary>
                <pre class="mt-2 mb-0"><code>${JSON.stringify(logEntry.data, null, 2)}</code></pre>
            </details>
        `;
        
        logsContainer.appendChild(logElement);
        
        // 保持最新的日志在顶部
        logsContainer.scrollTop = logsContainer.scrollHeight;
        
        // 限制日志数量
        while (logsContainer.children.length > 50) {
            logsContainer.removeChild(logsContainer.firstChild);
        }
    }

    /**
     * 清空日志
     */
    clearLogs() {
        const logsContainer = document.getElementById('apiLogs');
        logsContainer.innerHTML = `
            <div class="text-muted text-center py-3">
                <i class="fas fa-code me-2"></i>API调用日志将显示在这里
            </div>
        `;
    }
}

// 全局函数，供HTML调用
function testConnection() { app.testConnection(); }
function login() { app.login(); }
function getProfiles() { app.loadProfiles(); }
function getStats() { app.getStats(); }
function searchProfiles() { app.searchProfiles(); }
function getRecent() { app.getRecent(); }
function getUserInfo() { app.getUserInfo(); }
function checkUpdates() { app.checkUpdates(); }
function toggleAutoRefresh() { app.toggleAutoRefresh(); }
function performSearch() { app.performSearch(); }
function clearLogs() { app.clearLogs(); }

// 初始化应用
window.app = new App();