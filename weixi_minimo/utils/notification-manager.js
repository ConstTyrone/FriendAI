/**
 * 通知管理器 - 处理匹配通知的轮询和提醒
 */

import apiClient from './api-client';

class NotificationManager {
  constructor() {
    this.pollingInterval = null;
    this.lastNotificationCount = 0;
    this.audioContext = null;
    this.isPolling = false;
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
    console.log('开始轮询匹配通知...');

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
        
        // 如果有新的未读通知
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
      // 使用微信的振动API
      wx.vibrateShort({
        type: 'medium',
        success: () => {
          console.log('振动提醒');
        }
      });

      // 播放系统提示音
      const innerAudioContext = wx.createInnerAudioContext();
      innerAudioContext.src = '/assets/sounds/notification.mp3'; // 需要添加音频文件
      innerAudioContext.volume = 0.8;
      innerAudioContext.play();
      
      innerAudioContext.onError((res) => {
        console.log('播放提示音失败，使用默认提示');
        // 如果自定义音频失败，使用系统beep
        wx.showToast({
          title: '有新匹配！',
          icon: 'none',
          duration: 1000
        });
      });
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
          // 跳转到匹配列表页面
          wx.navigateTo({
            url: '/pages/matches/matches'
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
      if (count > 0) {
        // 在"匹配"tab上显示红点和数字
        wx.setTabBarBadge({
          index: 2, // 假设匹配是第3个tab
          text: count > 99 ? '99+' : count.toString()
        });
        
        // 显示红点
        wx.showTabBarRedDot({
          index: 2
        });
      } else {
        // 移除badge
        wx.removeTabBarBadge({
          index: 2
        });
        
        // 隐藏红点
        wx.hideTabBarRedDot({
          index: 2
        });
      }
    } catch (error) {
      console.error('更新TabBar Badge失败:', error);
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