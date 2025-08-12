import { formatRelativeTime } from '../../utils/format-utils';

Component({
  options: {
    multipleSlots: true,
    addGlobalClass: true
  },

  properties: {
    // 联系人数据
    contact: {
      type: Object,
      value: {}
    },
    
    // 搜索关键词（用于高亮显示）
    searchKeyword: {
      type: String,
      value: ''
    },
    
    // 是否显示摘要
    showSummary: {
      type: Boolean,
      value: false
    },
    
    // 是否显示操作按钮
    showActions: {
      type: Boolean,
      value: false
    },
    
    // 是否高亮显示
    highlight: {
      type: Boolean,
      value: false
    },
    
    // 是否骨架加载态
    skeleton: {
      type: Boolean,
      value: false
    }
  },

  data: {
    
  },

  methods: {
    /**
     * 卡片点击事件
     */
    onCardTap(event) {
      if (this.data.skeleton) return;
      
      console.log('联系人卡片点击:', this.properties.contact);
      
      this.triggerEvent('tap', {
        contact: this.properties.contact
      });
    },

    /**
     * 卡片长按事件
     */
    onCardLongPress(event) {
      if (this.data.skeleton) return;
      
      console.log('联系人卡片长按:', this.properties.contact);
      
      this.triggerEvent('longpress', {
        contact: this.properties.contact
      });
      
      // 触觉反馈
      wx.vibrateShort();
    },

    /**
     * 查看详情
     */
    onViewDetail(event) {
      event.stopPropagation();
      
      this.triggerEvent('viewdetail', {
        contact: this.properties.contact
      });
    },

    /**
     * 编辑联系人
     */
    onEditContact(event) {
      event.stopPropagation();
      
      this.triggerEvent('edit', {
        contact: this.properties.contact
      });
    },

    /**
     * 删除联系人
     */
    onDeleteContact(event) {
      event.stopPropagation();
      
      this.triggerEvent('delete', {
        contact: this.properties.contact
      });
    },

    /**
     * 格式化相对时间
     */
    formatRelativeTime(date) {
      return formatRelativeTime(date);
    },

    /**
     * 格式化置信度
     */
    formatConfidence(score) {
      if (typeof score !== 'number') return '';
      
      const percentage = Math.round(score * 100);
      return `${percentage}%`;
    },

    /**
     * 获取置信度等级
     */
    getConfidenceLevel(score) {
      if (typeof score !== 'number') return 'low';
      
      if (score >= 0.8) {
        return 'high';
      } else if (score >= 0.6) {
        return 'medium';
      } else {
        return 'low';
      }
    },

    /**
     * 高亮搜索关键词
     */
    highlightText(text, keyword) {
      if (!text || !keyword) return text;
      
      const regex = new RegExp(`(${keyword})`, 'gi');
      return text.replace(regex, '<span class="highlight-keyword">$1</span>');
    },

    /**
     * 获取标签类型
     */
    getTagType(tag) {
      if (!tag) return 'default';
      
      // 性别
      if (tag === '男' || tag === '女') return 'gender';
      
      // 年龄
      if (tag.includes('岁')) return 'age';
      
      // 位置
      if (tag.includes('北京') || tag.includes('上海') || tag.includes('广州') || 
          tag.includes('深圳') || tag.includes('杭州') || tag.includes('成都')) return 'location';
      
      // 婚姻状况
      if (tag === '已婚' || tag === '未婚' || tag === '离异') return 'marital';
      
      // 资产
      if (tag.includes('万')) return 'asset';
      
      // 默认为职位/公司
      return 'position';
    }
  },

  observers: {
    'contact, searchKeyword': function(contact, keyword) {
      if (!contact || !keyword) return;
      
      // 这里可以处理关键词高亮逻辑
      // 由于小程序不支持innerHTML，需要其他方式实现高亮
      console.log('关键词高亮:', contact.profile_name, keyword);
    }
  },

  lifetimes: {
    attached() {
      console.log('联系人卡片组件attached');
    },

    detached() {
      console.log('联系人卡片组件detached');
    }
  },

  pageLifetimes: {
    show() {
      // 页面显示时的逻辑
    },

    hide() {
      // 页面隐藏时的逻辑
    }
  }
});