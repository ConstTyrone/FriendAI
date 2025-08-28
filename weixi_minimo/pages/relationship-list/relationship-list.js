// 关系列表页面
import themeManager from '../../utils/theme-manager';
import dataManager from '../../utils/data-manager';
import { showToast, showConfirm } from '../../utils/ui-utils';

Page({
  /**
   * 页面数据
   */
  data: {
    themeClass: '',
    
    // 页面信息
    contactId: null,
    contactName: '',
    
    // 关系数据
    relationships: [],
    filteredRelationships: [],
    
    // 筛选和排序
    currentFilter: 'all', // all, discovered, confirmed
    currentSortIndex: 0,
    sortOptions: [
      { label: '按时间排序', value: 'time_desc' },
      { label: '按可信度排序', value: 'confidence_desc' },
      { label: '按姓名排序', value: 'name_asc' }
    ],
    
    // 统计信息
    stats: {
      total_relationships: 0,
      confirmed_relationships: 0,
      discovered_relationships: 0
    },
    
    // 状态管理
    loading: false,
    error: null,
    batchProcessing: false
  },

  /**
   * 页面加载
   */
  onLoad(options) {
    console.log('关系列表页面加载:', options);
    
    this.initTheme();
    
    // 获取联系人ID
    if (options.contactId) {
      this.setData({
        contactId: parseInt(options.contactId),
        contactName: decodeURIComponent(options.contactName || '联系人')
      });
      
      // 加载关系数据
      this.loadRelationships();
    } else {
      this.setData({
        error: '缺少联系人信息'
      });
    }
  },

  /**
   * 页面显示
   */
  onShow() {
    // 刷新数据（可能有其他页面的操作影响）
    if (this.data.contactId) {
      this.loadRelationships();
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.loadRelationships().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 初始化主题
   */
  initTheme() {
    themeManager.applyToPage(this);
  },

  /**
   * 加载关系数据
   */
  async loadRelationships() {
    if (!this.data.contactId) return;
    
    this.setData({
      loading: true,
      error: null
    });
    
    try {
      console.log('加载联系人关系:', this.data.contactId);
      
      // 调用API获取关系数据
      const response = await dataManager.getContactRelationships(this.data.contactId);
      
      if (response && response.success) {
        const relationships = response.relationships || [];
        
        // 计算统计信息
        const stats = this.calculateStats(relationships);
        
        this.setData({
          relationships,
          stats
        });
        
        // 应用当前筛选条件
        this.applyFilter();
        
      } else {
        throw new Error(response?.message || '获取关系数据失败');
      }
      
    } catch (error) {
      console.error('加载关系数据失败:', error);
      this.setData({
        error: error.message || '加载失败，请重试'
      });
    } finally {
      this.setData({
        loading: false
      });
    }
  },

  /**
   * 计算统计信息
   */
  calculateStats(relationships) {
    const stats = {
      total_relationships: relationships.length,
      confirmed_relationships: 0,
      discovered_relationships: 0
    };
    
    relationships.forEach(rel => {
      if (rel.status === 'confirmed') {
        stats.confirmed_relationships++;
      } else if (rel.status === 'discovered') {
        stats.discovered_relationships++;
      }
    });
    
    return stats;
  },

  /**
   * 应用筛选条件
   */
  applyFilter() {
    const { relationships, currentFilter, currentSortIndex, sortOptions } = this.data;
    let filtered = [...relationships];
    
    // 应用筛选
    if (currentFilter !== 'all') {
      filtered = filtered.filter(rel => {
        if (currentFilter === 'discovered') {
          return rel.status === 'discovered';
        } else if (currentFilter === 'confirmed') {
          return rel.status === 'confirmed';
        }
        return true;
      });
    }
    
    // 应用排序
    const sortOption = sortOptions[currentSortIndex];
    filtered = this.sortRelationships(filtered, sortOption.value);
    
    this.setData({
      filteredRelationships: filtered
    });
  },

  /**
   * 排序关系列表
   */
  sortRelationships(relationships, sortType) {
    return relationships.sort((a, b) => {
      switch (sortType) {
        case 'time_desc':
          return new Date(b.created_at) - new Date(a.created_at);
        case 'confidence_desc':
          return (b.confidence_score || 0) - (a.confidence_score || 0);
        case 'name_asc':
          const nameA = this.getOtherProfileName(a);
          const nameB = this.getOtherProfileName(b);
          return nameA.localeCompare(nameB);
        default:
          return 0;
      }
    });
  },

  /**
   * 获取对方联系人姓名
   */
  getOtherProfileName(relationship) {
    const { contactId } = this.data;
    if (relationship.source_profile_id === contactId) {
      return relationship.targetProfile?.profile_name || '未知联系人';
    } else {
      return relationship.sourceProfile?.profile_name || '未知联系人';
    }
  },

  /**
   * 筛选条件改变
   */
  onFilterChange(e) {
    const filter = e.currentTarget.dataset.filter;
    console.log('切换筛选条件:', filter);
    
    this.setData({
      currentFilter: filter
    });
    
    this.applyFilter();
  },

  /**
   * 排序方式改变
   */
  onSortChange(e) {
    const sortIndex = e.detail.value;
    console.log('切换排序方式:', this.data.sortOptions[sortIndex]);
    
    this.setData({
      currentSortIndex: sortIndex
    });
    
    this.applyFilter();
  },

  /**
   * 关系卡片点击
   */
  onRelationshipTap(e) {
    const { relationship } = e.detail;
    console.log('点击关系卡片:', relationship);
    
    // 跳转到关系详情页面
    wx.navigateTo({
      url: `/pages/relationship-detail/relationship-detail?relationshipId=${relationship.id}`
    });
  },

  /**
   * 确认关系
   */
  async onConfirmRelationship(e) {
    const { relationship } = e.detail;
    console.log('确认关系:', relationship);
    
    try {
      const response = await dataManager.confirmRelationship(relationship.id);
      
      if (response && response.success) {
        showToast('关系已确认');
        
        // 更新本地数据
        this.updateRelationshipStatus(relationship.id, 'confirmed');
      } else {
        throw new Error(response?.message || '操作失败');
      }
      
    } catch (error) {
      console.error('确认关系失败:', error);
      showToast('操作失败，请重试');
    }
  },

  /**
   * 忽略关系
   */
  async onIgnoreRelationship(e) {
    const { relationship } = e.detail;
    console.log('忽略关系:', relationship);
    
    try {
      const confirmed = await showConfirm('忽略关系', '确定要忽略这个关系吗？');
      if (!confirmed) return;
      
      const response = await dataManager.ignoreRelationship(relationship.id);
      
      if (response && response.success) {
        showToast('关系已忽略');
        
        // 更新本地数据
        this.updateRelationshipStatus(relationship.id, 'ignored');
      } else {
        throw new Error(response?.message || '操作失败');
      }
      
    } catch (error) {
      console.error('忽略关系失败:', error);
      showToast('操作失败，请重试');
    }
  },

  /**
   * 更新关系状态
   */
  updateRelationshipStatus(relationshipId, newStatus) {
    const { relationships } = this.data;
    const updatedRelationships = relationships.map(rel => {
      if (rel.id === relationshipId) {
        return { ...rel, status: newStatus };
      }
      return rel;
    });
    
    // 重新计算统计信息
    const stats = this.calculateStats(updatedRelationships);
    
    this.setData({
      relationships: updatedRelationships,
      stats
    });
    
    // 重新应用筛选
    this.applyFilter();
  },

  /**
   * 批量确认
   */
  async onBatchConfirm() {
    const discoveredRelationships = this.data.relationships.filter(rel => rel.status === 'discovered');
    
    if (discoveredRelationships.length === 0) {
      showToast('没有待确认的关系');
      return;
    }
    
    const confirmed = await showConfirm(
      '批量确认',
      `确定要确认全部 ${discoveredRelationships.length} 个待确认关系吗？`
    );
    
    if (!confirmed) return;
    
    this.setData({ batchProcessing: true });
    
    try {
      const relationshipIds = discoveredRelationships.map(rel => rel.id);
      const response = await dataManager.batchConfirmRelationships(relationshipIds);
      
      if (response && response.success) {
        showToast('批量操作成功');
        
        // 更新本地数据
        const updatedRelationships = this.data.relationships.map(rel => {
          if (relationshipIds.includes(rel.id)) {
            return { ...rel, status: 'confirmed' };
          }
          return rel;
        });
        
        const stats = this.calculateStats(updatedRelationships);
        
        this.setData({
          relationships: updatedRelationships,
          stats
        });
        
        this.applyFilter();
      } else {
        throw new Error(response?.message || '批量操作失败');
      }
      
    } catch (error) {
      console.error('批量确认失败:', error);
      showToast('操作失败，请重试');
    } finally {
      this.setData({ batchProcessing: false });
    }
  },

  /**
   * 批量忽略
   */
  async onBatchIgnore() {
    const discoveredRelationships = this.data.relationships.filter(rel => rel.status === 'discovered');
    
    if (discoveredRelationships.length === 0) {
      showToast('没有待确认的关系');
      return;
    }
    
    const confirmed = await showConfirm(
      '批量忽略',
      `确定要忽略全部 ${discoveredRelationships.length} 个待确认关系吗？`
    );
    
    if (!confirmed) return;
    
    this.setData({ batchProcessing: true });
    
    try {
      const relationshipIds = discoveredRelationships.map(rel => rel.id);
      const response = await dataManager.batchIgnoreRelationships(relationshipIds);
      
      if (response && response.success) {
        showToast('批量操作成功');
        
        // 更新本地数据
        const updatedRelationships = this.data.relationships.map(rel => {
          if (relationshipIds.includes(rel.id)) {
            return { ...rel, status: 'ignored' };
          }
          return rel;
        });
        
        const stats = this.calculateStats(updatedRelationships);
        
        this.setData({
          relationships: updatedRelationships,
          stats
        });
        
        this.applyFilter();
      } else {
        throw new Error(response?.message || '批量操作失败');
      }
      
    } catch (error) {
      console.error('批量忽略失败:', error);
      showToast('操作失败，请重试');
    } finally {
      this.setData({ batchProcessing: false });
    }
  },

  /**
   * 重新分析关系
   */
  async onReanalyze() {
    if (!this.data.contactId) return;
    
    const confirmed = await showConfirm(
      '重新分析',
      '这将重新分析该联系人的所有关系，可能需要一些时间'
    );
    
    if (!confirmed) return;
    
    this.setData({
      loading: true,
      error: null
    });
    
    try {
      const response = await dataManager.reanalyzeContactRelationships(this.data.contactId);
      
      if (response && response.success) {
        showToast('重新分析完成');
        
        // 重新加载数据
        await this.loadRelationships();
      } else {
        throw new Error(response?.message || '重新分析失败');
      }
      
    } catch (error) {
      console.error('重新分析失败:', error);
      this.setData({
        error: error.message || '重新分析失败，请重试'
      });
    } finally {
      this.setData({
        loading: false
      });
    }
  },

  /**
   * 返回上一页
   */
  onBack() {
    wx.navigateBack();
  },

  /**
   * 页面滚动
   */
  onPageScroll(e) {
    // 可以在这里处理页面滚动事件
  },

  /**
   * 获取空状态标题
   */
  getEmptyTitle() {
    const { currentFilter } = this.data;
    switch (currentFilter) {
      case 'discovered':
        return '暂无待确认关系';
      case 'confirmed':
        return '暂无已确认关系';
      default:
        return '暂无关系数据';
    }
  },

  /**
   * 获取空状态描述
   */
  getEmptyDescription() {
    const { currentFilter } = this.data;
    switch (currentFilter) {
      case 'discovered':
        return '目前没有发现新的关系，系统会持续分析';
      case 'confirmed':
        return '还没有确认任何关系';
      default:
        return '系统正在分析该联系人的社交关系，请稍后查看';
    }
  },

  /**
   * 检查是否有待确认关系
   */
  get hasUncofirmedRelationships() {
    return this.data.relationships.some(rel => rel.status === 'discovered');
  },

  /**
   * 切换到图谱视图
   */
  onSwitchToGraph() {
    const contactId = this.data.contactId;
    wx.navigateTo({
      url: `/pages/relationship-graph/relationship-graph?centerNodeId=${contactId}`
    });
  }
});