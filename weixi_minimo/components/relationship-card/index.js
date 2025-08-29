// 关系卡片组件
import themeManager from '../../utils/theme-manager';

Component({
  /**
   * 组件属性列表
   */
  properties: {
    // 关系数据
    relationship: {
      type: Object,
      value: {}
    },
    // 源联系人数据
    sourceProfile: {
      type: Object,
      value: {}
    },
    // 目标联系人数据
    targetProfile: {
      type: Object,
      value: {}
    },
    // 是否显示证据
    showEvidence: {
      type: Boolean,
      value: true
    },
    // 是否显示操作按钮
    showActions: {
      type: Boolean,
      value: true
    }
  },

  /**
   * 组件数据
   */
  data: {
    themeClass: '',
    sourceInitial: '',
    targetInitial: '',
    confidencePercentage: 0
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this.initTheme();
    },
    
    ready() {
      // 组件准备就绪时处理初始数据
      this.processProfiles();
    },
    
    detached() {
      if (this.themeListener) {
        themeManager.removeListener(this.themeListener);
      }
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 初始化主题
     */
    initTheme() {
      const theme = themeManager.getCurrentTheme();
      this.setData({
        themeClass: theme === 'dark' ? 'dark' : ''
      });

      // 监听主题变化
      this.themeListener = (newTheme) => {
        this.setData({
          themeClass: newTheme === 'dark' ? 'dark' : ''
        });
      };
      themeManager.addListener(this.themeListener);
    },

    /**
     * 处理联系人数据
     */
    processProfiles() {
      const { relationship, sourceProfile, targetProfile } = this.properties;
      console.log('processProfiles被调用:', { sourceProfile, targetProfile });
      
      // 调试：检查relationship数据
      console.log('=== relationship-card 组件调试 ===');
      console.log('传入的 relationship:', JSON.stringify(relationship, null, 2));
      console.log('relationship.confidence_score:', relationship?.confidence_score);
      
      // 使用内部data而不是直接修改properties
      const updateData = {};
      
      // 预计算置信度百分比
      if (relationship && relationship.confidence_score !== undefined) {
        updateData.confidencePercentage = Math.round(relationship.confidence_score * 100);
        console.log('预计算置信度:', relationship.confidence_score, '→', updateData.confidencePercentage);
      }
      
      if (sourceProfile && sourceProfile.profile_name && !sourceProfile.initial) {
        const sourceInitial = this.generateInitial(sourceProfile.profile_name);
        console.log('生成源联系人首字母（ready）:', { name: sourceProfile.profile_name, initial: sourceInitial });
        updateData.sourceInitial = sourceInitial;
      }
      
      if (targetProfile && targetProfile.profile_name && !targetProfile.initial) {
        const targetInitial = this.generateInitial(targetProfile.profile_name);
        console.log('生成目标联系人首字母（ready）:', { name: targetProfile.profile_name, initial: targetInitial });
        updateData.targetInitial = targetInitial;
      }
      
      if (Object.keys(updateData).length > 0) {
        this.setData(updateData);
      }
    },

    /**
     * 格式化关系类型
     */
    formatRelationshipType(type) {
      const typeMap = {
        'colleague': '同事',
        'same_location': '同地区',
        'alumni': '校友',
        'same_industry': '同行业',
        'investor': '投资人',
        'client': '客户',
        'partner': '合作伙伴',
        'competitor': '竞争对手',
        'friend': '朋友',
        'classmate': '同学',
        'neighbor': '邻居'
      };
      return typeMap[type] || '相关联系人';
    },

    /**
     * 获取关系图标
     */
    getRelationshipIcon(type) {
      const iconMap = {
        'colleague': '🤝',
        'same_location': '📍',
        'alumni': '🎓',
        'same_industry': '🏢',
        'investor': '💰',
        'client': '🛒',
        'partner': '🤝',
        'competitor': '⚔️',
        'friend': '👥',
        'classmate': '📚',
        'neighbor': '🏠'
      };
      return iconMap[type] || '🔗';
    },

    /**
     * 获取关系描述
     */
    getRelationshipDescription(type) {
      const descMap = {
        'colleague': '在同一公司工作',
        'same_location': '在同一地区',
        'alumni': '来自同一学校',
        'same_industry': '在同一行业',
        'investor': '投资关系',
        'client': '客户关系',
        'partner': '合作伙伴关系',
        'competitor': '竞争对手关系',
        'friend': '朋友关系',
        'classmate': '同学关系',
        'neighbor': '邻居关系'
      };
      return descMap[type] || '存在关联';
    },

    /**
     * 格式化关系方向
     */
    formatDirection(direction) {
      const directionMap = {
        'source_to_target': '单向关系',
        'target_to_source': '反向关系',
        'bidirectional': '双向关系'
      };
      return directionMap[direction] || '双向关系';
    },

    /**
     * 格式化关系状态
     */
    formatStatus(status) {
      const statusMap = {
        'discovered': '待确认',
        'confirmed': '已确认',
        'ignored': '已忽略',
        'deleted': '已删除'
      };
      return statusMap[status] || '未知';
    },

    /**
     * 格式化证据信息
     */
    formatEvidence(evidence) {
      if (!evidence || typeof evidence !== 'object') {
        return '暂无详细信息';
      }

      const evidenceTexts = [];
      
      if (evidence.match_type === 'exact') {
        evidenceTexts.push('精确匹配');
      } else if (evidence.match_type === 'fuzzy') {
        evidenceTexts.push(`模糊匹配 (${Math.round((evidence.similarity || 0) * 100)}% 相似度)`);
      } else if (evidence.match_type === 'contains') {
        evidenceTexts.push('包含匹配');
      }

      if (evidence.matched_values) {
        evidenceTexts.push(evidence.matched_values);
      }

      return evidenceTexts.join(' · ') || '系统自动识别';
    },

    /**
     * 格式化发现时间
     */
    formatDiscoveryTime(timestamp) {
      if (!timestamp) return '未知时间';
      
      const now = new Date();
      const discoveryTime = new Date(timestamp);
      const diffMs = now - discoveryTime;
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) {
        return '刚刚发现';
      } else if (diffMins < 60) {
        return `${diffMins}分钟前发现`;
      } else if (diffHours < 24) {
        return `${diffHours}小时前发现`;
      } else if (diffDays < 30) {
        return `${diffDays}天前发现`;
      } else {
        return discoveryTime.toLocaleDateString('zh-CN');
      }
    },

    /**
     * 点击卡片
     */
    onCardTap(e) {
      this.triggerEvent('cardTap', {
        relationship: this.data.relationship,
        sourceProfile: this.data.sourceProfile,
        targetProfile: this.data.targetProfile
      });
    },

    /**
     * 确认关系
     */
    onConfirm(e) {
      this.triggerEvent('confirm', {
        relationshipId: this.data.relationship.id,
        relationship: this.data.relationship
      });
    },

    /**
     * 忽略关系
     */
    onIgnore(e) {
      this.triggerEvent('ignore', {
        relationshipId: this.data.relationship.id,
        relationship: this.data.relationship
      });
    },

    /**
     * 阻止事件冒泡
     */
    stopPropagation(e) {
      // 阻止事件冒泡
    },

    /**
     * 格式化置信度（返回数字，不包含百分号）
     */
    formatConfidence(confidence) {
      console.log('formatConfidence调用:', confidence, '结果:', Math.round((confidence || 0) * 100));
      return Math.round((confidence || 0) * 100);
    },

    /**
     * 生成联系人姓名首字母
     */
    generateInitial(name) {
      if (!name) return '?';
      
      const firstChar = name.charAt(0);
      // 如果是中文，直接返回第一个字符
      if (/[\u4e00-\u9fa5]/.test(firstChar)) {
        return firstChar;
      } 
      // 如果是英文，返回大写首字母
      else if (/[a-zA-Z]/.test(firstChar)) {
        return firstChar.toUpperCase();
      }
      // 其他情况返回第一个字符
      else {
        return firstChar;
      }
    }
  },

  /**
   * 数据监听器
   */
  observers: {
    'sourceProfile.profile_name': function(profileName) {
      if (profileName && !this.data.sourceInitial) {
        const sourceInitial = this.generateInitial(profileName);
        console.log('生成源联系人首字母:', { profileName, sourceInitial });
        this.setData({
          sourceInitial: sourceInitial
        });
      }
    },
    
    'targetProfile.profile_name': function(profileName) {
      if (profileName && !this.data.targetInitial) {
        const targetInitial = this.generateInitial(profileName);
        console.log('生成目标联系人首字母:', { profileName, targetInitial });
        this.setData({
          targetInitial: targetInitial
        });
      }
    }
  }
});