import { STORAGE_KEYS, EVENT_TYPES, UI_CONFIG } from './constants';
import apiClient from './api-client';
import cacheManager from './cache-manager';
import compatibility from './compatibility';

class DataManager {
  constructor() {
    // 统一使用cacheManager，不再使用StorageManager
    this.contacts = [];
    this.contactsMap = new Map();
    this.searchResults = [];
    this.searchHistory = [];
    this.stats = {};
    this.listeners = [];
    this.lastUpdateTime = null;
    this.isMockMode = false;  // Mock模式标识
    this.maxMapSize = 500;  // Map最大容量限制
    this.memoryCleanupTimer = null; // 内存清理定时器
    this.isAppActive = true; // 应用是否活跃
    this.autoRefreshTimer = null; // 自动刷新定时器
    this.autoRefreshInterval = 30000; // 自动刷新间隔（30秒）
    
    // 初始化时加载缓存数据
    this.loadFromCache();
    this.initMockMode();
    
    // 不立即启动清理，等待应用初始化完成
  }

  /**
   * 初始化Mock模式检查
   */
  initMockMode() {
    try {
      const app = getApp();
      if (app && app.globalData) {
        const userInfo = app.globalData.userInfo;
        this.isMockMode = userInfo && userInfo.isMock;
        
        if (this.isMockMode) {
          console.log('检测到Mock模式，将使用本地模拟数据');
          this.setupMockData();
        }
      }
    } catch (error) {
      console.error('初始化Mock模式失败:', error);
    }
  }

  /**
   * 启用Mock模式
   */
  enableMockMode() {
    console.log('启用Mock模式');
    this.isMockMode = true;
    this.setupMockData();
    
    // 更新缓存数据为Mock数据
    this.contacts = this.mockContacts;
    this.buildContactsMap();
    this.cacheContacts();
    
    // 更新统计信息
    this.stats = this.mockStats;
    cacheManager.set('stats', this.stats, 'STATS');
    
    // 通知监听器
    this.notifyListeners('mockModeEnabled', this.mockContacts);
  }

  /**
   * 设置Mock数据
   */
  setupMockData() {
    this.mockContacts = [
      {
        id: 'mock_1',
        profile_id: 'mock_1',
        profile_name: '张伟（Mock）',
        gender: '男',
        age: 32,
        phone: '138****8888',
        location: '上海市浦东新区',
        company: 'Mock科技有限公司',
        position: '技术总监',
        marital_status: '已婚',
        assets: '中等',
        notes: '这是一个Mock测试联系人，用于前端功能测试',
        ai_summary: 'Mock联系人，技术背景，善于沟通，可以合作技术项目',
        created_at: '2024-01-15',
        updated_at: '2024-08-06',
        tags: ['技术', '合作伙伴', '上海']
      },
      {
        id: 'mock_2',
        profile_id: 'mock_2',
        profile_name: '李娜（Mock）',
        gender: '女',
        age: 28,
        phone: '139****9999',
        location: '北京市朝阳区',
        company: 'Mock互联网公司',
        position: '产品经理',
        marital_status: '未婚',
        assets: '较好',
        notes: 'Mock数据，产品思维敏锐，有很好的用户体验理念',
        ai_summary: 'Mock联系人，产品背景，注重用户体验，可以在产品设计方面合作',
        created_at: '2024-02-20',
        updated_at: '2024-08-06',
        tags: ['产品', '用户体验', '北京']
      },
      {
        id: 'mock_3',
        profile_id: 'mock_3',
        profile_name: '王明（Mock）',
        gender: '男',
        age: 45,
        phone: '136****7777',
        location: '深圳市南山区',
        company: 'Mock投资集团',
        position: '投资总监',
        marital_status: '已婚',
        assets: '优秀',
        notes: 'Mock投资人，对科技行业有深度理解',
        ai_summary: 'Mock联系人，投资背景，关注科技创新，可能的投资合作伙伴',
        created_at: '2024-03-10',
        updated_at: '2024-08-06',
        tags: ['投资', '科技', '深圳', '资源']
      },
      {
        id: 'mock_4',
        profile_id: 'mock_4',
        profile_name: '陈红（Mock）',
        gender: '女',
        age: 31,
        phone: '137****6666',
        location: '杭州市西湖区',
        company: 'Mock设计工作室',
        position: '设计总监',
        marital_status: '已婚',
        assets: '中等',
        notes: 'Mock设计师，擅长UI/UX设计',
        ai_summary: 'Mock联系人，设计背景，创意思维活跃，可以在设计项目上合作',
        created_at: '2024-04-05',
        updated_at: '2024-08-06',
        tags: ['设计', 'UI/UX', '创意', '杭州']
      },
      {
        id: 'mock_5',
        profile_id: 'mock_5',
        profile_name: '刘强（Mock）',
        gender: '男',
        age: 38,
        phone: '135****5555',
        location: '广州市天河区',
        company: 'Mock电商平台',
        position: '运营总监',
        marital_status: '已婚',
        assets: '较好',
        notes: 'Mock运营专家，擅长用户增长和数据分析',
        ai_summary: 'Mock联系人，运营背景，数据驱动思维，可以在用户增长方面合作',
        created_at: '2024-05-12',
        updated_at: '2024-08-06',
        tags: ['运营', '数据分析', '用户增长', '广州']
      }
    ];

    this.mockStats = {
      total_profiles: this.mockContacts.length,
      today_profiles: 2
    };
  }

  /**
   * 从缓存加载数据
   */
  loadFromCache() {
    try {
      // 使用新的分级缓存管理器
      const cachedContacts = cacheManager.get('contacts', []);
      this.contacts = cachedContacts;
      this.buildContactsMap();
      
      const cachedStats = cacheManager.get('stats', {});
      this.stats = cachedStats;
      
      const cachedSearchHistory = cacheManager.get('search_history', []);
      this.searchHistory = cachedSearchHistory;
      
      const cachedUpdateTime = cacheManager.get('last_update_time');
      this.lastUpdateTime = cachedUpdateTime;
      
      console.log('从缓存加载数据完成:', {
        contacts: this.contacts.length,
        searchHistory: this.searchHistory.length
      });
    } catch (error) {
      console.error('从缓存加载数据失败:', error);
    }
  }

  /**
   * 构建联系人映射表
   */
  buildContactsMap() {
    this.contactsMap.clear();
    this.contacts.forEach(contact => {
      this.contactsMap.set(contact.id, contact);
    });
  }

  /**
   * 获取联系人列表
   */
  async getContacts(params = {}) {
    try {
      const {
        page = 1,
        pageSize = UI_CONFIG.PAGE_SIZE,
        search = '',
        forceRefresh = false
      } = params;
      
      // 如果有搜索词，调用搜索接口
      if (search) {
        return await this.searchContacts(search);
      }
      
      // Mock模式：使用本地模拟数据
      if (this.isMockMode) {
        console.log('Mock模式：返回本地模拟联系人数据');
        const startIndex = (page - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const pagedContacts = this.mockContacts.slice(startIndex, endIndex);
        
        // 更新本地缓存
        if (page === 1) {
          this.contacts = this.mockContacts;
          this.buildContactsMap();
          this.cacheContacts();
        }
        
        return {
          profiles: pagedContacts,
          total: this.mockContacts.length,
          page,
          page_size: pageSize,
          total_pages: Math.ceil(this.mockContacts.length / pageSize),
          message: '当前使用Mock数据（测试模式）'
        };
      }
      
      // 如果不强制刷新且有缓存数据，先返回缓存
      if (!forceRefresh && this.contacts.length > 0) {
        const startIndex = (page - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const pagedContacts = this.contacts.slice(startIndex, endIndex);
        
        return {
          profiles: pagedContacts,
          total: this.contacts.length,
          page,
          page_size: pageSize,
          total_pages: Math.ceil(this.contacts.length / pageSize)
        };
      }
      
      // 从API获取数据
      let result;
      try {
        result = await apiClient.getProfiles({ page, pageSize, search });
      } catch (apiError) {
        console.error('API请求失败:', apiError);
        // 如果是网络错误，使用本地模拟数据
        if (apiError.errMsg && apiError.errMsg.includes('request:fail')) {
          console.log('使用本地模拟联系人数据');
          result = {
            profiles: [
              {
                id: 'demo_1',
                profile_id: 'demo_1',
                profile_name: '张三（示例）',
                gender: '男',
                age: 35,
                phone: '138****0001',
                location: '上海市浦东新区',
                company: '示例科技有限公司',
                position: '产品经理',
                ai_summary: '这是一个示例联系人，后端服务不可用时显示'
              },
              {
                id: 'demo_2',
                profile_id: 'demo_2',
                profile_name: '李四（示例）',
                gender: '女',
                age: 28,
                phone: '139****0002',
                location: '北京市朝阳区',
                company: '示例互联网公司',
                position: '市场总监',
                ai_summary: '这是另一个示例联系人'
              }
            ],
            total: 2,
            page: 1,
            page_size: 20,
            total_pages: 1,
            message: '当前使用本地示例数据（后端服务不可用）'
          };
        } else {
          throw apiError;
        }
      }
      
      // 如果是第一页，替换缓存数据
      if (page === 1) {
        this.contacts = result.profiles || [];
        this.buildContactsMap();
        this.cacheContacts();
      } else {
        // 如果是其他页，追加数据
        const existingIds = new Set(this.contacts.map(c => c.id));
        const newContacts = (result.profiles || []).filter(c => !existingIds.has(c.id));
        this.contacts.push(...newContacts);
        this.buildContactsMap();
        this.cacheContacts();
      }
      
      this.lastUpdateTime = Date.now();
      cacheManager.set('last_update_time', this.lastUpdateTime, 'default');
      
      // 缓存搜索结果（如果是搜索请求）
      if (params.search) {
        const cacheKey = `search_${params.search}_${page}`;
        cacheManager.set(cacheKey, result, 'SEARCH_RESULT');
      }
      
      // 触发数据更新事件
      this.notifyListeners('contactsUpdated', this.contacts);
      
      return result;
    } catch (error) {
      console.error('获取联系人列表失败:', error);
      
      // 如果API失败且有缓存数据，返回缓存数据
      if (this.contacts.length > 0) {
        const startIndex = (params.page - 1) * params.pageSize;
        const endIndex = startIndex + params.pageSize;
        const pagedContacts = this.contacts.slice(startIndex, endIndex);
        
        return {
          profiles: pagedContacts,
          total: this.contacts.length,
          page: params.page,
          page_size: params.pageSize,
          total_pages: Math.ceil(this.contacts.length / params.pageSize)
        };
      }
      
      throw error;
    }
  }

  /**
   * 获取联系人详情
   */
  async getContactDetail(contactId) {
    try {
      // Mock模式：使用本地模拟数据
      if (this.isMockMode) {
        console.log('Mock模式：获取联系人详情', contactId);
        const mockContact = this.mockContacts.find(contact => contact.id === contactId);
        if (mockContact) {
          // 为Mock数据添加一些详细信息
          const detailedMockContact = {
            ...mockContact,
            raw_message_content: `这是${mockContact.profile_name}的Mock原始消息内容，用于测试联系人详情页面功能。包含了完整的联系人信息和AI分析结果。`,
            interaction_count: Math.floor(Math.random() * 10) + 1,
            last_interaction: new Date().toISOString(),
            relationship_score: Math.floor(Math.random() * 50) + 50
          };
          return detailedMockContact;
        } else {
          throw new Error('Mock联系人不存在');
        }
      }
      
      // 先从缓存中查找
      if (this.contactsMap.has(contactId)) {
        const cachedContact = this.contactsMap.get(contactId);
        
        // 如果缓存的是简化数据，需要从API获取完整数据
        if (!cachedContact.raw_message_content) {
          const fullContact = await apiClient.getProfileDetail(contactId);
          this.contactsMap.set(contactId, fullContact);
          this.updateContactInList(fullContact);
          this.cacheContacts();
          return fullContact;
        }
        
        return cachedContact;
      }
      
      // 从API获取数据
      const contact = await apiClient.getProfileDetail(contactId);
      
      // 更新缓存
      this.contactsMap.set(contactId, contact);
      this.updateContactInList(contact);
      this.cacheContacts();
      
      return contact;
    } catch (error) {
      console.error('获取联系人详情失败:', error);
      throw error;
    }
  }

  /**
   * 获取联系人互动记录
   */
  async getContactInteractions(contactId, limit = 10) {
    try {
      const result = await apiClient.getContactInteractions(contactId, limit);
      return result.interactions || [];
    } catch (error) {
      console.error('获取联系人互动记录失败:', error);
      return [];
    }
  }

  /**
   * 删除联系人
   */
  async deleteContact(contactId) {
    try {
      await apiClient.deleteProfile(contactId);
      
      // 从缓存中删除
      this.contactsMap.delete(contactId);
      this.contacts = this.contacts.filter(contact => contact.id !== contactId);
      this.cacheContacts();
      
      // 触发删除事件
      this.notifyListeners('contactDeleted', contactId);
      this.notifyListeners(EVENT_TYPES.CONTACT_DELETED, contactId);
      
      // 刷新统计信息
      await this.refreshStats();
      
      return true;
    } catch (error) {
      console.error('删除联系人失败:', error);
      throw error;
    }
  }

  /**
   * 搜索联系人
   */
  async searchContacts(query, limit = 20) {
    try {
      if (!query.trim()) {
        return {
          profiles: [],
          total: 0,
          query: ''
        };
      }
      
      // Mock模式：使用本地搜索
      if (this.isMockMode) {
        console.log('Mock模式：本地搜索联系人', query);
        const lowerQuery = query.toLowerCase();
        
        const searchResults = this.mockContacts.filter(contact => {
          return (
            (contact.profile_name && contact.profile_name.toLowerCase().includes(lowerQuery)) ||
            (contact.company && contact.company.toLowerCase().includes(lowerQuery)) ||
            (contact.position && contact.position.toLowerCase().includes(lowerQuery)) ||
            (contact.location && contact.location.toLowerCase().includes(lowerQuery)) ||
            (contact.notes && contact.notes.toLowerCase().includes(lowerQuery)) ||
            (contact.ai_summary && contact.ai_summary.toLowerCase().includes(lowerQuery)) ||
            (contact.tags && contact.tags.some(tag => tag.toLowerCase().includes(lowerQuery)))
          );
        });
        
        // 保存搜索历史
        this.addSearchHistory(query);
        
        // 限制结果数量
        const limitedResults = searchResults.slice(0, limit);
        this.searchResults = limitedResults;
        
        // 触发搜索事件
        this.notifyListeners('searchPerformed', { query, results: limitedResults });
        this.notifyListeners(EVENT_TYPES.SEARCH_PERFORMED, { query, results: limitedResults });
        
        return {
          profiles: limitedResults,
          total: limitedResults.length,
          query: query,
          message: '当前使用Mock数据搜索'
        };
      }
      
      const result = await apiClient.searchProfiles(query, limit);
      this.searchResults = result.profiles || [];
      
      // 保存搜索历史
      this.addSearchHistory(query);
      
      // 触发搜索事件
      this.notifyListeners('searchPerformed', { query, results: this.searchResults });
      this.notifyListeners(EVENT_TYPES.SEARCH_PERFORMED, { query, results: this.searchResults });
      
      return result;
    } catch (error) {
      console.error('搜索联系人失败:', error);
      throw error;
    }
  }

  /**
   * 获取最近联系人
   */
  async getRecentContacts(limit = 10) {
    try {
      const result = await apiClient.getRecentProfiles(limit);
      return result.profiles || [];
    } catch (error) {
      console.error('获取最近联系人失败:', error);
      return [];
    }
  }

  /**
   * 获取统计信息
   */
  async getStats(forceRefresh = false) {
    try {
      // Mock模式：使用本地模拟统计数据
      if (this.isMockMode) {
        console.log('Mock模式：返回模拟统计数据');
        return this.mockStats;
      }
      
      if (!forceRefresh && Object.keys(this.stats).length > 0) {
        return this.stats;
      }
      
      const stats = await apiClient.getStats();
      this.stats = stats;
      // 统计信息缓存1小时
      cacheManager.set('stats', stats, 'STATS');
      
      return stats;
    } catch (error) {
      console.error('获取统计信息失败:', error);
      
      // 返回缓存的统计信息
      return this.stats;
    }
  }

  /**
   * 刷新统计信息
   */
  async refreshStats() {
    try {
      const stats = await this.getStats(true);
      this.notifyListeners('statsUpdated', stats);
      return stats;
    } catch (error) {
      console.error('刷新统计信息失败:', error);
      return this.stats;
    }
  }

  /**
   * 检查数据更新
   */
  async checkUpdates() {
    try {
      const result = await apiClient.checkUpdates(this.lastUpdateTime);
      
      if (result.has_updates) {
        // 有新数据，刷新联系人列表
        await this.getContacts({ forceRefresh: true });
        await this.refreshStats();
        
        this.notifyListeners('dataUpdated', result);
        
        return result;
      }
      
      return result;
    } catch (error) {
      console.error('检查数据更新失败:', error);
      return { has_updates: false };
    }
  }

  /**
   * 添加搜索历史
   */
  addSearchHistory(query) {
    if (!query || !query.trim()) return;
    
    const trimmedQuery = query.trim();
    
    // 移除重复项
    this.searchHistory = this.searchHistory.filter(item => item !== trimmedQuery);
    
    // 添加到开头
    this.searchHistory.unshift(trimmedQuery);
    
    // 限制历史记录数量
    if (this.searchHistory.length > 20) {
      this.searchHistory = this.searchHistory.slice(0, 20);
    }
    
    // 保存到缓存
    cacheManager.set('search_history', this.searchHistory, 'default');
  }

  /**
   * 获取搜索历史
   */
  getSearchHistory() {
    return this.searchHistory;
  }

  /**
   * 清除搜索历史
   */
  clearSearchHistory() {
    this.searchHistory = [];
    cacheManager.clear('search_history');
  }

  /**
   * 缓存联系人数据
   */
  cacheContacts() {
    // 使用分级缓存，联系人列表缓存30分钟
    cacheManager.set('contacts', this.contacts, 'CONTACT_LIST');
  }

  /**
   * 更新列表中的联系人
   */
  updateContactInList(updatedContact) {
    const index = this.contacts.findIndex(contact => contact.id === updatedContact.id);
    if (index !== -1) {
      this.contacts[index] = updatedContact;
    } else {
      this.contacts.unshift(updatedContact);
    }
  }

  /**
   * 获取联系人总数
   */
  getContactCount() {
    return this.contacts.length;
  }

  /**
   * 根据ID获取联系人
   */
  getContactById(contactId) {
    return this.contactsMap.get(contactId);
  }

  /**
   * 本地搜索联系人
   */
  localSearchContacts(query) {
    if (!query.trim()) {
      return [];
    }
    
    const lowerQuery = query.toLowerCase();
    
    return this.contacts.filter(contact => {
      return (
        (contact.profile_name && contact.profile_name.toLowerCase().includes(lowerQuery)) ||
        (contact.company && contact.company.toLowerCase().includes(lowerQuery)) ||
        (contact.position && contact.position.toLowerCase().includes(lowerQuery)) ||
        (contact.location && contact.location.toLowerCase().includes(lowerQuery)) ||
        (contact.phone && contact.phone.includes(query))
      );
    });
  }

  /**
   * 清除所有缓存（包括关系数据缓存）
   */
  clearCache() {
    this.contacts = [];
    this.contactsMap.clear();
    this.searchResults = [];
    this.searchHistory = [];
    this.stats = {};
    this.lastUpdateTime = null;
    
    // 清除基础缓存
    cacheManager.clear('contacts');
    cacheManager.clear('stats');
    cacheManager.clear('search_history');
    cacheManager.clear('last_update_time');
    
    // 清除所有关系相关缓存
    // 由于关系缓存键包含ID，我们通过clearAll来清除所有关系缓存
    const stats = cacheManager.getStats();
    if (stats.memoryItems > 0 || stats.storageItems > 0) {
      // 获取所有缓存键并清除关系相关的
      try {
        const res = wx.getStorageInfoSync();
        res.keys.forEach(key => {
          if (key.startsWith('cache_relationships_') || 
              key.startsWith('cache_relationship_detail_') || 
              key.startsWith('cache_relationship_stats_')) {
            wx.removeStorageSync(key);
          }
        });
        console.log('已清除所有关系相关缓存');
      } catch (error) {
        console.error('清除关系缓存失败:', error);
      }
    }
  }

  /**
   * 智能缓存失效策略 - 当联系人更新时清除相关关系缓存
   * @param {string} contactId - 联系人ID
   */
  invalidateRelatedRelationshipCache(contactId) {
    try {
      // 清除该联系人的关系缓存
      cacheManager.clearRelationshipCache(contactId);
      
      // 清除可能关联的其他联系人的关系缓存
      // 这里可以根据具体业务逻辑优化，比如只清除有实际关系的联系人缓存
      console.log(`已清除联系人 ${contactId} 相关的关系缓存`);
    } catch (error) {
      console.error('智能缓存失效失败:', error);
    }
  }

  /**
   * 预加载关系数据
   * @param {string} contactId - 联系人ID
   * @param {number} priority - 优先级 (1-10, 10最高)
   */
  async preloadRelationshipData(contactId, priority = 5) {
    try {
      // 检查是否已有缓存
      const cached = cacheManager.getRelationships(contactId);
      if (cached !== null) {
        console.log(`关系数据已缓存，跳过预加载: ${contactId}`);
        return;
      }
      
      console.log(`预加载关系数据: ${contactId}, 优先级: ${priority}`);
      
      // 异步预加载，不阻塞主流程
      setTimeout(async () => {
        try {
          await this.getContactRelationships(contactId);
          console.log(`关系数据预加载完成: ${contactId}`);
        } catch (error) {
          console.error(`关系数据预加载失败: ${contactId}`, error);
        }
      }, priority > 7 ? 0 : 1000); // 高优先级立即执行，否则延迟1秒
      
    } catch (error) {
      console.error('预加载关系数据失败:', error);
    }
  }

  /**
   * 批量预加载关系数据
   * @param {Array} contactIds - 联系人ID数组
   */
  async batchPreloadRelationshipData(contactIds) {
    console.log(`批量预加载关系数据: ${contactIds.length} 个联系人`);
    
    const promises = contactIds.map((contactId, index) => {
      // 分批执行，避免同时发起太多请求
      const delay = Math.floor(index / 3) * 500; // 每3个一批，间隔500ms
      return new Promise(resolve => {
        setTimeout(() => {
          this.preloadRelationshipData(contactId, 3).finally(resolve);
        }, delay);
      });
    });
    
    try {
      await Promise.all(promises);
      console.log('批量预加载完成');
    } catch (error) {
      console.error('批量预加载失败:', error);
    }
  }

  /**
   * 添加事件监听器
   */
  addListener(listener) {
    this.listeners.push(listener);
    
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }
  
  /**
   * 移除指定监听器
   */
  removeListener(listener) {
    const index = this.listeners.indexOf(listener);
    if (index > -1) {
      this.listeners.splice(index, 1);
      console.log('已移除数据监听器');
    }
  }
  
  /**
   * 移除所有监听器
   */
  removeAllListeners() {
    this.listeners = [];
    console.log('已移除所有数据监听器');
  }

  /**
   * 通知监听器
   */
  notifyListeners(eventType, data = null) {
    this.listeners.forEach(listener => {
      try {
        listener(eventType, data);
      } catch (error) {
        console.error('数据管理器事件监听器执行失败:', error);
      }
    });
  }

  /**
   * 获取数据概览
   */
  getDataOverview() {
    return {
      contactCount: this.contacts.length,
      searchHistoryCount: this.searchHistory.length,
      lastUpdateTime: this.lastUpdateTime,
      stats: this.stats
    };
  }

  /**
   * 创建联系人
   * @param {Object} profileData - 联系人数据
   */
  async createProfile(profileData) {
    console.log('========= DataManager.createProfile =========');
    console.log('传入数据:', JSON.stringify(profileData, null, 2));
    console.log('API Client:', typeof apiClient, !!apiClient.createProfile);
    
    try {
      // 调用API创建联系人
      console.log('开始调用 apiClient.createProfile...');
      const result = await apiClient.createProfile(profileData);
      console.log('API调用完成，原始结果:', result);
      
      if (result.success) {
        console.log('联系人创建成功:', result);
        
        // 清除缓存，强制下次重新加载
        this.clearCache();
        
        // 刷新统计信息
        await this.refreshStats();
        
        // 通知监听器
        this.notifyListeners('contact_created', result.profile);
        
        return result;
      } else {
        throw new Error(result.message || '创建失败');
      }
    } catch (error) {
      console.error('创建联系人失败:', error);
      throw error;
    }
  }

  /**
   * 更新联系人
   * @param {string|number} profileId - 联系人ID
   * @param {Object} profileData - 更新的数据
   */
  async updateProfile(profileId, profileData) {
    console.log('DataManager: 更新联系人', profileId, profileData);
    
    try {
      // 调用API更新联系人
      const result = await apiClient.updateProfile(profileId, profileData);
      
      if (result.success) {
        console.log('联系人更新成功:', result);
        
        // 更新本地缓存
        if (result.profile) {
          const index = this.contacts.findIndex(c => c.id === profileId);
          if (index !== -1) {
            this.contacts[index] = result.profile;
            this.contactsMap.set(profileId, result.profile);
          }
        }
        
        // 智能缓存失效 - 清除相关关系缓存
        this.invalidateRelatedRelationshipCache(profileId);
        
        // 清除缓存，强制下次重新加载
        this.clearCache();
        
        // 刷新统计信息
        await this.refreshStats();
        
        // 通知监听器
        this.notifyListeners('contact_updated', result.profile);
        
        return result;
      } else {
        throw new Error(result.message || '更新失败');
      }
    } catch (error) {
      console.error('更新联系人失败:', error);
      throw error;
    }
  }

  /**
   * 解析导入文件
   */
  async parseImportFile(filePath) {
    console.log('DataManager: 解析导入文件', filePath);
    
    try {
      const result = await apiClient.parseImportFile(filePath);
      console.log('文件解析结果:', result);
      return result;
    } catch (error) {
      console.error('解析导入文件失败:', error);
      throw error;
    }
  }

  /**
   * 批量导入联系人
   */
  async batchImportProfiles(profiles, importMode = 'create') {
    console.log('DataManager: 批量导入联系人', profiles.length, importMode);
    
    try {
      // 如果是Mock模式，模拟批量导入
      if (this.isMockMode) {
        return this.mockBatchImport(profiles, importMode);
      }
      
      const result = await apiClient.batchImportProfiles({
        profiles: profiles,
        import_mode: importMode
      });
      
      if (result.success) {
        console.log('批量导入成功:', result);
        
        // 清除缓存，强制下次重新加载
        this.clearCache();
        
        // 通知监听器
        this.notifyListeners('contacts_batch_imported', result);
        
        return result;
      } else {
        throw new Error(result.message || '批量导入失败');
      }
    } catch (error) {
      console.error('批量导入联系人失败:', error);
      throw error;
    }
  }

  /**
   * Mock模式下的批量导入
   */
  mockBatchImport(profiles, importMode) {
    console.log('Mock模式: 模拟批量导入', profiles.length);
    
    const result = {
      success: true,
      total_count: profiles.length,
      success_count: 0,
      failed_count: 0,
      skipped_count: 0,
      errors: [],
      created_profiles: []
    };
    
    profiles.forEach((profile, index) => {
      try {
        // 验证必填字段
        if (!profile.name || !profile.name.trim()) {
          result.failed_count++;
          result.errors.push({
            index: index,
            name: profile.name || '未知',
            error: '联系人姓名不能为空'
          });
          return;
        }
        
        // 检查重复
        if (importMode === 'skip_duplicate') {
          const existing = this.contacts.find(c => 
            c.profile_name === profile.name.trim() || c.name === profile.name.trim()
          );
          if (existing) {
            result.skipped_count++;
            return;
          }
        }
        
        // 创建新联系人
        const newContact = {
          id: Date.now() + index,  // 模拟ID
          profile_name: profile.name.trim(),
          phone: profile.phone || '未知',
          company: profile.company || '未知',
          position: profile.position || '未知',
          location: profile.address || profile.location || '未知',
          tags: profile.tags || [],
          created_at: new Date().toISOString(),
          ...profile
        };
        
        // 添加到本地数据
        this.contacts.unshift(newContact);
        this.contactsMap.set(newContact.id, newContact);
        
        result.success_count++;
        result.created_profiles.push(newContact);
        
      } catch (error) {
        result.failed_count++;
        result.errors.push({
          index: index,
          name: profile.name || '未知',
          error: error.message
        });
      }
    });
    
    // 保存到缓存
    this.saveToCache();
    
    console.log('Mock批量导入完成:', result);
    return result;
  }
  
  /**
   * 启动内存清理定时器
   */
  startMemoryCleanup() {
    // 如果已经在运行，不重复启动
    if (this.memoryCleanupTimer) {
      console.log('内存清理定时器已在运行');
      return;
    }
    
    // 标记为活跃
    this.isAppActive = true;
    
    // 每5分钟清理一次
    this.memoryCleanupTimer = setInterval(() => {
      // 只在应用活跃时清理
      if (this.isAppActive) {
        this.cleanupMemory();
      }
    }, 5 * 60 * 1000);
    
    console.log('内存清理定时器已启动');
  }
  
  /**
   * 停止内存清理定时器
   */
  stopMemoryCleanup() {
    this.isAppActive = false;
    
    if (this.memoryCleanupTimer) {
      clearInterval(this.memoryCleanupTimer);
      this.memoryCleanupTimer = null;
      console.log('内存清理定时器已停止');
    }
  }
  
  /**
   * 设置应用活跃状态
   */
  setAppActive(active) {
    this.isAppActive = active;
    console.log('应用活跃状态:', active);
  }
  
  /**
   * 清理内存
   */
  cleanupMemory() {
    console.log('开始内存清理...');
    
    // 1. 限制Map大小
    if (this.contactsMap.size > this.maxMapSize) {
      const excess = this.contactsMap.size - this.maxMapSize;
      const iterator = this.contactsMap.keys();
      
      // 删除最早的条目
      for (let i = 0; i < excess; i++) {
        const key = iterator.next().value;
        this.contactsMap.delete(key);
      }
      
      console.log(`清理了 ${excess} 个Map条目`);
    }
    
    // 2. 限制搜索历史长度
    if (this.searchHistory.length > 50) {
      this.searchHistory = this.searchHistory.slice(-50);
      console.log('清理搜索历史，保留最近50条');
    }
    
    // 3. 清理搜索结果缓存
    if (this.searchResults.length > 100) {
      this.searchResults = this.searchResults.slice(0, 100);
      console.log('清理搜索结果缓存');
    }
    
    // 4. 触发微信垃圾回收（如果可用）
    compatibility.safeTriggerGC();
    
    // 5. 清理过期缓存
    cacheManager.cleanExpired();
    
    console.log('内存清理完成', this.getMemoryStats());
  }
  
  /**
   * 获取内存统计信息
   */
  getMemoryStats() {
    return {
      contactsCount: this.contacts.length,
      mapSize: this.contactsMap.size,
      searchHistoryLength: this.searchHistory.length,
      searchResultsLength: this.searchResults.length,
      listenersCount: this.listeners.length
    };
  }
  
  /**
   * 解析语音文本，提取用户画像
   * @param {string} text - 语音识别后的文本
   * @param {boolean} mergeMode - 是否为合并模式（编辑现有联系人）
   * @returns {Promise<Object>} 解析结果
   */
  async parseVoiceText(text, mergeMode = false) {
    try {
      console.log('解析语音文本:', text, '合并模式:', mergeMode);
      
      // 调用后端API
      const response = await apiClient.post('/api/profiles/parse-voice', {
        text: text,
        merge_mode: mergeMode
      });
      
      console.log('语音文本解析结果:', response);
      
      return response;
    } catch (error) {
      console.error('解析语音文本失败:', error);
      throw error;
    }
  }
  
  /**
   * 手动触发垃圾回收
   */
  forceGarbageCollection() {
    this.cleanupMemory();
    
    // 清空不必要的引用
    this.searchResults = [];
    
    // 重建Map以释放内存
    const tempMap = new Map(this.contactsMap);
    this.contactsMap.clear();
    this.contactsMap = tempMap;
    
    console.log('强制垃圾回收完成');
  }
  
  /**
   * 启动自动刷新
   */
  startAutoRefresh() {
    if (this.autoRefreshTimer) {
      console.log('自动刷新已在运行');
      return; // 已经在运行
    }
    
    console.log('启动自动数据刷新，间隔：30秒');
    
    this.autoRefreshTimer = setInterval(async () => {
      try {
        // 只在应用活跃时进行检查
        if (!this.isAppActive) {
          return;
        }
        
        // 检查是否有数据更新
        const updateResult = await this.checkUpdates();
        
        if (updateResult.has_updates) {
          console.log('检测到数据更新，刷新联系人列表');
          
          // 清除缓存并获取新数据
          this.clearCache();
          await this.getContacts({ forceRefresh: true });
          
          // 通知所有监听器数据已更新
          this.notifyListeners('contactsUpdated', this.contacts);
          this.notifyListeners('dataUpdated', { 
            type: 'auto_refresh',
            timestamp: Date.now(),
            updateCount: updateResult.update_count || 1
          });
        }
      } catch (error) {
        console.error('自动刷新检查失败:', error);
        // 失败时不影响定时器继续运行
      }
    }, this.autoRefreshInterval);
  }
  
  /**
   * 停止自动刷新
   */
  stopAutoRefresh() {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer);
      this.autoRefreshTimer = null;
      console.log('停止自动数据刷新');
    }
  }
  
  /**
   * 设置自动刷新间隔
   * @param {number} interval 间隔时间（毫秒）
   */
  setAutoRefreshInterval(interval) {
    if (interval < 10000) {
      console.warn('自动刷新间隔不能少于10秒');
      return;
    }
    
    this.autoRefreshInterval = interval;
    console.log(`自动刷新间隔已设置为 ${interval / 1000} 秒`);
    
    // 如果正在运行，重启以应用新间隔
    if (this.autoRefreshTimer) {
      this.stopAutoRefresh();
      this.startAutoRefresh();
    }
  }
  
  /**
   * 获取自动刷新状态
   */
  getAutoRefreshStatus() {
    return {
      isRunning: !!this.autoRefreshTimer,
      interval: this.autoRefreshInterval,
      intervalSeconds: this.autoRefreshInterval / 1000
    };
  }
  
  // ============ 关系管理相关方法 ============
  
  /**
   * 获取联系人关系（优化版本 - 支持智能缓存）
   * @param {string} contactId - 联系人ID
   * @param {boolean} forceRefresh - 是否强制刷新
   * @returns {Promise<Object>} API响应
   */
  async getContactRelationships(contactId, forceRefresh = false) {
    try {
      console.log('获取联系人关系:', contactId, forceRefresh ? '(强制刷新)' : '');
      
      // Mock模式下返回模拟数据
      if (this.isMockMode) {
        return this.getMockRelationships(contactId);
      }
      
      // 如果不是强制刷新，先检查缓存
      if (!forceRefresh) {
        const cachedData = cacheManager.getRelationships(contactId);
        if (cachedData !== null) {
          console.log('使用缓存的关系数据:', contactId);
          return cachedData;
        }
      }
      
      // 从API获取数据
      const response = await apiClient.get(`/api/relationships/${contactId}`);
      console.log('从API获取关系数据成功:', response);
      
      // 缓存数据
      if (response && response.success) {
        cacheManager.setRelationships(contactId, response);
        console.log('关系数据已缓存');
      }
      
      return response;
    } catch (error) {
      console.error('获取关系数据失败:', error);
      
      // 先尝试使用过期的缓存数据
      const expiredCachedData = cacheManager.getRelationships(contactId);
      if (expiredCachedData !== null) {
        console.log('使用过期缓存的关系数据（降级策略）');
        return expiredCachedData;
      }
      
      // 网络错误时返回模拟数据
      if (error.message.includes('网络') || error.message.includes('Network')) {
        console.log('网络错误，使用Mock数据');
        return this.getMockRelationships(contactId);
      }
      
      throw error;
    }
  }
  
  /**
   * 确认关系
   * @param {number} relationshipId - 关系ID
   * @returns {Promise<Object>} API响应
   */
  async confirmRelationship(relationshipId) {
    try {
      console.log('确认关系:', relationshipId);
      
      // Mock模式下模拟确认操作
      if (this.isMockMode) {
        return {
          success: true,
          message: '关系确认成功（Mock模式）',
          data: { id: relationshipId, status: 'confirmed' }
        };
      }
      
      const response = await apiClient.post(`/api/relationships/${relationshipId}/confirm`);
      console.log('确认关系成功:', response);
      
      // 清除相关缓存
      cacheManager.clearRelationshipDetailCache(relationshipId);
      
      // 通知监听器
      this.notifyListeners('relationship_confirmed', { relationshipId });
      
      return response;
    } catch (error) {
      console.error('确认关系失败:', error);
      throw error;
    }
  }
  
  /**
   * 忽略关系
   * @param {number} relationshipId - 关系ID
   * @returns {Promise<Object>} API响应
   */
  async ignoreRelationship(relationshipId) {
    try {
      console.log('忽略关系:', relationshipId);
      
      // Mock模式下模拟忽略操作
      if (this.isMockMode) {
        return {
          success: true,
          message: '关系已忽略（Mock模式）',
          data: { id: relationshipId, status: 'ignored' }
        };
      }
      
      const response = await apiClient.post(`/api/relationships/${relationshipId}/ignore`);
      console.log('忽略关系成功:', response);
      
      // 清除相关缓存
      cacheManager.clearRelationshipDetailCache(relationshipId);
      
      // 通知监听器
      this.notifyListeners('relationship_ignored', { relationshipId });
      
      return response;
    } catch (error) {
      console.error('忽略关系失败:', error);
      throw error;
    }
  }
  
  /**
   * 批量确认关系
   * @param {Array} relationshipIds - 关系ID数组
   * @returns {Promise<Object>} API响应
   */
  async batchConfirmRelationships(relationshipIds) {
    try {
      console.log('批量确认关系:', relationshipIds);
      
      // Mock模式下模拟批量确认
      if (this.isMockMode) {
        return {
          success: true,
          message: `批量确认了 ${relationshipIds.length} 个关系（Mock模式）`,
          data: {
            confirmed_count: relationshipIds.length,
            failed_count: 0
          }
        };
      }
      
      const response = await apiClient.post('/api/relationships/batch/confirm', {
        relationship_ids: relationshipIds
      });
      console.log('批量确认成功:', response);
      
      // 批量清除相关缓存
      cacheManager.batchClearRelationshipCache(relationshipIds);
      
      // 通知监听器
      this.notifyListeners('relationships_batch_confirmed', { relationshipIds });
      
      return response;
    } catch (error) {
      console.error('批量确认关系失败:', error);
      throw error;
    }
  }
  
  /**
   * 批量忽略关系
   * @param {Array} relationshipIds - 关系ID数组
   * @returns {Promise<Object>} API响应
   */
  async batchIgnoreRelationships(relationshipIds) {
    try {
      console.log('批量忽略关系:', relationshipIds);
      
      // Mock模式下模拟批量忽略
      if (this.isMockMode) {
        return {
          success: true,
          message: `批量忽略了 ${relationshipIds.length} 个关系（Mock模式）`,
          data: {
            ignored_count: relationshipIds.length,
            failed_count: 0
          }
        };
      }
      
      const response = await apiClient.post('/api/relationships/batch/ignore', {
        relationship_ids: relationshipIds
      });
      console.log('批量忽略成功:', response);
      
      // 批量清除相关缓存
      cacheManager.batchClearRelationshipCache(relationshipIds);
      
      // 通知监听器
      this.notifyListeners('relationships_batch_ignored', { relationshipIds });
      
      return response;
    } catch (error) {
      console.error('批量忽略关系失败:', error);
      throw error;
    }
  }
  
  /**
   * 重新分析联系人关系
   * @param {number} contactId - 联系人ID
   * @returns {Promise<Object>} API响应
   */
  async reanalyzeContactRelationships(contactId) {
    try {
      console.log('重新分析联系人关系:', contactId);
      
      // Mock模式下模拟重新分析
      if (this.isMockMode) {
        return {
          success: true,
          message: '关系重新分析完成（Mock模式）',
          data: {
            analyzed_count: Math.floor(Math.random() * 5) + 1,
            new_relationships: Math.floor(Math.random() * 3)
          }
        };
      }
      
      const response = await apiClient.post(`/api/relationships/${contactId}/reanalyze`);
      console.log('重新分析成功:', response);
      
      // 清除该联系人的关系缓存，强制重新获取
      cacheManager.clearRelationshipCache(contactId);
      
      // 通知监听器
      this.notifyListeners('relationships_reanalyzed', { contactId });
      
      return response;
    } catch (error) {
      console.error('重新分析关系失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取关系详情（优化版本 - 支持智能缓存）
   * @param {string} relationshipId - 关系ID
   * @param {boolean} forceRefresh - 是否强制刷新
   * @returns {Promise<Object>} API响应
   */
  async getRelationshipDetail(relationshipId, forceRefresh = false) {
    try {
      console.log('获取关系详情:', relationshipId, forceRefresh ? '(强制刷新)' : '');
      
      // Mock模式下返回模拟数据
      if (this.isMockMode) {
        return this.getMockRelationshipDetail(relationshipId);
      }
      
      // 如果不是强制刷新，先检查缓存
      if (!forceRefresh) {
        const cachedData = cacheManager.getRelationshipDetail(relationshipId);
        if (cachedData !== null) {
          console.log('使用缓存的关系详情数据:', relationshipId);
          return cachedData;
        }
      }
      
      // 从API获取数据
      const response = await apiClient.get(`/api/relationships/detail/${relationshipId}`);
      console.log('从API获取关系详情成功:', response);
      
      // 缓存数据
      if (response && response.success) {
        cacheManager.setRelationshipDetail(relationshipId, response);
        console.log('关系详情数据已缓存');
      }
      
      return response;
    } catch (error) {
      console.error('获取关系详情失败:', error);
      
      // 先尝试使用过期的缓存数据
      const expiredCachedData = cacheManager.getRelationshipDetail(relationshipId);
      if (expiredCachedData !== null) {
        console.log('使用过期缓存的关系详情（降级策略）');
        return expiredCachedData;
      }
      
      // 网络错误时返回模拟数据
      if (error.message.includes('网络') || error.message.includes('Network')) {
        console.log('网络错误，使用Mock数据');
        return this.getMockRelationshipDetail(relationshipId);
      }
      
      throw error;
    }
  },

  /**
   * 获取Mock模式的关系详情
   * @param {number} relationshipId - 关系ID
   * @returns {Object} Mock关系详情数据
   */
  getMockRelationshipDetail(relationshipId) {
    console.log('生成Mock关系详情数据，关系ID:', relationshipId);
    
    // 模拟详细的关系数据
    const mockRelationshipDetail = {
      id: relationshipId,
      source_profile_id: 'mock_1',
      target_profile_id: 'mock_2',
      relationship_type: 'colleague',
      confidence_score: 0.85,
      status: 'discovered',
      evidence: {
        matched_fields: ['company', 'location', 'industry'],
        field_scores: {
          'company': 0.95,
          'location': 0.78,
          'industry': 0.82
        },
        details: {
          'company_source': 'Mock科技有限公司',
          'company_target': 'Mock科技有限公司',
          'location_source': '上海市浦东新区',
          'location_target': '上海市浦东新区张江',
          'industry_source': '互联网科技',
          'industry_target': '软件开发'
        }
      },
      ai_analysis: '基于工作地点和公司信息的分析显示，两位联系人很可能是同事关系。相同的公司背景和相近的工作地点为这个关系提供了强有力的证据。建议确认这个关系并在工作协作中保持联系。',
      created_at: '2024-08-06T10:30:00Z',
      updated_at: '2024-08-06T15:45:00Z',
      sourceProfile: {
        id: 'mock_1',
        profile_name: '张伟（Mock）',
        company: 'Mock科技有限公司',
        position: '技术总监',
        location: '上海市浦东新区',
        phone: '138****8888'
      },
      targetProfile: {
        id: 'mock_2',
        profile_name: '李娜（Mock）',
        company: 'Mock科技有限公司',
        position: '产品经理',
        location: '上海市浦东新区张江',
        phone: '139****9999'
      }
    };
    
    return {
      success: true,
      message: 'Mock关系详情数据',
      data: mockRelationshipDetail
    };
  },

  /**
   * 获取Mock模式的关系数据
   * @param {number} contactId - 联系人ID
   * @returns {Object} Mock关系数据
   */
  getMockRelationships(contactId) {
    console.log('生成Mock关系数据，联系人ID:', contactId);
    
    // 根据联系人ID生成不同的模拟关系
    const mockRelationships = [
      {
        id: 1,
        source_profile_id: contactId,
        target_profile_id: contactId === 'mock_1' ? 'mock_2' : 'mock_1',
        relationship_type: 'colleague',
        confidence_score: 0.85,
        status: 'discovered',
        evidence: {
          matched_fields: ['company'],
          details: '同公司员工'
        },
        created_at: '2024-08-06T10:30:00Z',
        sourceProfile: {
          id: contactId,
          profile_name: contactId === 'mock_1' ? '张伟（Mock）' : '李娜（Mock）'
        },
        targetProfile: {
          id: contactId === 'mock_1' ? 'mock_2' : 'mock_1',
          profile_name: contactId === 'mock_1' ? '李娜（Mock）' : '张伟（Mock）'
        }
      },
      {
        id: 2,
        source_profile_id: contactId,
        target_profile_id: 'mock_3',
        relationship_type: 'same_location',
        confidence_score: 0.72,
        status: 'discovered',
        evidence: {
          matched_fields: ['location'],
          details: '同一地区'
        },
        created_at: '2024-08-06T11:15:00Z',
        sourceProfile: {
          id: contactId,
          profile_name: contactId === 'mock_1' ? '张伟（Mock）' : '李娜（Mock）'
        },
        targetProfile: {
          id: 'mock_3',
          profile_name: '王强（Mock）'
        }
      }
    ];
    
    // 如果联系人ID是mock_1，增加一个已确认的关系
    if (contactId === 'mock_1') {
      mockRelationships.push({
        id: 3,
        source_profile_id: contactId,
        target_profile_id: 'mock_4',
        relationship_type: 'alumni',
        confidence_score: 0.91,
        status: 'confirmed',
        evidence: {
          matched_fields: ['education'],
          details: '同校校友'
        },
        created_at: '2024-08-05T14:20:00Z',
        sourceProfile: {
          id: contactId,
          profile_name: '张伟（Mock）'
        },
        targetProfile: {
          id: 'mock_4',
          profile_name: '赵丽（Mock）'
        }
      });
    }
    
    return {
      success: true,
      message: 'Mock关系数据',
      data: mockRelationships
    };
  }
}

// 创建单例实例
const dataManager = new DataManager();

export default dataManager;