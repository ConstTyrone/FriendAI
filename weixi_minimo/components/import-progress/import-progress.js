/**
 * 批量导入进度显示组件
 * 提供实时进度反馈和用户体验优化
 */
Component({
  properties: {
    // 是否显示进度条
    visible: {
      type: Boolean,
      value: false
    },
    // 进度数据
    progress: {
      type: Object,
      value: {}
    },
    // 主题模式
    themeMode: {
      type: String,
      value: 'light'
    }
  },

  data: {
    // 进度百分比
    percentage: 0,
    // 状态文本
    statusText: '准备导入...',
    // 详细信息
    detailText: '',
    // 是否显示动画
    showAnimation: true,
    // 当前阶段
    currentPhase: 'preparing',
    // 成功率
    successRate: 0,
    // 是否显示统计信息
    showStats: false
  },

  observers: {
    'progress': function(newProgress) {
      if (newProgress && Object.keys(newProgress).length > 0) {
        this.updateProgress(newProgress);
      }
    },

    'visible': function(visible) {
      if (visible) {
        this.resetProgress();
      }
    }
  },

  methods: {
    /**
     * 更新进度显示
     */
    updateProgress(progress) {
      console.log('进度组件更新:', progress);
      
      switch (progress.phase) {
        case 'starting':
          this.setData({
            currentPhase: 'starting',
            percentage: 5,
            statusText: '🚀 准备导入',
            detailText: `即将导入 ${progress.total} 个联系人`,
            showAnimation: true,
            showStats: false
          });
          break;

        case 'importing':
          const batchProgress = Math.floor((progress.batchIndex / progress.totalBatches) * 85) + 10;
          this.setData({
            currentPhase: 'importing',
            percentage: batchProgress,
            statusText: `📥 正在导入 (${progress.overallProgress}%)`,
            detailText: `批次 ${progress.batchIndex}/${progress.totalBatches} - ${progress.currentBatch} 个联系人`,
            showAnimation: true,
            showStats: false
          });
          break;

        case 'importing_contact':
          const contactProgress = Math.floor((progress.index / progress.total) * 80) + 15;
          this.setData({
            currentPhase: 'importing_contact',
            percentage: contactProgress,
            statusText: `⚡ 导入中 (${progress.index}/${progress.total})`,
            detailText: `正在导入: ${progress.contact}${progress.attempt > 1 ? ` (重试 ${progress.attempt})` : ''}`,
            showAnimation: true,
            showStats: false
          });
          break;

        case 'completed':
          const { stats } = progress;
          const successRate = stats.total > 0 ? Math.round((stats.success / stats.total) * 100) : 0;
          
          this.setData({
            currentPhase: 'completed',
            percentage: 100,
            statusText: '✅ 导入完成',
            detailText: `成功率: ${successRate}% (${stats.success}/${stats.total})`,
            successRate: successRate,
            showAnimation: false,
            showStats: true
          });

          // 2秒后自动隐藏
          setTimeout(() => {
            this.triggerEvent('close');
          }, 2000);
          break;

        case 'error':
          this.setData({
            currentPhase: 'error',
            percentage: 0,
            statusText: '❌ 导入失败',
            detailText: progress.error || '发生未知错误',
            showAnimation: false,
            showStats: false
          });
          break;

        default:
          console.log('未知进度阶段:', progress.phase);
      }
    },

    /**
     * 重置进度
     */
    resetProgress() {
      this.setData({
        percentage: 0,
        statusText: '准备导入...',
        detailText: '',
        currentPhase: 'preparing',
        successRate: 0,
        showAnimation: true,
        showStats: false
      });
    },

    /**
     * 关闭进度显示
     */
    onClose() {
      this.triggerEvent('close');
    },

    /**
     * 点击遮罩关闭（仅在完成或错误状态下允许）
     */
    onMaskTap() {
      if (this.data.currentPhase === 'completed' || this.data.currentPhase === 'error') {
        this.onClose();
      }
    }
  }
});