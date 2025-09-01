// 引入工具模块
const authManager = getApp().authManager || require('../../utils/auth-manager');
const dataManager = getApp().dataManager || require('../../utils/data-manager');
const cacheManager = getApp().cacheManager || require('../../utils/cache-manager');

// UI工具方法
const showToast = (message, icon = 'none', duration = 2000) => {
  wx.showToast({ title: message, icon, duration });
};

const showLoading = (title = '加载中...') => {
  wx.showLoading({ title });
};

const hideLoading = () => {
  wx.hideLoading();
};

Page({
  data: {
    // 数据
    relationships: [],
    profiles: [],
    centerNodeId: null,
    
    // 页面模式
    isGlobalMode: false,  // 是否为全局关系网络模式
    
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
    fullscreenHeight: 667,
    
    // UI数据
    relationshipTypes: [], // 关系类型统计
    confirmedCount: 0,     // 已确认关系数量
    selectedContactName: '' // 当前选中的联系人名称
  },
  
  onLoad(options) {
    // 从参数获取中心节点ID
    if (options.centerNodeId) {
      this.setData({
        centerNodeId: parseInt(options.centerNodeId),
        isGlobalMode: false
      });
      
      // 动态设置导航栏标题
      const title = options.contactName ? `${decodeURIComponent(options.contactName)}的关系` : '联系人关系';
      wx.setNavigationBarTitle({ title });
    } else {
      // 全局关系网络模式
      this.setData({
        isGlobalMode: true
      });
      wx.setNavigationBarTitle({ title: '关系网络' });
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
   * 初始化页面尺寸 - 最大化图谱画布空间
   */
  initPageSize() {
    const systemInfo = wx.getSystemInfoSync();
    const { windowWidth, windowHeight, safeArea } = systemInfo;
    
    console.log('🎯 开始计算最大化图谱尺寸...', { windowWidth, windowHeight });
    
    // 图谱画布最大化策略：压缩所有非核心UI元素
    const statusBarHeight = systemInfo.statusBarHeight || 0;
    const navigationBarHeight = 44; // 系统导航栏高度
    const headerInfoHeight = 50;  // 顶部信息栏极度压缩（原80→50）
    const footerInfoHeight = 60;  // 底部信息面板极度压缩（原100→60）
    const tabBarHeight = this.data.isGlobalMode ? 0 : 80; // 底部导航栏压缩（原98→80）
    const safeAreaBottom = safeArea ? (windowHeight - safeArea.bottom) : 0;
    const padding = 8; // 最小边距（原16→8）
    
    // 计算图谱可用高度 - 让图谱占据绝对主要空间
    const occupiedHeight = statusBarHeight + navigationBarHeight + headerInfoHeight + footerInfoHeight + tabBarHeight + safeAreaBottom + padding;
    const availableHeight = windowHeight - occupiedHeight;
    
    // 图谱高度策略：占据屏幕80-85%的空间
    const minHeight = Math.max(500, windowHeight * 0.75); // 至少75%屏幕高度（提升从60%）
    const preferredHeight = Math.max(availableHeight, windowHeight * 0.82); // 优选82%屏幕高度（提升从70%）
    const maxHeight = windowHeight * 0.85; // 最大85%屏幕高度
    const graphHeight = Math.min(maxHeight, Math.max(minHeight, preferredHeight));
    
    console.log('🎯 图谱尺寸最大化计算:', {
      windowHeight,
      occupiedHeight,
      availableHeight,
      graphHeight,
      minHeight,
      preferredHeight,
      screenRatio: (graphHeight / windowHeight * 100).toFixed(1) + '%'
    });
    
    this.setData({
      graphWidth: windowWidth - 8, // 最小边距8px（原16px）
      graphHeight,
      fullscreenWidth: windowWidth,
      fullscreenHeight: windowHeight
    });
  },
  
  /**
   * 标准化置信度分数
   * @param {any} value - 原始置信度值
   * @returns {number} - 标准化后的置信度分数 (0-1)
   */
  normalizeConfidenceScore(value) {
    // 处理undefined, null, 空字符串
    if (value === undefined || value === null || value === '') {
      console.warn('置信度值为空，使用默认值0.5');
      return 0.5;
    }
    
    // 转换为数字
    let score = parseFloat(value);
    
    // 处理NaN
    if (isNaN(score)) {
      console.warn('置信度值无法解析为数字:', value, '使用默认值0.5');
      return 0.5;
    }
    
    // 如果值大于1，假设是百分比形式，转换为小数
    if (score > 1) {
      score = score / 100;
    }
    
    // 确保在0-1范围内
    score = Math.max(0, Math.min(1, score));
    
    console.log('置信度标准化:', {原始值: value, 标准化后: score});
    return score;
  },

  /**
   * 加载数据
   */
  async loadData() {
    try {
      this.setData({ loading: true, error: null });
      
      // 检查登录状态
      const token = wx.getStorageSync('auth_token');
      if (!token) {
        wx.reLaunch({ url: '/pages/settings/settings' });
        return;
      }
      
      // 并行加载联系人和关系数据
      const [profiles, relationships] = await Promise.all([
        this.loadProfiles(),
        this.loadRelationships()
      ]);
      
      // 根据是否有中心节点决定显示逻辑
      let profilesWithRelationships;
      if (this.data.centerNodeId) {
        // 有中心节点时：显示中心节点和所有相关联系人
        profilesWithRelationships = relationships.length > 0 
          ? this.getRelatedProfiles(profiles, relationships, this.data.centerNodeId)
          : profiles.filter(p => p.id === this.data.centerNodeId);
      } else {
        // 无中心节点时：显示所有有关系的联系人，如果没有关系则显示所有联系人
        profilesWithRelationships = relationships.length > 0 
          ? this.filterProfilesWithRelationships(profiles, relationships)
          : profiles;
      }
      
      // 处理关系类型统计和联系人名称
      const relationshipTypes = this.processRelationshipTypes(relationships);
      const confirmedCount = this.getConfirmedCount(relationships);
      const selectedContactName = this.getSelectedContactName();
      
      console.log('🔄 设置页面数据...', {
        profiles: profilesWithRelationships.length,
        relationships: relationships.length,
        filteredProfiles: profilesWithRelationships.length,
        relationshipTypes: relationshipTypes.length,
        confirmedCount: confirmedCount,
        selectedContactName: selectedContactName,
        centerNodeId: this.data.centerNodeId
      });
      
      this.setData({
        profiles: profilesWithRelationships,
        relationships: relationships,
        filteredProfiles: profilesWithRelationships,
        relationshipTypes: relationshipTypes,
        confirmedCount: confirmedCount,
        selectedContactName: selectedContactName,
        loading: false
      });
      
      console.log('✅ 数据加载完成，已传递给组件');
      console.log('🔍 检查数据传递给组件:', {
        '组件profiles': this.data.profiles?.length || 0,
        '组件relationships': this.data.relationships?.length || 0,
        '画布尺寸': { width: this.data.graphWidth, height: this.data.graphHeight }
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
      // 直接使用wx.request调用API，避免模块导入问题
      console.log('开始获取联系人数据...');
      
      // 获取token
      const token = wx.getStorageSync('auth_token');
      if (!token) {
        console.error('用户未登录');
        return [];
      }
      
      return new Promise((resolve) => {
        wx.request({
          url: 'https://weixin.dataelem.com/api/profiles',
          method: 'GET',
          header: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          data: {
            page: 1,
            page_size: 1000
          },
          success: (res) => {
            console.log('联系人API响应:', res);
            
            if (res.statusCode === 200 && res.data) {
              // 检查是否有profiles字段
              const profilesList = res.data.profiles || res.data.contacts || [];
              const profiles = profilesList.map(profile => ({
                id: profile.id,
                name: profile.profile_name || profile.name || '未知',
                company: profile.basic_info?.company || profile.company || '',
                position: profile.basic_info?.position || profile.position || '',
                avatar: profile.avatar || ''
              }));
              
              console.log('处理后的联系人数据:', profiles);
              resolve(profiles);
            } else {
              console.warn('API响应格式错误:', res.data);
              resolve([]);
            }
          },
          fail: (error) => {
            console.error('API请求失败:', error);
            resolve([]);
          }
        });
      });
      
    } catch (error) {
      console.error('加载联系人失败:', error);
      return [];
    }
  },
  
  /**
   * 加载关系数据
   */
  async loadRelationships() {
    try {
      console.log('开始获取关系数据...');
      
      // 获取token
      const token = wx.getStorageSync('auth_token');
      if (!token) {
        console.error('用户未登录');
        return [];
      }
      
      // 如果指定了中心节点ID，获取特定联系人的关系；否则获取所有关系
      const apiUrl = this.data.centerNodeId 
        ? `https://weixin.dataelem.com/api/relationships/${this.data.centerNodeId}`
        : 'https://weixin.dataelem.com/api/relationships';
      
      console.log('关系API URL:', apiUrl);
      
      return new Promise((resolve) => {
        wx.request({
          url: apiUrl,
          method: 'GET',
          header: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          success: (res) => {
            console.log('关系API响应:', res);
            
            if (res.statusCode === 200 && res.data) {
              // 检查是否有relationships字段
              const relationshipsList = res.data.relationships || [];
              
              // 调试：检查原始数据
              console.log('=== 知识图谱页面调试 ===');
              if (relationshipsList.length > 0) {
                console.log('第一个原始关系:', JSON.stringify(relationshipsList[0], null, 2));
                console.log('原始confidence_score:', relationshipsList[0].confidence_score);
              }
              
              const relationships = relationshipsList.map(rel => {
                // 标准化置信度字段 - 统一使用confidence_score
                const confidence_score = this.normalizeConfidenceScore(rel.confidence_score || rel.confidence);
                
                console.log(`关系${rel.id}置信度标准化:`, {
                  原始confidence_score: rel.confidence_score,
                  备用confidence: rel.confidence,
                  最终值: confidence_score
                });
                
                return {
                  id: rel.id,
                  source_profile_id: rel.source_profile_id,
                  target_profile_id: rel.target_profile_id,
                  relationship_type: rel.relationship_type,
                  relationship_strength: rel.relationship_strength,
                  confidence_score: confidence_score, // 使用标准化后的置信度
                  status: rel.status || 'discovered',
                  evidence_fields: rel.evidence_fields || '',
                  discovered_at: rel.discovered_at || new Date().toISOString(),
                  updated_at: rel.updated_at || new Date().toISOString(),
                  // 保存完整的profile信息
                  sourceProfile: rel.sourceProfile,
                  targetProfile: rel.targetProfile
                };
              });
              
              console.log('处理后的关系数据:', relationships);
              resolve(relationships);
            } else {
              console.warn('关系API响应格式错误:', res.data);
              // 如果是特定联系人查询但没有数据，返回空数组
              if (this.data.centerNodeId) {
                resolve([]);
              } else {
                // 全局查询失败时返回模拟数据用于演示
                const mockRelationships = this.generateMockRelationships();
                resolve(mockRelationships);
              }
            }
          },
          fail: (error) => {
            console.error('关系API请求失败:', error);
            // 如果是特定联系人查询失败，返回空数组
            if (this.data.centerNodeId) {
              resolve([]);
            } else {
              // 全局查询失败时返回模拟数据用于演示
              const mockRelationships = this.generateMockRelationships();
              resolve(mockRelationships);
            }
          }
        });
      });
      
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
   * 获取与中心节点相关的联系人
   */
  getRelatedProfiles(profiles, relationships, centerNodeId) {
    const relatedIds = new Set();
    relatedIds.add(centerNodeId); // 包含中心节点本身
    
    // 收集与中心节点相关的所有联系人ID
    relationships.forEach(rel => {
      if (rel.source_profile_id === centerNodeId) {
        relatedIds.add(rel.target_profile_id);
      } else if (rel.target_profile_id === centerNodeId) {
        relatedIds.add(rel.source_profile_id);
      }
    });
    
    // 过滤联系人
    return profiles.filter(profile => relatedIds.has(profile.id));
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
      const contact = profiles.find(p => p.id === centerNodeId);
      const selectedContactName = contact ? contact.name : '未知联系人';
      this.setData({ 
        centerNodeId,
        selectedContactName 
      });
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
   * 获取选中联系人的名称
   */
  getSelectedContactName() {
    if (!this.data.centerNodeId) {
      return '关系网络';
    }
    
    const contact = this.data.profiles.find(p => p.id === this.data.centerNodeId);
    return contact ? contact.name : '未知联系人';
  },
  
  /**
   * 获取已确认关系数量
   */
  getConfirmedCount(relationships = null) {
    const rels = relationships || this.data.relationships;
    return rels.filter(rel => rel.status === 'confirmed').length;
  },
  
  /**
   * 处理关系类型统计
   */
  processRelationshipTypes(relationships) {
    const typeStats = {};
    const typeColors = {
      'colleague': '#3b82f6',    // 蓝色 - 同事
      'friend': '#10b981',       // 绿色 - 朋友
      'partner': '#f59e0b',      // 橙色 - 合作伙伴
      'client': '#ef4444',       // 红色 - 客户
      'alumni': '#8b5cf6',       // 紫色 - 校友
      'family': '#ec4899',       // 粉色 - 家人
      'other': '#6b7280'         // 灰色 - 其他
    };
    
    const typeNames = {
      'colleague': '同事',
      'friend': '朋友', 
      'partner': '合作伙伴',
      'client': '客户',
      'alumni': '校友',
      'family': '家人',
      'other': '其他'
    };
    
    // 统计每种关系类型的数量
    relationships.forEach(rel => {
      const type = rel.relationship_type || 'other';
      typeStats[type] = (typeStats[type] || 0) + 1;
    });
    
    // 转换为数组格式
    return Object.entries(typeStats).map(([type, count]) => ({
      type: type,
      name: typeNames[type] || type,
      count: count,
      color: typeColors[type] || typeColors.other
    }));
  },
  
  /**
   * 返回上一页
   */
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
    const contact = this.data.profiles.find(p => p.id === contactId);
    const selectedContactName = contact ? contact.name : '未知联系人';
    
    this.setData({ 
      centerNodeId: contactId,
      selectedContactName: selectedContactName,
      showCenterSelector: false 
    });
    
    if (contact) {
      showToast(`已设置 ${contact.name} 为中心节点`);
      // 重新加载该节点的关系数据
      this.loadData();
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
    const contact = this.data.profiles.find(p => p.id === centerNodeId);
    const selectedContactName = contact ? contact.name : '未知联系人';
    
    this.setData({ 
      centerNodeId,
      selectedContactName 
    });
    
    if (contact) {
      showToast(`已设置 ${contact.name} 为中心节点`);
      // 重新加载该节点的关系数据
      this.loadData();
    }
  },
  
  /**
   * 确认关系
   */
  async onConfirmRelationship(e) {
    try {
      const { relationshipId } = e.detail;
      showLoading('确认关系中...');
      
      // 获取token
      const token = wx.getStorageSync('auth_token');
      if (!token) {
        showToast('请先登录');
        return;
      }
      
      // 调用确认关系API
      wx.request({
        url: `https://weixin.dataelem.com/api/relationships/${relationshipId}/confirm`,
        method: 'PUT',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        success: (res) => {
          console.log('确认关系API响应:', res);
          
          if (res.statusCode === 200 && res.data && res.data.success) {
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
        },
        fail: (error) => {
          console.error('确认关系API请求失败:', error);
          showToast('确认关系失败');
        }
      });
      
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
      
      // 获取token
      const token = wx.getStorageSync('auth_token');
      if (!token) {
        showToast('请先登录');
        return;
      }
      
      // 调用忽略关系API
      wx.request({
        url: `https://weixin.dataelem.com/api/relationships/${relationshipId}/ignore`,
        method: 'DELETE',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        success: (res) => {
          console.log('忽略关系API响应:', res);
          
          if (res.statusCode === 200 && res.data && res.data.success) {
            // 从本地数据中移除
            const relationships = this.data.relationships.filter(rel => rel.id !== relationshipId);
            this.setData({ relationships });
            showToast('关系已忽略');
          } else {
            showToast('忽略关系失败');
          }
        },
        fail: (error) => {
          console.error('忽略关系API请求失败:', error);
          showToast('忽略关系失败');
        }
      });
      
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
  },
  
  /**
   * 导出图谱
   */
  onExport() {
    // TODO: 实现导出功能
    showToast('导出功能开发中', 'none');
  },
  
  /**
   * 放大图谱
   */
  onZoomIn() {
    // 通过组件事件通知图谱组件放大
    this.selectComponent('.relationship-graph')?.zoomIn();
  },
  
  /**
   * 缩小图谱
   */
  onZoomOut() {
    // 通过组件事件通知图谱组件缩小
    this.selectComponent('.relationship-graph')?.zoomOut();
  },
  
  /**
   * 重置视图
   */
  onResetView() {
    // 通过组件事件通知图谱组件重置视图
    this.selectComponent('.relationship-graph')?.resetView();
  },
  
  /**
   * 底部导航栏切换
   */
  onTabChange(e) {
    const { path } = e.detail;
    wx.redirectTo({
      url: path
    });
  }
});