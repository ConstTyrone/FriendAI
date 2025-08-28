import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import cacheManager from '../../utils/cache-manager';
import { showToast, showLoading, hideLoading } from '../../utils/ui-utils';

Page({
  data: {
    // 数据
    relationships: [],
    profiles: [],
    centerNodeId: null,
    
    // 搜索和筛选
    centerSearchKeyword: '',
    filteredProfiles: [],
    
    // 界面状态
    loading: true,
    error: null,
    showCenterSelector: false,
    fullscreenMode: false,
    
    // 画布尺寸
    graphWidth: 350,
    graphHeight: 400,
    fullscreenWidth: 375,
    fullscreenHeight: 667
  },
  
  onLoad(options) {
    // 从参数获取中心节点ID
    if (options.centerNodeId) {
      this.setData({
        centerNodeId: parseInt(options.centerNodeId)
      });
    }
    
    this.initPageSize();
    this.loadData();
  },
  
  onShow() {
    // 页面显示时刷新数据（可能有关系状态变更）
    if (!this.data.loading) {
      this.loadData();
    }
  },
  
  /**
   * 初始化页面尺寸
   */
  initPageSize() {
    const systemInfo = wx.getSystemInfoSync();
    const { windowWidth, windowHeight } = systemInfo;
    
    // 计算图谱画布尺寸（减去头部和边距）
    const graphHeight = windowHeight - 88 - 40; // 头部高度 + 边距
    
    this.setData({
      graphWidth: windowWidth - 32,
      graphHeight: Math.max(300, graphHeight),
      fullscreenWidth: windowWidth,
      fullscreenHeight: windowHeight
    });
  },
  
  /**
   * 加载数据
   */
  async loadData() {
    try {
      this.setData({ loading: true, error: null });
      
      // 检查登录状态
      const isLoggedIn = authManager.checkLoginStatus();
      if (!isLoggedIn) {
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }
      
      // 并行加载联系人和关系数据
      const [profiles, relationships] = await Promise.all([
        this.loadProfiles(),
        this.loadRelationships()
      ]);
      
      // 过滤出有关系的联系人
      const profilesWithRelationships = this.filterProfilesWithRelationships(profiles, relationships);
      
      this.setData({
        profiles: profilesWithRelationships,
        relationships: relationships,
        filteredProfiles: profilesWithRelationships,
        loading: false
      });
      
      // 如果没有指定中心节点，自动选择关系最多的联系人
      if (!this.data.centerNodeId && profilesWithRelationships.length > 0) {
        this.autoSelectCenterNode(profilesWithRelationships, relationships);
      }
      
    } catch (error) {
      console.error('加载关系图谱数据失败:', error);
      this.setData({
        loading: false,
        error: '加载数据失败，请重试'
      });
      showToast('加载数据失败');
    }
  },
  
  /**
   * 加载联系人数据
   */
  async loadProfiles() {
    try {
      // 先尝试从缓存获取
      const cachedProfiles = cacheManager.getContacts();
      if (cachedProfiles && cachedProfiles.length > 0) {
        return cachedProfiles;
      }
      
      // 从API获取
      const response = await dataManager.getContacts({
        page: 1,
        pageSize: 1000 // 获取所有联系人用于图谱分析
      });
      
      if (response.success && response.data) {
        const profiles = response.data;
        cacheManager.setContacts(profiles);
        return profiles;
      }
      
      return [];
      
    } catch (error) {
      console.error('加载联系人失败:', error);
      throw error;
    }
  },
  
  /**
   * 加载关系数据
   */
  async loadRelationships() {
    try {
      // 这里应该调用获取所有关系的API
      // 暂时使用模拟数据，实际应该调用 dataManager.getAllRelationships()
      
      // 尝试从缓存获取
      const cachedKey = 'all_relationships';
      const cachedData = cacheManager.get(cachedKey);
      if (cachedData) {
        return cachedData;
      }
      
      // 模拟API调用（实际开发中替换为真实API）
      const mockRelationships = this.generateMockRelationships();
      cacheManager.set(cachedKey, mockRelationships, 5 * 60 * 1000); // 缓存5分钟
      
      return mockRelationships;
      
    } catch (error) {
      console.error('加载关系数据失败:', error);
      throw error;
    }
  },
  
  /**
   * 生成模拟关系数据（用于测试）
   */
  generateMockRelationships() {
    const relationshipTypes = ['colleague', 'friend', 'partner', 'client', 'alumni'];
    const relationships = [];
    
    // 为演示目的生成一些模拟关系
    for (let i = 1; i <= 20; i++) {
      if (Math.random() > 0.3) { // 70%概率生成关系
        const sourceId = Math.floor(Math.random() * 10) + 1;
        let targetId = Math.floor(Math.random() * 10) + 1;
        
        // 确保不是自关系
        while (targetId === sourceId) {
          targetId = Math.floor(Math.random() * 10) + 1;
        }
        
        relationships.push({
          id: i,
          source_profile_id: sourceId,
          target_profile_id: targetId,
          relationship_type: relationshipTypes[Math.floor(Math.random() * relationshipTypes.length)],
          relationship_strength: ['weak', 'medium', 'strong'][Math.floor(Math.random() * 3)],
          confidence_score: 0.3 + Math.random() * 0.7,
          status: Math.random() > 0.3 ? 'discovered' : 'confirmed',
          evidence_fields: 'company,location',
          discovered_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        });
      }
    }
    
    return relationships;
  },
  
  /**
   * 过滤出有关系的联系人
   */
  filterProfilesWithRelationships(profiles, relationships) {
    const profileIds = new Set();
    
    // 收集所有在关系中出现的联系人ID
    relationships.forEach(rel => {
      profileIds.add(rel.source_profile_id);
      profileIds.add(rel.target_profile_id);
    });
    
    // 过滤联系人
    return profiles.filter(profile => profileIds.has(profile.id));
  },
  
  /**
   * 自动选择中心节点
   */
  autoSelectCenterNode(profiles, relationships) {
    // 计算每个联系人的关系数量
    const relationshipCounts = {};
    
    relationships.forEach(rel => {
      relationshipCounts[rel.source_profile_id] = (relationshipCounts[rel.source_profile_id] || 0) + 1;
      relationshipCounts[rel.target_profile_id] = (relationshipCounts[rel.target_profile_id] || 0) + 1;
    });
    
    // 找到关系数量最多的联系人
    let maxCount = 0;
    let centerNodeId = null;
    
    Object.entries(relationshipCounts).forEach(([profileId, count]) => {
      if (count > maxCount) {
        maxCount = count;
        centerNodeId = parseInt(profileId);
      }
    });
    
    if (centerNodeId) {
      this.setData({ centerNodeId });
    }
  },
  
  /**
   * 获取联系人关系数量
   */
  getContactRelationshipCount(contactId) {
    const count = this.data.relationships.filter(rel => 
      rel.source_profile_id === contactId || rel.target_profile_id === contactId
    ).length;
    
    return count;
  },
  
  /**
   * 返回上一页
   */
  onBack() {
    wx.navigateBack();
  },
  
  /**
   * 选择中心节点
   */
  onSelectCenter() {
    this.setData({ 
      showCenterSelector: true,
      filteredProfiles: this.data.profiles
    });
  },
  
  /**
   * 关闭中心节点选择器
   */
  onCenterSelectorClose() {
    this.setData({ 
      showCenterSelector: false,
      centerSearchKeyword: ''
    });
  },
  
  /**
   * 中心节点搜索
   */
  onCenterSearchChange(e) {
    const keyword = e.detail.value.toLowerCase();
    this.setData({ centerSearchKeyword: keyword });
    
    if (!keyword) {
      this.setData({ filteredProfiles: this.data.profiles });
      return;
    }
    
    const filtered = this.data.profiles.filter(profile => 
      profile.name.toLowerCase().includes(keyword) ||
      (profile.company && profile.company.toLowerCase().includes(keyword)) ||
      (profile.position && profile.position.toLowerCase().includes(keyword))
    );
    
    this.setData({ filteredProfiles: filtered });
  },
  
  /**
   * 执行中心节点搜索
   */
  onCenterSearch(e) {
    this.onCenterSearchChange(e);
  },
  
  /**
   * 选择中心联系人
   */
  onSelectCenterContact(e) {
    const contactId = e.currentTarget.dataset.contactId;
    this.setData({ 
      centerNodeId: contactId,
      showCenterSelector: false 
    });
    
    const contact = this.data.profiles.find(p => p.id === contactId);
    if (contact) {
      showToast(`已设置 ${contact.name} 为中心节点`);
    }
  },
  
  /**
   * 查看节点详情
   */
  onNodeDetail(e) {
    const { nodeId } = e.detail;
    wx.navigateTo({
      url: `/pages/contact-detail/contact-detail?id=${nodeId}`
    });
  },
  
  /**
   * 中心节点改变
   */
  onCenterChange(e) {
    const { centerNodeId } = e.detail;
    this.setData({ centerNodeId });
    
    const contact = this.data.profiles.find(p => p.id === centerNodeId);
    if (contact) {
      showToast(`已设置 ${contact.name} 为中心节点`);
    }
  },
  
  /**
   * 确认关系
   */
  async onConfirmRelationship(e) {
    try {
      const { relationshipId } = e.detail;
      showLoading('确认关系中...');
      
      // 调用确认关系API
      const response = await dataManager.confirmRelationship(relationshipId);
      
      if (response.success) {
        // 更新本地数据
        const relationships = this.data.relationships.map(rel => {
          if (rel.id === relationshipId) {
            return { ...rel, status: 'confirmed' };
          }
          return rel;
        });
        
        this.setData({ relationships });
        showToast('关系已确认');
      } else {
        showToast('确认关系失败');
      }
      
    } catch (error) {
      console.error('确认关系失败:', error);
      showToast('确认关系失败');
    } finally {
      hideLoading();
    }
  },
  
  /**
   * 忽略关系
   */
  async onIgnoreRelationship(e) {
    try {
      const { relationshipId } = e.detail;
      showLoading('忽略关系中...');
      
      // 调用忽略关系API
      const response = await dataManager.ignoreRelationship(relationshipId);
      
      if (response.success) {
        // 从本地数据中移除
        const relationships = this.data.relationships.filter(rel => rel.id !== relationshipId);
        this.setData({ relationships });
        showToast('关系已忽略');
      } else {
        showToast('忽略关系失败');
      }
      
    } catch (error) {
      console.error('忽略关系失败:', error);
      showToast('忽略关系失败');
    } finally {
      hideLoading();
    }
  },
  
  /**
   * 进入全屏模式
   */
  onFullscreen() {
    this.setData({ fullscreenMode: true });
  },
  
  /**
   * 退出全屏模式
   */
  onFullscreenClose() {
    this.setData({ fullscreenMode: false });
  },
  
  /**
   * 重试加载
   */
  onRetry() {
    this.loadData();
  }
});