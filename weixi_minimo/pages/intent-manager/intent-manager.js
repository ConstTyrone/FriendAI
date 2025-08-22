// 意图管理页面
import { UI_CONFIG, PAGE_ROUTES } from '../../utils/constants';
import authManager from '../../utils/auth-manager';
import apiClient from '../../utils/api-client';
import themeManager from '../../utils/theme-manager';

Page({
  data: {
    // 意图列表
    intents: [],
    loading: false,
    refreshing: false,
    
    // 统计数据
    stats: {
      activeCount: 0,
      totalMatches: 0,
      todayPush: 0
    },
    
    // 创建/编辑对话框
    showCreateDialog: false,
    createMode: 'natural', // natural | template | advanced
    editMode: false, // 是否为编辑模式
    editingIntentId: null, // 正在编辑的意图ID
    
    // 表单数据
    formData: {
      name: '',
      description: '',
      type: 'business',
      conditions: {
        required: [],
        preferred: [],
        keywords: []
      },
      threshold: 70,
      priority: 5,
      maxPushPerDay: 5
    },
    
    // 类型选择索引
    typeIndex: 0,
    
    // 意图模板
    templates: [
      {
        name: '寻找投资人',
        description: '寻找关注特定领域的投资人',
        template: '寻找在{行业}领域有投资经验的{阶段}投资人',
        conditions: {
          keywords: ['投资', '融资', 'VC', '天使']
        }
      },
      {
        name: '招聘人才',
        description: '招募特定岗位的优秀人才',
        template: '招聘{职位}，要求有{技能}经验，{学历}以上',
        conditions: {
          keywords: ['招聘', '人才', '经验']
        }
      },
      {
        name: '寻找客户',
        description: '发现潜在的商业客户',
        template: '寻找{行业}的{职位}决策者，有{需求}',
        conditions: {
          keywords: ['客户', '采购', '决策']
        }
      },
      {
        name: '找合作伙伴',
        description: '寻找业务合作伙伴',
        template: '寻找能提供{服务}的{类型}合作伙伴',
        conditions: {
          keywords: ['合作', '伙伴', '资源']
        }
      },
      {
        name: '技术交流',
        description: '寻找技术领域的专家',
        template: '寻找精通{技术}的{级别}工程师',
        conditions: {
          keywords: ['技术', '开发', '工程师']
        }
      }
    ],
    
    // 选项数据
    priorityOptions: ['低', '较低', '中等', '较高', '高', '紧急'],
    typeOptions: [
      { value: 'business', label: '商务' },
      { value: 'recruitment', label: '招聘' },
      { value: 'social', label: '社交' },
      { value: 'resource', label: '资源' }
    ],
    
    // 重新匹配提示
    showMatchingHint: false,
    matchingHintText: ''
  },

  onLoad() {
    console.log('意图管理页面加载');
    
    // 应用主题
    themeManager.applyToPage(this);
    
    // 检查登录状态
    if (!authManager.isLoggedIn()) {
      wx.showModal({
        title: '需要登录',
        content: '请先登录后使用意图匹配功能',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    }
    
    // 加载意图列表
    this.loadIntents();
    this.loadStats();
  },

  onShow() {
    // 页面显示时刷新数据
    if (this.data.intents.length > 0) {
      this.loadIntents();
    }
  },

  /**
   * 加载意图列表
   */
  async loadIntents() {
    if (this.data.loading) return;
    
    this.setData({ loading: true });
    
    try {
      const response = await apiClient.request({
        url: '/api/intents',
        method: 'GET',
        data: {
          status: 'active',
          page: 1,
          size: 100
        }
      });
      
      if (response.success) {
        const intents = response.data.intents.map(intent => ({
          ...intent,
          typeLabel: this.getTypeLabel(intent.type),
          priorityLabel: this.data.priorityOptions[intent.priority - 1] || '中等',
          thresholdPercent: Math.round((intent.threshold || 0.7) * 100),
          keywordsList: this.extractKeywords(intent.conditions),
          match_count: intent.match_count || 0,  // 确保有默认值
          // AI功能可视化
          isAIMatch: this.isAIEnhanced(intent),
          aiFeatures: this.getAIFeatures(intent)
        }));
        
        // 计算总匹配数
        const totalMatches = intents.reduce((sum, intent) => sum + (intent.match_count || 0), 0);
        
        this.setData({
          intents,
          'stats.activeCount': intents.length,
          'stats.totalMatches': totalMatches
        });
      }
    } catch (error) {
      console.error('加载意图列表失败:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  /**
   * 加载统计数据
   */
  async loadStats() {
    try {
      // TODO: 从后端获取统计数据
      // 暂时使用模拟数据
      this.setData({
        stats: {
          activeCount: this.data.intents.length,
          totalMatches: 0,
          todayPush: 0
        }
      });
    } catch (error) {
      console.error('加载统计数据失败:', error);
    }
  },

  /**
   * 显示创建对话框
   */
  showCreateDialog() {
    console.log('显示创建对话框');
    
    this.setData({
      showCreateDialog: true,
      createMode: 'natural',
      typeIndex: 0,
      editMode: false,
      editingIntentId: null,
      formData: {
        name: '',
        description: '',
        type: 'general',
        conditions: {
          required: [],
          preferred: [],
          keywords: []
        },
        threshold: 70,
        priority: 5,
        maxPushPerDay: 5
      }
    });
  },

  /**
   * 隐藏创建对话框
   */
  hideCreateDialog() {
    console.log('隐藏创建对话框');
    
    this.setData({
      showCreateDialog: false,
      editMode: false,
      editingIntentId: null,
      formData: {
        name: '',
        description: '',
        type: 'general',
        conditions: {
          required: [],
          preferred: [],
          keywords: []
        },
        threshold: 70,
        priority: 5,
        maxPushPerDay: 5
      }
    });
  },

  /**
   * 切换创建模式
   */
  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({
      createMode: mode
    });
  },

  /**
   * 选择模板
   */
  selectTemplate(e) {
    const index = e.currentTarget.dataset.index;
    const template = this.data.templates[index];
    
    this.setData({
      'formData.name': template.name,
      'formData.description': template.template,
      'formData.conditions.keywords': template.conditions.keywords || [],
      createMode: 'natural'
    });
    
    wx.showToast({
      title: '已选择模板',
      icon: 'success'
    });
  },

  /**
   * 输入变化
   */
  onInputChange(e) {
    const field = e.currentTarget.dataset.field;
    let value = e.detail.value;
    
    // 处理数字类型字段
    if (field === 'maxPushPerDay') {
      value = parseInt(value) || 5;
      if (value < 1) value = 1;
      if (value > 20) value = 20;
    }
    
    this.setData({
      [`formData.${field}`]: value
    });
  },

  /**
   * 阈值变化（拖动过程中实时更新）
   */
  onThresholdInput(e) {
    const threshold = Math.round(Number(e.detail.value));
    console.log('Threshold input:', threshold, 'Original value:', e.detail.value);
    this.setData({
      'formData.threshold': threshold
    });
  },

  /**
   * 阈值变化完成
   */
  onThresholdChange(e) {
    const threshold = parseInt(e.detail.value);
    console.log('Threshold change:', threshold);
    this.setData({
      'formData.threshold': threshold
    });
  },

  /**
   * 优先级变化
   */
  onPriorityChange(e) {
    this.setData({
      'formData.priority': parseInt(e.detail.value) + 1
    });
  },

  /**
   * 类型变化
   */
  onTypeChange(e) {
    const index = parseInt(e.detail.value);
    this.setData({
      typeIndex: index,
      'formData.type': this.data.typeOptions[index].value
    });
  },

  /**
   * 保存意图（创建或编辑）
   */
  async saveIntent() {
    const { formData, editMode, editingIntentId } = this.data;
    
    // 验证必填字段
    if (!formData.name || !formData.name.trim()) {
      wx.showToast({
        title: '请输入意图名称',
        icon: 'none'
      });
      return;
    }
    
    if (!formData.description || !formData.description.trim()) {
      wx.showToast({
        title: '请描述你的意图',
        icon: 'none'
      });
      return;
    }
    
    wx.showLoading({
      title: editMode ? '保存中...' : '创建中...',
      mask: true  // 防止用户重复点击
    });
    
    try {
      // 处理关键词
      if (formData.description && this.data.createMode === 'natural') {
        formData.conditions.keywords = this.extractKeywordsFromText(formData.description);
      }
      
      // 准备请求数据
      const requestData = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        type: formData.type,
        conditions: formData.conditions,
        threshold: formData.threshold / 100,
        priority: formData.priority,
        max_push_per_day: formData.maxPushPerDay
      };
      
      // 根据模式选择API
      let response;
      if (editMode) {
        // 编辑模式：更新意图
        response = await apiClient.request({
          url: `/api/intents/${editingIntentId}`,
          method: 'PUT',
          data: requestData
        });
      } else {
        // 创建模式：新建意图
        response = await apiClient.request({
          url: '/api/intents',
          method: 'POST',
          data: requestData
        });
      }
      
      if (response.success) {
        wx.hideLoading();
        
        // 处理编辑模式下的重新匹配提示
        if (editMode && response.data) {
          const { need_rematch, need_threshold_reeval } = response.data;
          
          if (need_rematch) {
            // 显示保存成功提示
            wx.showToast({
              title: '保存成功',
              icon: 'success',
              duration: 1500
            });
            
            // 显示重新匹配进度提示
            setTimeout(() => {
              this.setData({
                showMatchingHint: true,
                matchingHintText: '正在根据新的条件重新匹配联系人...'
              });
              
              // 5秒后隐藏提示并刷新列表
              setTimeout(() => {
                this.setData({ showMatchingHint: false });
                this.loadIntents();
              }, 5000);
            }, 1600);
            
          } else if (need_threshold_reeval) {
            // 显示保存成功提示
            wx.showToast({
              title: '保存成功',
              icon: 'success',
              duration: 1500
            });
            
            // 显示阈值重新评估提示
            setTimeout(() => {
              this.setData({
                showMatchingHint: true,
                matchingHintText: '正在根据新阈值更新匹配结果...'
              });
              
              // 3秒后隐藏提示并刷新列表
              setTimeout(() => {
                this.setData({ showMatchingHint: false });
                this.loadIntents();
              }, 3000);
            }, 1600);
            
          } else {
            // 只修改了不影响匹配的字段
            wx.showToast({
              title: '保存成功',
              icon: 'success'
            });
            this.loadIntents();
          }
        } else {
          // 创建模式
          wx.showToast({
            title: '创建成功',
            icon: 'success'
          });
          this.loadIntents();
          
          // 创建模式下显示匹配分析提示
          if (response.data && response.data.intentId) {
            setTimeout(() => {
              this.setData({
                showMatchingHint: true,
                matchingHintText: '正在为您匹配符合条件的联系人...'
              });
              
              // 触发匹配
              this.triggerMatch(response.data.intentId);
              
              // 5秒后隐藏提示
              setTimeout(() => {
                this.setData({ showMatchingHint: false });
                this.loadIntents();
              }, 5000);
            }, 1500);
          }
        }
        
        // 隐藏对话框
        this.hideCreateDialog();
      } else {
        wx.hideLoading();
        wx.showToast({
          title: response.message || (editMode ? '保存失败' : '创建失败'),
          icon: 'none',
          duration: 2000
        });
      }
    } catch (error) {
      console.error(editMode ? '保存意图失败:' : '创建意图失败:', error);
      wx.hideLoading();
      wx.showToast({
        title: error.message || (editMode ? '保存失败' : '创建失败'),
        icon: 'error'
      });
    }
  },

  /**
   * 触发匹配
   */
  async triggerMatch(intentId) {
    try {
      await apiClient.request({
        url: `/api/intents/${intentId}/match`,
        method: 'POST',
        timeout: 60000  // AI匹配需要更长时间
      });
      
      console.log('匹配分析已触发');
    } catch (error) {
      console.error('触发匹配失败:', error);
    }
  },

  /**
   * 切换意图状态
   */
  async toggleIntent(e) {
    const intentId = e.currentTarget.dataset.id;
    const checked = e.detail.value;
    const status = checked ? 'active' : 'paused';
    
    try {
      await apiClient.request({
        url: `/api/intents/${intentId}`,
        method: 'PUT',
        data: { status }
      });
      
      wx.showToast({
        title: checked ? '已启用' : '已暂停',
        icon: 'success'
      });
      
      // 更新本地状态
      const intents = this.data.intents.map(intent => {
        if (intent.id === intentId) {
          intent.status = status;
        }
        return intent;
      });
      
      this.setData({ intents });
    } catch (error) {
      console.error('更新状态失败:', error);
      wx.showToast({
        title: '操作失败',
        icon: 'error'
      });
    }
  },

  /**
   * 查看匹配结果
   */
  viewMatches(e) {
    const intentId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/matches/matches?intentId=${intentId}`
    });
  },

  /**
   * 编辑意图
   */
  editIntent(e) {
    const intentId = e.currentTarget.dataset.id;
    
    // 找到要编辑的意图
    const intent = this.data.intents.find(item => item.id === intentId);
    if (!intent) {
      wx.showToast({
        title: '意图不存在',
        icon: 'error'
      });
      return;
    }
    
    // 保存原始数据用于对比
    const originalData = {
      name: intent.name || '',
      description: intent.description || '',
      type: intent.type || 'general',
      conditions: JSON.parse(JSON.stringify(intent.conditions || {
        required: [],
        preferred: [],
        keywords: []
      })),
      threshold: Math.round((intent.threshold || 0.7) * 100),
      priority: intent.priority || 5,
      maxPushPerDay: intent.max_push_per_day || 5
    };
    
    // 设置编辑模式和填充表单数据
    this.setData({
      editMode: true,
      editingIntentId: intentId,
      showCreateDialog: true,
      createMode: 'natural', // 默认使用自然语言模式
      originalFormData: originalData, // 保存原始数据
      formData: {
        name: intent.name || '',
        description: intent.description || '',
        type: intent.type || 'general',
        conditions: intent.conditions || {
          required: [],
          preferred: [],
          keywords: []
        },
        threshold: Math.round((intent.threshold || 0.7) * 100), // 转换为百分比
        priority: intent.priority || 5,
        maxPushPerDay: intent.max_push_per_day || 5
      }
    });
    
    // 设置类型选择索引
    const typeIndex = this.data.typeOptions.findIndex(opt => opt.value === intent.type);
    this.setData({ typeIndex: typeIndex >= 0 ? typeIndex : 0 });
  },

  /**
   * 删除意图
   */
  deleteIntent(e) {
    const intentId = e.currentTarget.dataset.id;
    const intent = this.data.intents.find(i => i.id === intentId);
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除意图"${intent.name}"吗？`,
      confirmColor: '#FF3B30',
      success: async (res) => {
        if (res.confirm) {
          try {
            await apiClient.request({
              url: `/api/intents/${intentId}`,
              method: 'DELETE'
            });
            
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            });
            
            // 从列表中移除
            const intents = this.data.intents.filter(i => i.id !== intentId);
            this.setData({ intents });
          } catch (error) {
            console.error('删除失败:', error);
            wx.showToast({
              title: '删除失败',
              icon: 'error'
            });
          }
        }
      }
    });
  },

  /**
   * 获取类型标签
   */
  getTypeLabel(type) {
    const typeMap = {
      'general': '通用',
      'business': '商务',
      'recruitment': '招聘',
      'social': '社交',
      'resource': '资源'
    };
    return typeMap[type] || '通用';
  },

  /**
   * 提取关键词
   */
  extractKeywords(conditions) {
    if (!conditions) return [];
    
    const keywords = conditions.keywords || [];
    
    // 从必要条件中提取
    if (conditions.required) {
      conditions.required.forEach(cond => {
        if (cond.value && typeof cond.value === 'string') {
          keywords.push(cond.value);
        }
      });
    }
    
    return [...new Set(keywords)].slice(0, 5);
  },

  /**
   * 从文本中提取关键词
   */
  extractKeywordsFromText(text) {
    // 简单的关键词提取逻辑
    const keywords = [];
    const patterns = [
      /寻找(.+?)的/g,
      /需要(.+?)$/g,
      /招聘(.+?)$/g,
      /(.+?)经验/g,
      /(.+?)背景/g
    ];
    
    patterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) {
        matches.forEach(match => {
          const word = match.replace(pattern, '$1').trim();
          if (word && word.length > 1 && word.length < 10) {
            keywords.push(word);
          }
        });
      }
    });
    
    // 添加一些关键词
    const importantWords = ['AI', '投资', '创业', 'CTO', '技术', '管理', '销售', '市场'];
    importantWords.forEach(word => {
      if (text.includes(word)) {
        keywords.push(word);
      }
    });
    
    return [...new Set(keywords)].slice(0, 10);
  },

  /**
   * 判断AI增强功能
   */
  isAIEnhanced(intent) {
    // 检查意图是否使用了AI功能
    return !!(intent.embedding || intent.vector_enabled || 
              (intent.conditions && intent.conditions.ai_keywords) ||
              intent.match_type === 'hybrid' || intent.match_type === 'vector');
  },

  /**
   * 获取AI功能特性
   */
  getAIFeatures(intent) {
    const features = [];
    
    if (intent.embedding) {
      features.push('语义向量');
    }
    
    if (intent.match_type === 'hybrid') {
      features.push('混合匹配');
    }
    
    if (intent.match_type === 'vector') {
      features.push('向量匹配');
    }
    
    if (intent.conditions && intent.conditions.ai_keywords) {
      features.push('智能关键词');
    }
    
    return features;
  },

  /**
   * 下拉刷新
   */
  async onPullDownRefresh() {
    this.setData({ refreshing: true });
    
    await Promise.all([
      this.loadIntents(),
      this.loadStats()
    ]);
    
    wx.stopPullDownRefresh();
    this.setData({ refreshing: false });
  },

  /**
   * 停止事件冒泡
   */
  stopPropagation(e) {
    console.log('阻止事件冒泡');
    // 不做任何操作，只是阻止冒泡到父元素
  }
});