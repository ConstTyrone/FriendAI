# API使用示例集合

## 🚀 完整的前端集成示例

### React.js 集成示例

```jsx
import React, { useState, useEffect, useCallback } from 'react';

// API客户端类
class UserProfileAPI {
  constructor(baseURL = 'http://localhost:3001') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('auth_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
        ...options.headers
      }
    };

    const response = await fetch(url, config);
    
    if (response.status === 401) {
      this.logout();
      throw new Error('认证失败，请重新登录');
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
  }

  async login(wechatUserId) {
    const data = await this.request('/api/login', {
      method: 'POST',
      body: JSON.stringify({ wechat_user_id: wechatUserId })
    });
    
    this.token = data.token;
    localStorage.setItem('auth_token', data.token);
    return data;
  }

  async getProfiles(page = 1, pageSize = 20, search = '') {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...(search && { search })
    });
    
    return await this.request(`/api/profiles?${params}`);
  }

  async getStats() {
    return await this.request('/api/stats');
  }

  async deleteProfile(profileId) {
    return await this.request(`/api/profiles/${profileId}`, {
      method: 'DELETE'
    });
  }

  logout() {
    this.token = null;
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
  }
}

const api = new UserProfileAPI();

// React组件示例
const ProfileDashboard = () => {
  const [profiles, setProfiles] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  // 加载画像列表
  const loadProfiles = useCallback(async (page = 1, search = '') => {
    setLoading(true);
    try {
      const data = await api.getProfiles(page, 20, search);
      setProfiles(data.profiles);
      setTotalPages(data.total_pages);
      setCurrentPage(page);
    } catch (error) {
      alert('加载失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // 加载统计信息
  const loadStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (error) {
      console.error('加载统计失败:', error);
    }
  }, []);

  // 删除画像
  const handleDelete = async (profileId) => {
    if (!window.confirm('确定要删除这个画像吗？')) return;
    
    try {
      await api.deleteProfile(profileId);
      loadProfiles(currentPage, searchQuery);
      loadStats();
      alert('删除成功');
    } catch (error) {
      alert('删除失败: ' + error.message);
    }
  };

  // 搜索处理
  const handleSearch = (e) => {
    e.preventDefault();
    loadProfiles(1, searchQuery);
  };

  // 初始化加载
  useEffect(() => {
    loadProfiles();
    loadStats();
  }, [loadProfiles, loadStats]);

  return (
    <div className="profile-dashboard">
      {/* 统计卡片 */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>{stats.total_profiles || 0}</h3>
          <p>总画像数</p>
        </div>
        <div className="stat-card">
          <h3>{stats.unique_names || 0}</h3>
          <p>唯一姓名</p>
        </div>
        <div className="stat-card">
          <h3>{stats.today_profiles || 0}</h3>
          <p>今日新增</p>
        </div>
      </div>

      {/* 搜索框 */}
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索姓名、公司、职位..."
        />
        <button type="submit">搜索</button>
      </form>

      {/* 画像列表 */}
      {loading ? (
        <div>加载中...</div>
      ) : (
        <div className="profile-grid">
          {profiles.map(profile => (
            <div key={profile.id} className="profile-card">
              <h4>{profile.profile_name}</h4>
              <p>{profile.company} - {profile.position}</p>
              <p>{profile.location}</p>
              <div className="card-actions">
                <button onClick={() => handleDelete(profile.id)}>
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 分页 */}
      <div className="pagination">
        {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
          <button
            key={page}
            className={page === currentPage ? 'active' : ''}
            onClick={() => loadProfiles(page, searchQuery)}
          >
            {page}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ProfileDashboard;
```

### Vue.js 集成示例

```vue
<template>
  <div class="profile-dashboard">
    <!-- 统计信息 -->
    <div class="stats-row">
      <div class="stat-card">
        <h3>{{ stats.total_profiles || 0 }}</h3>
        <p>总画像数</p>
      </div>
      <div class="stat-card">
        <h3>{{ stats.unique_names || 0 }}</h3>
        <p>唯一姓名</p>
      </div>
      <div class="stat-card">
        <h3>{{ stats.today_profiles || 0 }}</h3>
        <p>今日新增</p>
      </div>
    </div>

    <!-- 搜索框 -->
    <div class="search-section">
      <input
        v-model="searchQuery"
        @keyup.enter="handleSearch"
        placeholder="搜索姓名、公司、职位..."
      />
      <button @click="handleSearch">搜索</button>
    </div>

    <!-- 画像列表 -->
    <div v-if="loading" class="loading">加载中...</div>
    
    <div v-else class="profile-list">
      <div
        v-for="profile in profiles"
        :key="profile.id"
        class="profile-item"
        @click="showProfileDetail(profile)"
      >
        <h4>{{ profile.profile_name }}</h4>
        <p>{{ profile.company }} - {{ profile.position }}</p>
        <p>{{ profile.location }}</p>
        <span class="confidence">
          置信度: {{ Math.round((profile.confidence_score || 0) * 100) }}%
        </span>
        <button @click.stop="deleteProfile(profile.id)">删除</button>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <button
        v-for="page in totalPages"
        :key="page"
        :class="{ active: page === currentPage }"
        @click="loadProfiles(page)"
      >
        {{ page }}
      </button>
    </div>

    <!-- 画像详情弹窗 -->
    <div v-if="selectedProfile" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h3>{{ selectedProfile.profile_name }}</h3>
        <div class="profile-details">
          <p v-if="selectedProfile.gender">
            <strong>性别:</strong> {{ selectedProfile.gender }}
          </p>
          <p v-if="selectedProfile.age">
            <strong>年龄:</strong> {{ selectedProfile.age }}
          </p>
          <p v-if="selectedProfile.company">
            <strong>公司:</strong> {{ selectedProfile.company }}
          </p>
          <p v-if="selectedProfile.position">
            <strong>职位:</strong> {{ selectedProfile.position }}
          </p>
          <p v-if="selectedProfile.location">
            <strong>地址:</strong> {{ selectedProfile.location }}
          </p>
          <p v-if="selectedProfile.personality">
            <strong>性格:</strong> {{ selectedProfile.personality }}
          </p>
        </div>
        <button @click="closeModal">关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, reactive } from 'vue';

export default {
  name: 'ProfileDashboard',
  setup() {
    const profiles = ref([]);
    const stats = reactive({});
    const loading = ref(false);
    const currentPage = ref(1);
    const totalPages = ref(1);
    const searchQuery = ref('');
    const selectedProfile = ref(null);

    // API客户端
    const api = {
      async request(endpoint, options = {}) {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`http://localhost:3001${endpoint}`, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...options.headers
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
      },

      async getProfiles(page = 1, pageSize = 20, search = '') {
        const params = new URLSearchParams({
          page: page.toString(),
          page_size: pageSize.toString(),
          ...(search && { search })
        });
        
        return await this.request(`/api/profiles?${params}`);
      },

      async getStats() {
        return await this.request('/api/stats');
      },

      async deleteProfile(profileId) {
        return await this.request(`/api/profiles/${profileId}`, {
          method: 'DELETE'
        });
      }
    };

    // 加载画像列表
    const loadProfiles = async (page = 1, search = '') => {
      loading.value = true;
      try {
        const data = await api.getProfiles(page, 20, search);
        profiles.value = data.profiles;
        totalPages.value = data.total_pages;
        currentPage.value = page;
      } catch (error) {
        alert('加载失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    // 加载统计信息
    const loadStats = async () => {
      try {
        const data = await api.getStats();
        Object.assign(stats, data);
      } catch (error) {
        console.error('加载统计失败:', error);
      }
    };

    // 搜索处理
    const handleSearch = () => {
      loadProfiles(1, searchQuery.value);
    };

    // 删除画像
    const deleteProfile = async (profileId) => {
      if (!confirm('确定要删除这个画像吗？')) return;
      
      try {
        await api.deleteProfile(profileId);
        loadProfiles(currentPage.value, searchQuery.value);
        loadStats();
        alert('删除成功');
      } catch (error) {
        alert('删除失败: ' + error.message);
      }
    };

    // 显示画像详情
    const showProfileDetail = (profile) => {
      selectedProfile.value = profile;
    };

    // 关闭弹窗
    const closeModal = () => {
      selectedProfile.value = null;
    };

    // 初始化
    onMounted(() => {
      loadProfiles();
      loadStats();
    });

    return {
      profiles,
      stats,
      loading,
      currentPage,
      totalPages,
      searchQuery,
      selectedProfile,
      loadProfiles,
      handleSearch,
      deleteProfile,
      showProfileDetail,
      closeModal
    };
  }
};
</script>
```

### 原生JavaScript完整示例

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户画像管理系统</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-card h3 { font-size: 2em; color: #007bff; margin-bottom: 10px; }
        .search-section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .search-section input { width: 70%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .search-section button { width: 25%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; margin-left: 10px; cursor: pointer; }
        .profile-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .profile-card { background: white; padding: 20px; border-radius: 8px; cursor: pointer; transition: transform 0.2s; }
        .profile-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .profile-card h4 { color: #333; margin-bottom: 10px; }
        .profile-card p { color: #666; margin-bottom: 5px; }
        .profile-card .meta { font-size: 0.9em; color: #999; margin-top: 10px; }
        .pagination { display: flex; justify-content: center; margin-top: 30px; gap: 10px; }
        .pagination button { padding: 10px 15px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px; }
        .pagination button.active { background: #007bff; color: white; }
        .loading { text-align: center; padding: 50px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal-content { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 8px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .modal-content h3 { margin-bottom: 20px; color: #333; }
        .detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .detail-item { padding: 10px; background: #f8f9fa; border-radius: 4px; }
        .detail-item strong { color: #007bff; }
        .close-btn { position: absolute; top: 10px; right: 15px; background: none; border: none; font-size: 24px; cursor: pointer; }
        .delete-btn { background: #dc3545; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>用户画像管理系统</h1>
            <p>当前用户: <span id="currentUser">未登录</span></p>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3 id="totalProfiles">0</h3>
                <p>总画像数</p>
            </div>
            <div class="stat-card">
                <h3 id="uniqueNames">0</h3>
                <p>唯一姓名</p>
            </div>
            <div class="stat-card">
                <h3 id="todayProfiles">0</h3>
                <p>今日新增</p>
            </div>
            <div class="stat-card">
                <h3 id="usagePercent">0%</h3>
                <p>使用率</p>
            </div>
        </div>

        <!-- 搜索区域 -->
        <div class="search-section">
            <input type="text" id="searchInput" placeholder="搜索姓名、公司、职位...">
            <button onclick="handleSearch()">搜索</button>
            <button onclick="loadProfiles()" style="margin-left: 10px;">刷新</button>
        </div>

        <!-- 画像列表 -->
        <div id="profileGrid" class="profile-grid">
            <div class="loading">加载中...</div>
        </div>

        <!-- 分页 -->
        <div id="pagination" class="pagination"></div>
    </div>

    <!-- 详情弹窗 -->
    <div id="profileModal" class="modal">
        <div class="modal-content">
            <button class="close-btn" onclick="closeModal()">&times;</button>
            <h3 id="modalTitle">画像详情</h3>
            <div id="modalBody"></div>
            <button class="delete-btn" onclick="deleteCurrentProfile()">删除画像</button>
        </div>
    </div>

    <script>
        // API客户端
        class ProfileAPI {
            constructor() {
                this.baseURL = 'http://localhost:3001';
                this.token = localStorage.getItem('auth_token');
            }

            async request(endpoint, options = {}) {
                const url = `${this.baseURL}${endpoint}`;
                const config = {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
                        ...options.headers
                    }
                };

                try {
                    const response = await fetch(url, config);
                    
                    if (response.status === 401) {
                        this.logout();
                        throw new Error('认证失败，请重新登录');
                    }
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    
                    return await response.json();
                } catch (error) {
                    console.error('API请求失败:', error);
                    throw error;
                }
            }

            async login(wechatUserId) {
                const data = await this.request('/api/login', {
                    method: 'POST',
                    body: JSON.stringify({ wechat_user_id: wechatUserId })
                });
                
                this.token = data.token;
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('wechat_user_id', data.wechat_user_id);
                return data;
            }

            async getProfiles(page = 1, pageSize = 12, search = '') {
                const params = new URLSearchParams({
                    page: page.toString(),
                    page_size: pageSize.toString(),
                    ...(search && { search })
                });
                
                return await this.request(`/api/profiles?${params}`);
            }

            async getProfileDetail(profileId) {
                const data = await this.request(`/api/profiles/${profileId}`);
                return data.profile;
            }

            async deleteProfile(profileId) {
                return await this.request(`/api/profiles/${profileId}`, {
                    method: 'DELETE'
                });
            }

            async getStats() {
                return await this.request('/api/stats');
            }

            logout() {
                this.token = null;
                localStorage.removeItem('auth_token');
                localStorage.removeItem('wechat_user_id');
                alert('登录已过期，请重新登录');
            }
        }

        // 全局变量
        const api = new ProfileAPI();
        let currentPage = 1;
        let totalPages = 1;
        let currentSearch = '';
        let selectedProfileId = null;

        // 初始化
        async function init() {
            // 检查登录状态
            const wechatUserId = localStorage.getItem('wechat_user_id');
            if (!wechatUserId) {
                const userId = prompt('请输入微信用户ID:');
                if (userId) {
                    try {
                        await api.login(userId);
                        document.getElementById('currentUser').textContent = userId;
                    } catch (error) {
                        alert('登录失败: ' + error.message);
                        return;
                    }
                } else {
                    return;
                }
            } else {
                document.getElementById('currentUser').textContent = wechatUserId;
            }

            // 加载数据
            await loadStats();
            await loadProfiles();

            // 绑定搜索框回车事件
            document.getElementById('searchInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handleSearch();
                }
            });
        }

        // 加载统计信息
        async function loadStats() {
            try {
                const stats = await api.getStats();
                document.getElementById('totalProfiles').textContent = stats.total_profiles || 0;
                document.getElementById('uniqueNames').textContent = stats.unique_names || 0;
                document.getElementById('todayProfiles').textContent = stats.today_profiles || 0;
                
                const usagePercent = stats.max_profiles ? 
                    Math.round((stats.used_profiles / stats.max_profiles) * 100) : 0;
                document.getElementById('usagePercent').textContent = `${usagePercent}%`;
            } catch (error) {
                console.error('加载统计失败:', error);
            }
        }

        // 加载画像列表
        async function loadProfiles(page = 1, search = '') {
            const grid = document.getElementById('profileGrid');
            grid.innerHTML = '<div class="loading">加载中...</div>';

            try {
                const data = await api.getProfiles(page, 12, search);
                currentPage = page;
                totalPages = data.total_pages;
                currentSearch = search;

                if (data.profiles.length === 0) {
                    grid.innerHTML = '<div class="loading">暂无数据</div>';
                    return;
                }

                // 渲染画像卡片
                const cardsHTML = data.profiles.map(profile => `
                    <div class="profile-card" onclick="showProfileDetail(${profile.id})">
                        <h4>${profile.profile_name || '未知'}</h4>
                        <p><strong>性别:</strong> ${profile.gender || '未知'}</p>
                        <p><strong>年龄:</strong> ${profile.age || '未知'}</p>
                        <p><strong>公司:</strong> ${profile.company || '未知'}</p>
                        <p><strong>职位:</strong> ${profile.position || '未知'}</p>
                        <p><strong>地址:</strong> ${profile.location || '未知'}</p>
                        <div class="meta">
                            <span>置信度: ${profile.confidence_score ? Math.round(profile.confidence_score * 100) + '%' : '未知'}</span>
                            <span style="float: right;">${profile.created_at ? new Date(profile.created_at).toLocaleDateString() : ''}</span>
                        </div>
                    </div>
                `).join('');

                grid.innerHTML = cardsHTML;

                // 渲染分页
                renderPagination();

            } catch (error) {
                grid.innerHTML = `<div class="loading">加载失败: ${error.message}</div>`;
            }
        }

        // 渲染分页
        function renderPagination() {
            const pagination = document.getElementById('pagination');
            
            if (totalPages <= 1) {
                pagination.innerHTML = '';
                return;
            }

            let paginationHTML = '';
            
            // 上一页
            if (currentPage > 1) {
                paginationHTML += `<button onclick="loadProfiles(${currentPage - 1}, '${currentSearch}')">上一页</button>`;
            }

            // 页码
            const startPage = Math.max(1, currentPage - 2);
            const endPage = Math.min(totalPages, currentPage + 2);

            for (let i = startPage; i <= endPage; i++) {
                paginationHTML += `
                    <button class="${i === currentPage ? 'active' : ''}" 
                            onclick="loadProfiles(${i}, '${currentSearch}')">${i}</button>
                `;
            }

            // 下一页
            if (currentPage < totalPages) {
                paginationHTML += `<button onclick="loadProfiles(${currentPage + 1}, '${currentSearch}')">下一页</button>`;
            }

            pagination.innerHTML = paginationHTML;
        }

        // 搜索处理
        function handleSearch() {
            const searchInput = document.getElementById('searchInput');
            const query = searchInput.value.trim();
            loadProfiles(1, query);
        }

        // 显示画像详情
        async function showProfileDetail(profileId) {
            selectedProfileId = profileId;
            
            try {
                const profile = await api.getProfileDetail(profileId);
                
                document.getElementById('modalTitle').textContent = `${profile.profile_name || '未知'} - 详细信息`;
                
                const fields = [
                    { key: 'profile_name', label: '姓名' },
                    { key: 'gender', label: '性别' },
                    { key: 'age', label: '年龄' },
                    { key: 'phone', label: '电话' },
                    { key: 'location', label: '所在地' },
                    { key: 'marital_status', label: '婚育状况' },
                    { key: 'education', label: '学历' },
                    { key: 'company', label: '公司' },
                    { key: 'position', label: '职位' },
                    { key: 'asset_level', label: '资产水平' },
                    { key: 'personality', label: '性格' }
                ];

                let bodyHTML = '<div class="detail-grid">';
                
                fields.forEach(field => {
                    const value = profile[field.key];
                    if (value && value !== '未知') {
                        bodyHTML += `
                            <div class="detail-item">
                                <strong>${field.label}:</strong><br>
                                ${value}
                            </div>
                        `;
                    }
                });

                bodyHTML += '</div>';

                if (profile.ai_summary) {
                    bodyHTML += `
                        <div style="margin-top: 20px;">
                            <strong>AI总结:</strong><br>
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 4px; margin-top: 10px;">
                                ${profile.ai_summary}
                            </div>
                        </div>
                    `;
                }

                document.getElementById('modalBody').innerHTML = bodyHTML;
                document.getElementById('profileModal').style.display = 'block';

            } catch (error) {
                alert('加载详情失败: ' + error.message);
            }
        }

        // 关闭弹窗
        function closeModal() {
            document.getElementById('profileModal').style.display = 'none';
            selectedProfileId = null;
        }

        // 删除当前画像
        async function deleteCurrentProfile() {
            if (!selectedProfileId) return;

            if (!confirm('确定要删除这个用户画像吗？此操作不可恢复。')) {
                return;
            }

            try {
                await api.deleteProfile(selectedProfileId);
                alert('删除成功');
                closeModal();
                await loadProfiles(currentPage, currentSearch);
                await loadStats();
            } catch (error) {
                alert('删除失败: ' + error.message);
            }
        }

        // 点击弹窗外部关闭
        document.getElementById('profileModal').addEventListener('click', (e) => {
            if (e.target.id === 'profileModal') {
                closeModal();
            }
        });

        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
```

## 🔄 WebSocket实时更新示例

```javascript
class RealTimeProfileUpdater {
  constructor(apiClient) {
    this.api = apiClient;
    this.ws = null;
    this.callbacks = [];
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  // 连接WebSocket (如果后端支持)
  connect() {
    try {
      this.ws = new WebSocket('ws://localhost:3001/ws');
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立');
        this.reconnectAttempts = 0;
        
        // 发送认证信息
        this.ws.send(JSON.stringify({
          type: 'auth',
          token: localStorage.getItem('auth_token')
        }));
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };

      this.ws.onclose = () => {
        console.log('WebSocket连接已关闭');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
      };

    } catch (error) {
      console.error('WebSocket连接失败:', error);
      this.fallbackToPolling();
    }
  }

  // 处理WebSocket消息
  handleMessage(data) {
    switch (data.type) {
      case 'new_profile':
        this.notifyCallbacks('newProfile', data.profile);
        break;
      case 'profile_updated':
        this.notifyCallbacks('profileUpdated', data.profile);
        break;
      case 'profile_deleted':
        this.notifyCallbacks('profileDeleted', data.profileId);
        break;
      case 'stats_updated':
        this.notifyCallbacks('statsUpdated', data.stats);
        break;
    }
  }

  // 尝试重连
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, Math.pow(2, this.reconnectAttempts) * 1000);
    } else {
      console.log('WebSocket重连失败，切换到轮询模式');
      this.fallbackToPolling();
    }
  }

  // 降级到轮询模式
  fallbackToPolling() {
    this.startPolling();
  }

  // 开始轮询
  startPolling(interval = 30000) {
    this.pollingInterval = setInterval(async () => {
      try {
        const result = await this.api.checkUpdates();
        if (result.has_updates) {
          this.notifyCallbacks('hasUpdates', result);
        }
      } catch (error) {
        console.error('轮询检查更新失败:', error);
      }
    }, interval);
  }

  // 停止轮询
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  // 添加回调
  subscribe(callback) {
    this.callbacks.push(callback);
    return () => {
      const index = this.callbacks.indexOf(callback);
      if (index > -1) {
        this.callbacks.splice(index, 1);
      }
    };
  }

  // 通知所有回调
  notifyCallbacks(event, data) {
    this.callbacks.forEach(callback => {
      try {
        callback(event, data);
      } catch (error) {
        console.error('回调执行失败:', error);
      }
    });
  }

  // 断开连接
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.stopPolling();
  }
}

// 使用示例
const updater = new RealTimeProfileUpdater(api);

updater.subscribe((event, data) => {
  switch (event) {
    case 'newProfile':
      console.log('新画像:', data);
      showNotification(`新增用户画像: ${data.profile_name}`);
      refreshProfileList();
      break;
    
    case 'profileUpdated':
      console.log('画像更新:', data);
      updateProfileInList(data);
      break;
    
    case 'profileDeleted':
      console.log('画像删除:', data);
      removeProfileFromList(data);
      break;
    
    case 'statsUpdated':
      console.log('统计更新:', data);
      updateStatsDisplay(data);
      break;
    
    case 'hasUpdates':
      console.log('发现更新:', data);
      refreshAllData();
      break;
  }
});

// 开始实时更新
updater.connect();

// 页面卸载时断开连接
window.addEventListener('beforeunload', () => {
  updater.disconnect();
});
```

## 📱 移动端优化示例

```javascript
// 移动端适配工具类
class MobileOptimizer {
  constructor() {
    this.isMobile = this.detectMobile();
    this.init();
  }

  detectMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  init() {
    if (this.isMobile) {
      this.addMobileStyles();
      this.optimizeForMobile();
    }
  }

  addMobileStyles() {
    const style = document.createElement('style');
    style.textContent = `
      @media (max-width: 768px) {
        .profile-grid {
          grid-template-columns: 1fr;
          gap: 10px;
        }
        
        .profile-card {
          padding: 15px;
        }
        
        .stats-grid {
          grid-template-columns: repeat(2, 1fr);
        }
        
        .search-section input {
          width: 100%;
          margin-bottom: 10px;
        }
        
        .search-section button {
          width: 100%;
          margin-left: 0;
        }
        
        .modal-content {
          width: 95%;
          margin: 20px;
        }
        
        .pagination button {
          padding: 8px 12px;
          font-size: 14px;
        }
      }
    `;
    document.head.appendChild(style);
  }

  optimizeForMobile() {
    // 触摸优化
    this.addTouchSupport();
    
    // 减少动画
    this.reduceAnimations();
    
    // 优化加载性能
    this.optimizeLoading();
  }

  addTouchSupport() {
    // 为卡片添加触摸反馈
    document.addEventListener('touchstart', (e) => {
      if (e.target.closest('.profile-card')) {
        e.target.closest('.profile-card').style.transform = 'scale(0.98)';
      }
    });

    document.addEventListener('touchend', (e) => {
      if (e.target.closest('.profile-card')) {
        e.target.closest('.profile-card').style.transform = '';
      }
    });
  }

  reduceAnimations() {
    if (this.isMobile) {
      const style = document.createElement('style');
      style.textContent = `
        * {
          transition-duration: 0.1s !important;
          animation-duration: 0.1s !important;
        }
      `;
      document.head.appendChild(style);
    }
  }

  optimizeLoading() {
    // 移动端减少每页加载数量
    window.MOBILE_PAGE_SIZE = 8;
    
    // 图片懒加载
    this.addLazyLoading();
  }

  addLazyLoading() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          observer.unobserve(img);
        }
      });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      observer.observe(img);
    });
  }
}

// 初始化移动端优化
const mobileOptimizer = new MobileOptimizer();
```

这些示例涵盖了：

1. **React/Vue/原生JS**完整集成方案
2. **WebSocket实时更新**机制
3. **移动端优化**策略
4. **错误处理**最佳实践
5. **性能优化**技巧

每个示例都是可以直接使用的完整代码，帮助前端开发者快速集成API功能！