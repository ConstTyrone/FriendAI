/**
 * 通知管理器 - 处理匹配通知的轮询和提醒
 */

import apiClient from './api-client';
import compatibility from './compatibility';

class NotificationManager {
  constructor() {
    this.pollingInterval = null;
    this.lastNotificationCount = 0;
    this.audioContext = null;
    this.isPolling = false;
    this.currentInterval = null;
  }

  /**
   * 开始轮询通知
   * @param {number} interval - 轮询间隔（毫秒），默认30秒
   */
  startPolling(interval = 30000) {
    if (this.isPolling) {
      console.log('通知轮询已在运行');
      return;
    }

    this.isPolling = true;
    this.currentInterval = interval;
    console.log('开始轮询匹配通知，间隔:', interval / 1000, '秒');

    // 立即检查一次
    this.checkNotifications();

    // 设置定时轮询
    this.pollingInterval = setInterval(() => {
      this.checkNotifications();
    }, interval);
  }

  /**
   * 停止轮询
   */
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
      this.isPolling = false;
      console.log('停止轮询通知');
    }
  }
  
  /**
   * 调整轮询间隔
   * @param {number} newInterval - 新的轮询间隔（毫秒）
   */
  adjustPollingInterval(newInterval) {
    if (!this.isPolling) return;
    
    // 如果新间隔与当前间隔相同，不做任何操作
    if (this.currentInterval === newInterval) {
      return;
    }
    
    console.log('调整轮询间隔为:', newInterval / 1000, '秒');
    
    // 停止当前轮询
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
    
    // 记录当前间隔
    this.currentInterval = newInterval;
    
    // 使用新间隔重新开始轮询
    this.pollingInterval = setInterval(() => {
      this.checkNotifications();
    }, newInterval);
  }

  /**
   * 检查新通知
   */
  async checkNotifications() {
    try {
      // 调用API获取未读匹配通知
      const result = await apiClient.request({
        url: '/api/notifications/matches',
        method: 'GET',
        data: {
          unread_only: true,
          limit: 10
        }
      });

      if (result.success) {
        const unreadCount = result.unread_count || 0;
        
        // 首次检查时，只记录数量，不显示通知
        // 避免登录时显示历史通知
        if (this.lastNotificationCount === 0 && unreadCount > 0) {
          console.log(`初始化通知数量: ${unreadCount} 个未读匹配`);
          this.lastNotificationCount = unreadCount;
          
          // 更新tabBar的badge，但不播放声音和显示通知
          this.updateTabBarBadge(unreadCount);
          
          // 更新全局状态
          const app = getApp();
          if (app && app.globalData) {
            app.globalData.hasNewMatches = true;
            app.globalData.unreadMatchCount = unreadCount;
            app.globalData.latestMatches = result.matches;
          }
          
          return; // 首次检查不显示通知
        }
        
        // 如果有新的未读通知（比上次多）
        if (unreadCount > this.lastNotificationCount) {
          const newCount = unreadCount - this.lastNotificationCount;
          console.log(`发现 ${newCount} 个新匹配！`);
          
          // 播放提示音
          this.playNotificationSound();
          
          // 显示通知
          this.showNotification(result.matches[0], newCount);
          
          // 更新tabBar的badge
          this.updateTabBarBadge(unreadCount);
          
          // 触发全局事件，让页面更新
          const app = getApp();
          if (app && app.globalData) {
            app.globalData.hasNewMatches = true;
            app.globalData.unreadMatchCount = unreadCount;
            app.globalData.latestMatches = result.matches;
          }
          
          // 发送事件给当前页面
          const pages = getCurrentPages();
          const currentPage = pages[pages.length - 1];
          if (currentPage && currentPage.onNewMatchNotification) {
            currentPage.onNewMatchNotification(result.matches);
          }
        }
        
        this.lastNotificationCount = unreadCount;
      }
    } catch (error) {
      console.error('检查通知失败:', error);
    }
  }

  /**
   * 播放提示音
   */
  playNotificationSound() {
    try {
      // 使用兼容性检查器安全调用振动API
      compatibility.safeVibrate({ type: 'medium' });

      // 播放系统提示音
      const audioContext = compatibility.safePlayAudio('/assets/sounds/notification.mp3', {
        volume: 0.8,
        onError: (res) => {
          console.log('播放提示音失败，使用默认提示');
          // 如果自定义音频失败，使用系统toast
          wx.showToast({
            title: '有新匹配！',
            icon: 'none',
            duration: 1000
          });
        }
      });
      
      if (!audioContext) {
        // 如果音频API不可用，显示toast提示
        wx.showToast({
          title: '有新匹配！',
          icon: 'none',
          duration: 1000
        });
      }
    } catch (error) {
      console.error('播放提示音失败:', error);
    }
  }

  /**
   * 显示通知提醒
   */
  showNotification(match, count) {
    if (!match) return;

    const title = count > 1 ? `发现${count}个新匹配！` : '发现新的匹配！';
    const content = `${match.intent_name} - ${match.profile_name || '新联系人'}`;

    // 显示模态对话框
    wx.showModal({
      title: title,
      content: content + '\n匹配度：' + (match.match_score * 100).toFixed(0) + '%',
      confirmText: '查看详情',
      cancelText: '稍后查看',
      success: (res) => {
        if (res.confirm) {
          // 跳转到匹配列表页面，传递意图ID以只显示该意图的匹配
          // 同时传递matchId用于高亮显示
          // 标记该匹配为已读
          if (match.id) {
            this.markAsRead(match.id);
          }
          
          // 构建跳转URL，传递意图ID和匹配ID
          let url = `/pages/matches/matches?intentId=${match.intent_id}`;
          if (match.id) {
            url += `&highlightId=${match.id}`;
          }
          
          wx.navigateTo({
            url: url
          });
        }
      }
    });
  }

  /**
   * 更新TabBar的badge
   */
  updateTabBarBadge(count) {
    try {
      // 由于使用自定义tabbar，改为通过全局数据更新
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.unreadMatchCount = count;
        
        // 触发自定义tabbar更新事件
        const pages = getCurrentPages();
        const currentPage = pages[pages.length - 1];
        if (currentPage && currentPage.updateTabBarBadge) {
          currentPage.updateTabBarBadge(count);
        }
      }
      
      // 如果有未读消息，在标题栏显示提示
      if (count > 0) {
        const title = count > 99 ? '(99+) 新匹配' : `(${count}) 新匹配`;
        wx.setNavigationBarTitle({
          title: title
        });
      }
    } catch (error) {
      console.error('更新未读计数失败:', error);
    }
  }

  /**
   * 标记匹配为已读
   */
  async markAsRead(matchId) {
    try {
      const result = await apiClient.request({
        url: `/api/notifications/matches/${matchId}/read`,
        method: 'POST'
      });

      if (result.success) {
        // 更新未读数
        this.lastNotificationCount = Math.max(0, this.lastNotificationCount - 1);
        this.updateTabBarBadge(this.lastNotificationCount);
        
        return true;
      }
      return false;
    } catch (error) {
      console.error('标记已读失败:', error);
      return false;
    }
  }

  /**
   * 获取所有未读通知
   */
  async getUnreadNotifications() {
    try {
      const result = await apiClient.request({
        url: '/api/notifications/matches',
        method: 'GET',
        data: {
          unread_only: true,
          limit: 50
        }
      });

      if (result.success) {
        return result.matches || [];
      }
      return [];
    } catch (error) {
      console.error('获取未读通知失败:', error);
      return [];
    }
  }
}

// 创建单例
const notificationManager = new NotificationManager();

export default notificationManager;