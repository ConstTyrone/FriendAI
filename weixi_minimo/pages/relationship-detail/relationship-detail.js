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
        const relationship = response.relationship;
        
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
    // 数据验证
    if (!rawRelationship) {
      console.error('关系数据为空');
      return;
    }
    
    // 提取联系人信息，添加防护措施
    const sourceProfile = rawRelationship.sourceProfile || rawRelationship.source_profile || {};
    const targetProfile = rawRelationship.targetProfile || rawRelationship.target_profile || {};
    
    const sourceName = sourceProfile.profile_name || sourceProfile.name || rawRelationship.source_profile_name || '联系人';
    const targetName = targetProfile.profile_name || targetProfile.name || rawRelationship.target_profile_name || '联系人';
    const sourceCompany = sourceProfile.company || '';
    const targetCompany = targetProfile.company || '';
    
    // 生成首字母
    const sourceInitial = this.getNameInitial(sourceName);
    const targetInitial = this.getNameInitial(targetName);
    
    // 处理证据数据（传入关系数据用于生成默认证据）
    const evidenceList = this.processEvidence(rawRelationship.evidence, rawRelationship);
    
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
  processEvidence(evidence, relationship) {
    const evidenceList = [];
    
    // 如果有具体的证据数据，使用实际数据
    if (evidence && typeof evidence === 'object') {
      const { matched_fields = [], field_scores = {}, details = {} } = evidence;
      
      matched_fields.forEach(field => {
        evidenceList.push({
          field,
          match_score: Math.round((field_scores[field] || 0.5) * 100),
          source_value: details[`${field}_source`] || '未知',
          target_value: details[`${field}_target`] || '未知'
        });
      });
      
      if (evidenceList.length > 0) {
        return evidenceList;
      }
    }
    
    // 如果没有具体证据，根据关系类型生成默认证据
    if (relationship) {
      return this.generateDefaultEvidence(relationship);
    }
    
    return [];
  },
  
  /**
   * 生成默认证据数据
   */
  generateDefaultEvidence(relationship) {
    const defaultEvidence = [];
    const relationshipType = relationship.relationship_type || 'unknown';
    
    // 根据关系类型生成相应的证据字段
    switch (relationshipType) {
      case 'colleague':
        defaultEvidence.push({
          field: 'company',
          match_score: Math.round((relationship.confidence_score || 0.7) * 100),
          source_value: relationship.sourceCompany || '工作单位',
          target_value: relationship.targetCompany || '工作单位'
        });
        if (relationship.sourceCompany && relationship.targetCompany) {
          defaultEvidence.push({
            field: 'position',
            match_score: Math.round(((relationship.confidence_score || 0.7) * 0.8) * 100),
            source_value: '相关职位',
            target_value: '相关职位'
          });
        }
        break;
        
      case 'same_location':
        defaultEvidence.push({
          field: 'location',
          match_score: Math.round((relationship.confidence_score || 0.6) * 100),
          source_value: '相近地区',
          target_value: '相近地区'
        });
        break;
        
      case 'alumni':
        defaultEvidence.push({
          field: 'education',
          match_score: Math.round((relationship.confidence_score || 0.8) * 100),
          source_value: '相同院校',
          target_value: '相同院校'
        });
        break;
        
      case 'same_industry':
        defaultEvidence.push({
          field: 'industry',
          match_score: Math.round((relationship.confidence_score || 0.7) * 100),
          source_value: '行业领域',
          target_value: '行业领域'
        });
        break;
        
      default:
        // 通用证据
        defaultEvidence.push({
          field: 'company',
          match_score: Math.round((relationship.confidence_score || 0.5) * 100),
          source_value: '系统分析',
          target_value: '相关信息'
        });
        break;
    }
    
    return defaultEvidence;
  },

  /**
   * 生成更具体的AI分析
   */
  generateDefaultAnalysis(relationship) {
    const sourceName = relationship.sourceName || '联系人A';
    const targetName = relationship.targetName || '联系人B';
    const sourceCompany = relationship.sourceCompany || '';
    const targetCompany = relationship.targetCompany || '';
    const confidenceScore = relationship.confidence_score || 0.5;
    const relationshipType = relationship.relationship_type || 'unknown';
    
    let analysis = '';
    let actionableAdvice = '';
    
    // 根据关系类型生成具体分析
    switch (relationshipType) {
      case 'colleague':
        analysis = `${sourceName}和${targetName}存在同事关系`;
        if (sourceCompany && targetCompany && sourceCompany === targetCompany) {
          analysis += `，均在${sourceCompany}工作`;
          actionableAdvice = `建议利用这一同事关系开展内部项目协作，可以考虑：1）在公司项目中互相支持；2）分享工作经验和专业技能；3）建立长期的职业发展联系。`;
        } else if (sourceCompany && targetCompany) {
          analysis += `，分别在${sourceCompany}和${targetCompany}工作`;
          actionableAdvice = `建议探索跨公司的合作机会：1）分享行业见解和最佳实践；2）探讨潜在的商业合作；3）建立更广泛的职业网络。`;
        } else {
          actionableAdvice = `同事关系为双方提供了良好的合作基础，建议保持定期的工作交流。`;
        }
        break;
        
      case 'same_location':
        analysis = `${sourceName}和${targetName}地理位置相近`;
        if (confidenceScore > 0.7) {
          analysis += `，匹配度较高(${Math.round(confidenceScore * 100)}%)`;
          actionableAdvice = `地理优势明显，建议：1）安排线下会面以深化关系；2）参加本地行业活动增进了解；3）考虑本地化的商业合作机会。`;
        } else {
          actionableAdvice = `可以考虑线下见面的机会，但建议先确认具体的地理位置信息。`;
        }
        break;
        
      case 'alumni':
        analysis = `${sourceName}和${targetName}具有校友关系`;
        actionableAdvice = `校友网络具有天然的信任基础，建议：1）回忆共同的学校经历建立话题；2）参加校友活动增强联系；3）在职业发展上互相支持和推荐。这种关系通常具有较强的持续性和互助性。`;
        break;
        
      case 'same_industry':
        analysis = `${sourceName}和${targetName}属于相同行业领域`;
        if (sourceCompany && targetCompany) {
          analysis += `，分别在${sourceCompany}和${targetCompany}从事相关工作`;
        }
        actionableAdvice = `同行业关系价值巨大，建议：1）定期分享行业趋势和市场洞察；2）探讨技术创新和业务模式；3）考虑在非竞争领域的战略合作；4）参加行业会议时保持联系。`;
        break;
        
      case 'client':
        analysis = `${sourceName}和${targetName}存在客户服务关系`;
        actionableAdvice = `客户关系需要精心维护，建议：1）定期跟进客户需求和满意度；2）提供增值服务以强化合作；3）保持专业沟通增进信任；4）探索长期合作的可能性。`;
        break;
        
      case 'partner':
        analysis = `${sourceName}和${targetName}为合作伙伴关系`;
        actionableAdvice = `合作伙伴关系需要持续投入，建议：1）建立定期的沟通机制；2）明确双方的合作目标和期望；3）探索更深层次的战略合作；4）在困难时互相支持。`;
        break;
        
      default:
        analysis = `${sourceName}和${targetName}之间发现了潜在的社交关系`;
        if (confidenceScore > 0.7) {
          analysis += `，系统匹配度较高`;
          actionableAdvice = `虽然关系类型待进一步确认，但高匹配度表明两人可能有重要联系。建议：1）主动了解对方的背景和兴趣；2）寻找共同话题和连接点；3）在合适时机深入交流。`;
        } else {
          actionableAdvice = `建议进一步核实和了解这一关系的具体性质，可以通过共同朋友或直接交流来确认。`;
        }
        break;
    }
    
    // 添加可信度相关的建议
    if (confidenceScore < 0.5) {
      actionableAdvice += `\n\n注意：当前关系匹配度较低(${Math.round(confidenceScore * 100)}%)，建议谨慎判断并通过多种渠道验证关系的真实性。`;
    } else if (confidenceScore > 0.8) {
      actionableAdvice += `\n\n系统对这一关系有很高的信心度(${Math.round(confidenceScore * 100)}%)，可以积极推进相关的联系计划。`;
    }
    
    return `${analysis}。\n\n${actionableAdvice}`;
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