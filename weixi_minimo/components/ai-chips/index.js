Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 建议词/历史记录数组
    chips: {
      type: Array,
      value: []
    },
    
    // 类型：suggestion(建议词) 或 history(历史记录)
    type: {
      type: String,
      value: 'suggestion'
    },
    
    // 是否可删除
    deletable: {
      type: Boolean,
      value: true
    },
    
    // 最大显示数量
    maxDisplay: {
      type: Number,
      value: 20
    }
  },

  data: {
    displayChips: []
  },

  observers: {
    'chips, maxDisplay': function(chips, maxDisplay) {
      const displayChips = (chips || []).slice(0, maxDisplay);
      this.setData({ displayChips });
    }
  },

  methods: {
    /**
     * 建议词点击事件
     */
    onChipTap(event) {
      const chip = event.currentTarget.dataset.chip;
      const index = event.currentTarget.dataset.index;
      
      console.log('建议词点击:', { chip, index, type: this.properties.type });
      
      // 触发点击事件
      this.triggerEvent('chip-tap', {
        chip,
        index,
        type: this.properties.type
      });
      
      // 触觉反馈
      wx.vibrateShort();
    },

    /**
     * 删除建议词
     */
    onDeleteChip(event) {
      if (!this.properties.deletable) return;
      
      const index = event.currentTarget.dataset.index;
      const chip = this.data.displayChips[index];
      
      console.log('删除建议词:', { chip, index });
      
      // 触发删除事件
      this.triggerEvent('chip-delete', {
        chip,
        index,
        type: this.properties.type
      });
      
      // 触觉反馈
      wx.vibrateShort();
    },

    /**
     * 阻止事件冒泡
     */
    onStopPropagation(event) {
      // 阻止事件冒泡到父元素
    },

    /**
     * 添加建议词
     */
    addChip(chip) {
      const currentChips = [...this.properties.chips];
      
      // 检查是否已存在
      if (!currentChips.includes(chip)) {
        currentChips.unshift(chip); // 添加到开头
        
        // 限制数量
        if (currentChips.length > this.properties.maxDisplay) {
          currentChips.pop(); // 移除最后一个
        }
        
        // 触发更新事件
        this.triggerEvent('chips-update', {
          chips: currentChips,
          type: this.properties.type
        });
      }
    },

    /**
     * 移除建议词
     */
    removeChip(chipToRemove) {
      const currentChips = this.properties.chips.filter(chip => chip !== chipToRemove);
      
      // 触发更新事件
      this.triggerEvent('chips-update', {
        chips: currentChips,
        type: this.properties.type
      });
    },

    /**
     * 清空所有建议词
     */
    clearChips() {
      this.triggerEvent('chips-update', {
        chips: [],
        type: this.properties.type
      });
    },

    /**
     * 获取建议词数量
     */
    getChipCount() {
      return this.data.displayChips.length;
    },

    /**
     * 检查是否包含某个建议词
     */
    hasChip(chip) {
      return this.properties.chips.includes(chip);
    }
  },

  lifetimes: {
    attached() {
      console.log('AI建议词组件attached:', {
        type: this.properties.type,
        chipCount: this.properties.chips.length
      });
    },

    detached() {
      console.log('AI建议词组件detached');
    }
  }
});