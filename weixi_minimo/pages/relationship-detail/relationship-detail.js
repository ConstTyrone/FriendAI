// 关系详情页面
import themeManager from '../../utils/theme-manager';
import dataManager from '../../utils/data-manager';
import { showToast, showConfirm } from '../../utils/ui-utils';
import { formatDate, formatDateTime } from '../../utils/format-utils';

Page({
  /**
   * 页面数据
   */
  data: {
    themeClass: '',
    
    // 关系信息
    relationshipId: null,
    relationship: null,
    
    // 证据列表
    evidenceList: [],
    
    // 时间线数据
    timeline: [],
    
    // 相关建议
    suggestions: [],
    
    // 状态管理
    loading: false,
    error: null
  },

  /**
   * 页面加载
   */
  onLoad(options) {
    console.log('关系详情页面加载:', options);
    
    this.initTheme();
    
    // 获取关系ID
    if (options.relationshipId) {
      this.setData({
        relationshipId: parseInt(options.relationshipId)
      });
      
      // 加载关系详情
      this.loadRelationshipDetail();
    } else {
      this.setData({
        error: '缺少关系ID参数'
      });
    }
  },

  /**
   * 页面显示
   */
  onShow() {
    // 刷新数据（可能有其他页面的操作影响）
    if (this.data.relationshipId) {
      this.loadRelationshipDetail();
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.loadRelationshipDetail().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 分享页面
   */
  onShareAppMessage() {
    const { relationship } = this.data;
    return {
      title: `${relationship?.sourceName || '联系人'} 和 ${relationship?.targetName || '联系人'} 的关系`,
      path: `/pages/relationship-detail/relationship-detail?relationshipId=${this.data.relationshipId}`,
      imageUrl: ''
    };
  },

  /**
   * 初始化主题
   */
  initTheme() {
    themeManager.applyToPage(this);
  },

  /**
   * 加载关系详情
   */
  async loadRelationshipDetail() {
    if (!this.data.relationshipId) return;
    
    this.setData({
      loading: true,
      error: null
    });
    
    try {
      console.log('加载关系详情:', this.data.relationshipId);
      
      // 调用API获取关系详情
      const response = await dataManager.getRelationshipDetail(this.data.relationshipId);
      
      if (response && response.success) {
        const relationship = response.data;
        
        // 处理关系数据
        this.processRelationshipData(relationship);
        
        // 生成时间线
        this.generateTimeline(relationship);
        
        // 生成建议
        this.generateSuggestions(relationship);
        
      } else {
        throw new Error(response?.message || '获取关系详情失败');
      }
      
    } catch (error) {
      console.error('加载关系详情失败:', error);
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
   * 处理关系数据
   */
  processRelationshipData(rawRelationship) {
    // 提取联系人信息
    const sourceName = rawRelationship.sourceProfile?.profile_name || '未知联系人';
    const targetName = rawRelationship.targetProfile?.profile_name || '未知联系人';
    const sourceCompany = rawRelationship.sourceProfile?.company || '未知公司';
    const targetCompany = rawRelationship.targetProfile?.company || '未知公司';
    
    // 生成首字母
    const sourceInitial = this.getNameInitial(sourceName);
    const targetInitial = this.getNameInitial(targetName);
    
    // 处理证据数据
    const evidenceList = this.processEvidence(rawRelationship.evidence);
    
    // 处理AI分析
    const aiAnalysis = rawRelationship.ai_analysis || this.generateDefaultAnalysis(rawRelationship);
    const analysisTags = this.extractAnalysisTags(aiAnalysis);
    
    const relationship = {
      ...rawRelationship,
      sourceName,
      targetName,
      sourceCompany,
      targetCompany,
      sourceInitial,
      targetInitial,
      ai_analysis: aiAnalysis,
      analysis_tags: analysisTags
    };
    
    this.setData({
      relationship,
      evidenceList
    });
  },

  /**
   * 获取姓名首字母
   */
  getNameInitial(name) {
    if (!name) return '?';
    const firstChar = name.charAt(0);
    return /[\u4e00-\u9fa5]/.test(firstChar) ? firstChar : firstChar.toUpperCase();
  },

  /**
   * 处理证据数据
   */
  processEvidence(evidence) {
    if (!evidence || typeof evidence !== 'object') return [];
    
    const evidenceList = [];
    const { matched_fields = [], field_scores = {}, details = {} } = evidence;
    
    matched_fields.forEach(field => {
      evidenceList.push({
        field,
        match_score: Math.round((field_scores[field] || 0.5) * 100),
        source_value: details[`${field}_source`] || '未知',
        target_value: details[`${field}_target`] || '未知'
      });
    });
    
    return evidenceList;
  },

  /**
   * 生成默认分析
   */
  generateDefaultAnalysis(relationship) {
    const relationshipTypes = {
      'colleague': '同事关系通常意味着工作上的协作机会，可以考虑在项目合作中互相支持。',
      'same_location': '地理位置相近的联系人便于线下会面，有助于建立更深层次的合作关系。',
      'alumni': '校友关系是珍贵的社交网络资源，通常有着相似的教育背景和价值观。',
      'same_industry': '同行业的专业人士可以相互学习，分享行业洞察和最佳实践。',
      'client': '客户关系需要用心维护，持续提供价值是保持长期合作的关键。',
      'partner': '合作伙伴关系建立在互利共赢的基础上，需要定期沟通以加强合作。'
    };
    
    return relationshipTypes[relationship.relationship_type] || 
           '这是一个重要的社交关系，建议定期保持联系以维护和发展这种关系。';
  },

  /**
   * 提取分析标签
   */
  extractAnalysisTags(analysis) {
    const tagKeywords = {
      '工作': '工作合作',
      '项目': '项目协作', 
      '合作': '合作伙伴',
      '学习': '学习成长',
      '价值': '价值创造',
      '沟通': '定期沟通',
      '维护': '关系维护'
    };
    
    const tags = [];
    Object.keys(tagKeywords).forEach(keyword => {
      if (analysis.includes(keyword)) {
        tags.push(tagKeywords[keyword]);
      }
    });
    
    return tags.length > 0 ? tags : ['重要关系'];
  },

  /**
   * 生成时间线
   */
  generateTimeline(relationship) {
    const timeline = [];
    
    // 关系发现
    timeline.push({
      id: `created_${relationship.id}`,
      type: 'created',
      title: '关系被发现',
      description: `系统分析发现了这个${this.formatRelationshipType(relationship.relationship_type)}关系`,
      timestamp: relationship.created_at
    });
    
    // 关系更新
    if (relationship.updated_at && relationship.updated_at !== relationship.created_at) {
      timeline.push({
        id: `updated_${relationship.id}`,
        type: 'updated',
        title: '关系信息更新',
        description: '关系的详细信息或可信度发生了更新',
        timestamp: relationship.updated_at
      });
    }
    
    // 关系确认或忽略
    if (relationship.status === 'confirmed') {
      timeline.push({
        id: `confirmed_${relationship.id}`,
        type: 'confirmed',
        title: '关系已确认',
        description: '用户确认了这个关系的真实性',
        timestamp: relationship.confirmed_at || relationship.updated_at
      });
    } else if (relationship.status === 'ignored') {
      timeline.push({
        id: `ignored_${relationship.id}`,
        type: 'ignored',
        title: '关系已忽略',
        description: '用户选择忽略这个关系',
        timestamp: relationship.ignored_at || relationship.updated_at
      });
    }
    
    // 按时间倒序排列
    timeline.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    this.setData({ timeline });
  },

  /**
   * 生成建议
   */
  generateSuggestions(relationship) {
    const suggestions = [];
    
    // 基于关系类型的建议
    const typeSuggestions = this.getTypeSuggestions(relationship.relationship_type);
    suggestions.push(...typeSuggestions);
    
    // 基于状态的建议
    if (relationship.status === 'confirmed') {
      suggestions.push({
        id: 'maintain_relationship',
        icon: '💬',
        title: '保持联系',
        description: '定期与双方保持沟通，维护这个重要关系'
      });
      
      suggestions.push({
        id: 'introduce_contacts',
        icon: '🤝',
        title: '牵线搭桥',
        description: '在合适的时机为双方引荐，促成更多合作'
      });
    }
    
    // 通用建议
    suggestions.push({
      id: 'update_profiles',
      icon: '📝',
      title: '更新信息',
      description: '完善双方联系人信息，提高关系发现的准确性'
    });
    
    this.setData({ suggestions });
  },

  /**
   * 获取关系类型建议
   */
  getTypeSuggestions(relationshipType) {
    const suggestionMap = {
      'colleague': [
        {
          id: 'work_collaboration',
          icon: '💼',
          title: '工作协作',
          description: '探索项目合作机会，发挥各自专业优势'
        }
      ],
      'same_location': [
        {
          id: 'offline_meeting',
          icon: '📍',
          title: '线下会面',
          description: '安排面对面会议，加深彼此了解'
        }
      ],
      'alumni': [
        {
          id: 'alumni_network',
          icon: '🎓',
          title: '校友网络',
          description: '利用校友关系扩展职业网络'
        }
      ],
      'client': [
        {
          id: 'service_enhancement',
          icon: '⭐',
          title: '服务提升',
          description: '持续改进服务质量，维护客户关系'
        }
      ]
    };
    
    return suggestionMap[relationshipType] || [];
  },

  /**
   * 确认关系
   */
  async onConfirmRelationship() {
    const confirmed = await showConfirm('确认关系', '确定要确认这个关系吗？');
    if (!confirmed) return;
    
    try {
      const response = await dataManager.confirmRelationship(this.data.relationshipId);
      
      if (response && response.success) {
        showToast('关系已确认');
        
        // 更新本地数据
        this.setData({
          'relationship.status': 'confirmed',
          'relationship.confirmed_at': new Date().toISOString()
        });
        
        // 重新生成时间线
        this.generateTimeline(this.data.relationship);
        this.generateSuggestions(this.data.relationship);
        
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
  async onIgnoreRelationship() {
    const confirmed = await showConfirm('忽略关系', '确定要忽略这个关系吗？');
    if (!confirmed) return;
    
    try {
      const response = await dataManager.ignoreRelationship(this.data.relationshipId);
      
      if (response && response.success) {
        showToast('关系已忽略');
        
        // 更新本地数据
        this.setData({
          'relationship.status': 'ignored',
          'relationship.ignored_at': new Date().toISOString()
        });
        
        // 重新生成时间线
        this.generateTimeline(this.data.relationship);
        this.generateSuggestions(this.data.relationship);
        
      } else {
        throw new Error(response?.message || '操作失败');
      }
      
    } catch (error) {
      console.error('忽略关系失败:', error);
      showToast('操作失败，请重试');
    }
  },

  /**
   * 建议卡片点击
   */
  onSuggestionTap(e) {
    const { suggestion } = e.currentTarget.dataset;
    console.log('点击建议:', suggestion);
    
    // 根据建议类型执行不同操作
    switch (suggestion.id) {
      case 'update_profiles':
        this.handleUpdateProfiles();
        break;
      case 'maintain_relationship':
        this.handleMaintainRelationship();
        break;
      case 'introduce_contacts':
        this.handleIntroduceContacts();
        break;
      case 'work_collaboration':
        this.handleWorkCollaboration();
        break;
      case 'offline_meeting':
        this.handleOfflineMeeting();
        break;
      default:
        showToast('功能开发中...');
    }
  },

  /**
   * 处理更新联系人信息建议
   */
  handleUpdateProfiles() {
    const { relationship } = this.data;
    wx.showActionSheet({
      itemList: [
        `编辑 ${relationship.sourceName}`,
        `编辑 ${relationship.targetName}`
      ],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 编辑源联系人
          wx.navigateTo({
            url: `/pages/contact-form/contact-form?mode=edit&contactId=${relationship.source_profile_id}`
          });
        } else if (res.tapIndex === 1) {
          // 编辑目标联系人
          wx.navigateTo({
            url: `/pages/contact-form/contact-form?mode=edit&contactId=${relationship.target_profile_id}`
          });
        }
      }
    });
  },

  /**
   * 处理其他建议
   */
  handleMaintainRelationship() {
    showToast('建议已记录，请定期联系');
  },

  handleIntroduceContacts() {
    showToast('牵线搭桥功能开发中');
  },

  handleWorkCollaboration() {
    showToast('工作协作建议已记录');
  },

  handleOfflineMeeting() {
    showToast('已提醒安排线下会面');
  },

  /**
   * 分享
   */
  onShare() {
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    });
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
   * 格式化关系类型
   */
  formatRelationshipType(type) {
    const typeMap = {
      'colleague': '同事',
      'same_location': '同地区',
      'alumni': '校友',
      'same_industry': '同行',
      'investor': '投资人',
      'client': '客户',
      'partner': '合作伙伴',
      'competitor': '竞争对手',
      'friend': '朋友'
    };
    return typeMap[type] || '相关联系人';
  },

  /**
   * 格式化状态
   */
  formatStatus(status) {
    const statusMap = {
      'discovered': '待确认',
      'confirmed': '已确认',
      'ignored': '已忽略'
    };
    return statusMap[status] || status;
  },

  /**
   * 获取关系图标
   */
  getRelationshipIcon(type) {
    const iconMap = {
      'colleague': '💼',
      'same_location': '📍',
      'alumni': '🎓',
      'same_industry': '🏢',
      'investor': '💰',
      'client': '🤝',
      'partner': '🤝',
      'competitor': '⚔️',
      'friend': '👥'
    };
    return iconMap[type] || '🔗';
  },

  /**
   * 获取证据图标
   */
  getEvidenceIcon(field) {
    const iconMap = {
      'company': '🏢',
      'location': '📍',
      'education': '🎓',
      'industry': '💼',
      'position': '👔',
      'phone': '📞',
      'email': '📧'
    };
    return iconMap[field] || '📋';
  },

  /**
   * 获取证据标题
   */
  getEvidenceTitle(field) {
    const titleMap = {
      'company': '公司信息',
      'location': '位置信息',
      'education': '教育背景',
      'industry': '行业领域',
      'position': '职位信息',
      'phone': '电话号码',
      'email': '邮箱地址'
    };
    return titleMap[field] || '相关信息';
  },

  /**
   * 格式化日期
   */
  formatDate,

  /**
   * 格式化日期时间
   */
  formatDateTime
});