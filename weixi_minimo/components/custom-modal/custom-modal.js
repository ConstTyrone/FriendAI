Component({
  properties: {
    // 显示状态
    visible: {
      type: Boolean,
      value: false
    },
    // 标题
    title: {
      type: String,
      value: ''
    },
    // 内容
    content: {
      type: String,
      value: ''
    },
    // 确认按钮文字
    confirmText: {
      type: String,
      value: '确定'
    },
    // 取消按钮文字
    cancelText: {
      type: String,
      value: '取消'
    },
    // 是否显示取消按钮
    showCancel: {
      type: Boolean,
      value: true
    },
    // 确认按钮类型
    confirmType: {
      type: String,
      value: 'primary' // primary, danger, success
    },
    // 是否显示关闭图标
    showClose: {
      type: Boolean,
      value: true
    }
  },

  data: {
    // 动画状态
    animationClass: ''
  },

  lifetimes: {
    attached() {
      // 监听主题变化
      const app = getApp();
      if (app.globalData && app.globalData.themeManager) {
        app.globalData.themeManager.applyToComponent(this);
      }
    }
  },

  observers: {
    visible(newVal) {
      if (newVal) {
        this.showModal();
      } else {
        this.hideModal();
      }
    }
  },

  methods: {
    showModal() {
      this.setData({
        animationClass: 'show'
      });
    },

    hideModal() {
      this.setData({
        animationClass: 'hide'
      });
      
      // 延迟隐藏，等待动画完成
      setTimeout(() => {
        this.triggerEvent('close');
      }, 300);
    },

    onConfirm() {
      this.triggerEvent('confirm');
      this.hideModal();
    },

    onCancel() {
      this.triggerEvent('cancel');
      this.hideModal();
    },

    onClose() {
      this.triggerEvent('close');
      this.hideModal();
    },

    onMaskTap() {
      // 点击遮罩关闭
      this.onClose();
    },

    onModalTap(e) {
      // 阻止冒泡，防止点击模态框内容时关闭
      e.stopPropagation();
    }
  }
});