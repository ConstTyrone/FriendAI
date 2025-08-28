// 关系发现提示组件
import themeManager from '../../utils/theme-manager';

Component({
  /**
   * 组件属性列表
   */
  properties: {
    // 关系数据列表
    relationships: {
      type: Array,
      value: []
    },
    // 是否显示组件
    visible: {
      type: Boolean,
      value: false
    },
    // 是否显示预览
    showPreview: {
      type: Boolean,
      value: true
    },
    // 是否显示快速操作
    showActions: {
      type: Boolean,
      value: true
    },
    // 最大预览数量
    maxPreview: {
      type: Number,
      value: 3
    }
  },

  /**
   * 组件数据
   */
  data: {
    themeClass: ''
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this.initTheme();
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
     * 格式化关系类型摘要
     */
    formatRelationshipTypes(relationships) {
      if (!relationships || relationships.length === 0) {
        return '';
      }

      const typeMap = new Map();
      relationships.forEach(rel => {
        const type = this.formatRelationshipType(rel.relationship_type);
        const count = typeMap.get(type) || 0;
        typeMap.set(type, count + 1);
      });

      const types = [];
      for (const [type, count] of typeMap) {
        if (count > 1) {
          types.push(`${count}个${type}`);
        } else {
          types.push(type);
        }
      }

      return types.slice(0, 2).join('、') + (types.length > 2 ? '等' : '');
    },

    /**
     * 格式化单个关系类型
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
     * 获取其他联系人的首字母
     */
    getOtherProfileInitial(relationship, currentProfileId) {
      const isSource = relationship.source_profile_id === currentProfileId;
      const otherName = isSource ? 
        relationship.target_profile_name : 
        relationship.source_profile_name;
      
      if (!otherName) return '?';
      
      // 提取中文或英文首字母
      const firstChar = otherName.charAt(0);
      if (/[\u4e00-\u9fa5]/.test(firstChar)) {
        return firstChar;
      } else {
        return firstChar.toUpperCase();
      }
    },

    /**
     * 获取其他联系人姓名
     */
    getOtherProfileName(relationship, currentProfileId) {
      const isSource = relationship.source_profile_id === currentProfileId;
      return isSource ? 
        relationship.target_profile_name : 
        relationship.source_profile_name;
    },

    /**
     * 查看详情
     */
    onViewDetails(e) {
      this.triggerEvent('viewDetails', {
        relationships: this.data.relationships
      });
    },

    /**
     * 全部确认
     */
    onConfirmAll(e) {
      this.triggerEvent('confirmAll', {
        relationships: this.data.relationships
      });
    },

    /**
     * 全部忽略
     */
    onIgnoreAll(e) {
      this.triggerEvent('ignoreAll', {
        relationships: this.data.relationships
      });
    },

    /**
     * 关闭提示
     */
    onClose(e) {
      this.triggerEvent('close');
    },

    /**
     * 阻止事件冒泡
     */
    stopPropagation(e) {
      // 阻止事件冒泡
    }
  },

  /**
   * 数据监听器
   */
  observers: {
    'relationships': function(relationships) {
      if (!relationships || relationships.length === 0) {
        return;
      }

      // 处理预览数据
      const previewRelationships = relationships.slice(0, this.data.maxPreview).map(rel => {
        const currentProfileId = rel.source_profile_id; // 假设当前是source
        return {
          id: rel.id,
          relationship_type: rel.relationship_type,
          confidence_score: rel.confidence_score,
          otherProfileName: this.getOtherProfileName(rel, currentProfileId),
          otherProfileInitial: this.getOtherProfileInitial(rel, currentProfileId)
        };
      });

      this.setData({
        previewRelationships: previewRelationships
      });
    }
  }
});