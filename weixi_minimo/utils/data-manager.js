import { STORAGE_KEYS, EVENT_TYPES, UI_CONFIG } from './constants';
import { StorageManager } from './storage-utils';
import apiClient from './api-client';

class DataManager {
  constructor() {
    this.storage = new StorageManager('data');
    this.contacts = [];
    this.contactsMap = new Map();
    this.searchResults = [];
    this.searchHistory = [];
    this.stats = {};
    this.listeners = [];
    this.lastUpdateTime = null;
    this.isMockMode = false;  // Mock模式标识
    
    // 初始化时加载缓存数据
    this.loadFromCache();
    this.initMockMode();
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
    this.storage.cache('stats', this.stats);
    
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
      const cachedContacts = this.storage.get('contacts', []);
      this.contacts = cachedContacts;
      this.buildContactsMap();
      
      const cachedStats = this.storage.get('stats', {});
      this.stats = cachedStats;
      
      const cachedSearchHistory = this.storage.get('search_history', []);
      this.searchHistory = cachedSearchHistory;
      
      const cachedUpdateTime = this.storage.get('last_update_time');
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
      this.storage.cache('last_update_time', this.lastUpdateTime);
      
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
      this.storage.cache('stats', stats);
      
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
    this.storage.cache('search_history', this.searchHistory);
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
    this.storage.remove('search_history');
  }

  /**
   * 缓存联系人数据
   */
  cacheContacts() {
    this.storage.cache('contacts', this.contacts);
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
   * 清除所有缓存
   */
  clearCache() {
    this.contacts = [];
    this.contactsMap.clear();
    this.searchResults = [];
    this.searchHistory = [];
    this.stats = {};
    this.lastUpdateTime = null;
    
    this.storage.remove('contacts');
    this.storage.remove('stats');
    this.storage.remove('search_history');
    this.storage.remove('last_update_time');
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
        
        // 清除缓存，强制下次重新加载
        this.clearCache();
        
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
}

// 创建单例实例
const dataManager = new DataManager();

export default dataManager;