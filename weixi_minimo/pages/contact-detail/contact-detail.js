import { PAGE_ROUTES } from '../../utils/constants';
import { formatDate, formatPhone as formatPhoneUtil, getNameInitial, getAvatarColor } from '../../utils/format-utils';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import themeManager from '../../utils/theme-manager';

Page({
  data: {
    // 联系人信息
    contactId: '',
    contactInfo: null,
    
    // 页面状态
    loading: true,
    error: null,
    
    // 互动记录
    interactions: [],
    interactionsLoading: false,
    
    // 对话框状态
    showDeleteDialog: false,
    
    // 操作状态
    actionLoading: false,
    
    // 信息来源展开状态
    showSourceMessages: false
  },

  onLoad(options) {
    console.log('联系人详情页面加载', options);
    
    // 应用主题
    themeManager.applyToPage(this);
    
    const contactId = options.id || options.contactId;
    
    if (!contactId) {
      console.error('缺少联系人ID参数');
      this.setData({
        error: '缺少联系人ID参数',
        loading: false
      });
      return;
    }
    
    this.setData({ contactId });
    
    // 初始化页面数据
    this.initPageData();
  },

  onShow() {
    console.log('联系人详情页面显示');
    
    // 刷新联系人信息（可能在编辑后返回）
    if (this.data.contactId && !this.data.loading) {
      this.loadContactInfo();
    }
  },

  onReady() {
    console.log('联系人详情页面准备就绪');
  },

  onHide() {
    console.log('联系人详情页面隐藏');
  },

  onUnload() {
    console.log('联系人详情页面卸载');
  },
  
  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    console.log('下拉刷新联系人详情');
    this.refreshData();
  },

  /**
   * 初始化页面数据
   */
  async initPageData() {
    try {
      // 检查登录状态
      if (!authManager.isLoggedIn()) {
        wx.showModal({
          title: '未登录',
          content: '请先登录再查看联系人详情',
          showCancel: false,
          success: () => {
            wx.navigateBack();
          }
        });
        return;
      }
      
      // 加载联系人信息
      await this.loadContactInfo();
      
      console.log('页面数据初始化完成');
    } catch (error) {
      console.error('初始化页面数据失败:', error);
      this.setData({
        error: error.message || '加载失败',
        loading: false
      });
    }
  },

  /**
   * 加载联系人信息
   */
  async loadContactInfo() {
    try {
      this.setData({ 
        loading: true, 
        error: null 
      });
      
      // 获取联系人详细信息
      const contactInfo = await dataManager.getContactDetail(this.data.contactId);
      
      if (!contactInfo) {
        throw new Error('联系人不存在或已被删除');
      }
      
      // 同时加载互动记录
      await this.loadInteractions();
      
      // 调试：打印联系人详情
      console.log('联系人详情数据:', contactInfo);
      console.log('手机号字段:', contactInfo.phone);
      console.log('所有字段:', Object.keys(contactInfo));
      
      // 预处理联系人数据，添加头像信息和格式化电话
      const processedContactInfo = {
        ...contactInfo,
        initial: this.getAvatarText(contactInfo.profile_name || contactInfo.name),
        avatarColor: this.getAvatarColor(contactInfo.profile_name || contactInfo.name),
        // 如果有电话，格式化显示
        phone: contactInfo.phone ? formatPhoneUtil(contactInfo.phone) : contactInfo.phone
      };
      
      this.setData({
        contactInfo: processedContactInfo,
        loading: false
      });
      
      // 设置页面标题
      wx.setNavigationBarTitle({
        title: contactInfo.profile_name || contactInfo.name || '联系人详情'
      });
      
      console.log('联系人信息加载完成:', contactInfo);
    } catch (error) {
      console.error('加载联系人信息失败:', error);
      
      this.setData({
        error: error.message || '加载联系人信息失败',
        loading: false
      });
      
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    }
  },

  /**
   * 加载互动记录
   */
  async loadInteractions() {
    try {
      this.setData({ interactionsLoading: true });
      
      const interactions = await dataManager.getContactInteractions(this.data.contactId);
      
      this.setData({
        interactions: interactions || [],
        interactionsLoading: false
      });
      
      console.log('互动记录加载完成:', interactions);
    } catch (error) {
      console.error('加载互动记录失败:', error);
      
      this.setData({ 
        interactions: [],
        interactionsLoading: false 
      });
    }
  },

  /**
   * 刷新数据
   */
  async refreshData() {
    try {
      await this.loadContactInfo();
      
      wx.stopPullDownRefresh();
      
      wx.showToast({
        title: '刷新完成',
        icon: 'success'
      });
      
    } catch (error) {
      wx.stopPullDownRefresh();
      
      console.error('刷新数据失败:', error);
      
      wx.showToast({
        title: '刷新失败',
        icon: 'error'
      });
    }
  },

  /**
   * 编辑联系人
   */
  onEditContact() {
    if (!this.data.contactInfo) {
      return;
    }
    
    // 跳转到联系人表单页面，传递编辑模式参数
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_FORM}?mode=edit&id=${this.data.contactId}`
    });
  },

  /**
   * 显示删除确认对话框
   */
  onDeleteContact() {
    this.setData({ showDeleteDialog: true });
  },

  /**
   * 确认删除联系人
   */
  onConfirmDelete() {
    this.setData({ showDeleteDialog: false });
    this.performDeleteContact();
  },

  /**
   * 取消删除
   */
  onCancelDelete() {
    this.setData({ showDeleteDialog: false });
  },

  /**
   * 执行删除联系人
   */
  async performDeleteContact() {
    if (this.data.actionLoading) return;
    
    try {
      this.setData({ actionLoading: true });
      
      wx.showLoading({
        title: '删除中...',
        mask: true
      });
      
      // 调用删除接口
      await dataManager.deleteContact(this.data.contactId);
      
      wx.hideLoading();
      
      wx.showToast({
        title: '删除成功',
        icon: 'success',
        duration: 2000
      });
      
      // 延迟返回，让用户看到成功提示
      setTimeout(() => {
        wx.navigateBack();
      }, 2000);
      
      console.log('联系人删除成功');
    } catch (error) {
      wx.hideLoading();
      
      this.setData({ actionLoading: false });
      
      console.error('删除联系人失败:', error);
      
      wx.showModal({
        title: '删除失败',
        content: error.message || '请检查网络连接后重试',
        showCancel: false
      });
    }
  },

  /**
   * 拨打电话
   */
  onCallPhone() {
    const phone = this.data.contactInfo?.phone;
    
    if (!phone) {
      wx.showToast({
        title: '没有电话号码',
        icon: 'none'
      });
      return;
    }
    
    wx.showModal({
      title: '拨打电话',
      content: `是否拨打 ${formatPhoneUtil(phone)}？`,
      success: (res) => {
        if (res.confirm) {
          wx.makePhoneCall({
            phoneNumber: phone,
            fail: (error) => {
              console.error('拨打电话失败:', error);
              wx.showToast({
                title: '拨打失败',
                icon: 'error'
              });
            }
          });
        }
      }
    });
  },

  /**
   * 复制微信号
   */
  onCopyWechatId() {
    const wechatId = this.data.contactInfo?.wechat_id;
    
    if (!wechatId) {
      wx.showToast({
        title: '没有微信号',
        icon: 'none'
      });
      return;
    }
    
    wx.setClipboardData({
      data: wechatId,
      success: () => {
        wx.showToast({
          title: '已复制微信号',
          icon: 'success'
        });
      },
      fail: () => {
        wx.showToast({
          title: '复制失败',
          icon: 'error'
        });
      }
    });
  },


  /**
   * 添加备注
   */
  onAddNote() {
    // 这里可以实现添加备注的功能
    wx.showModal({
      title: '功能开发中',
      content: '添加备注功能正在开发中，敬请期待...',
      showCancel: false
    });
  },

  /**
   * 查看更多互动记录
   */
  onViewMoreInteractions() {
    // 这里可以实现查看更多互动记录的功能
    wx.showModal({
      title: '功能开发中',
      content: '更多互动记录功能正在开发中，敬请期待...',
      showCancel: false
    });
  },

  /**
   * 格式化日期
   */
  formatDate(timestamp) {
    if (!timestamp) return '未知';
    return formatDate(new Date(timestamp), 'YYYY-MM-DD HH:mm');
  },

  /**
   * 格式化电话号码
   */
  formatPhone(phone) {
    return formatPhoneUtil(phone);
  },

  /**
   * 格式化数据来源类型
   */
  formatSourceType(type) {
    const typeMap = {
      'text': '文本消息',
      'voice': '语音消息',
      'image': '图片识别',
      'file': '文件解析',
      'chat_record': '聊天记录'
    };
    return typeMap[type] || type || '未知';
  },

  /**
   * 获取联系人头像文字
   */
  getAvatarText(name) {
    return getNameInitial(name);
  },

  /**
   * 获取头像背景色
   */
  getAvatarColor(name) {
    return getAvatarColor(name);
  },

  /**
   * 获取标签颜色
   */
  getTagTheme(index) {
    const themes = ['primary', 'success', 'warning', 'danger', 'default'];
    return themes[index % themes.length];
  },

  /**
   * 获取互动类型图标
   */
  getInteractionIcon(type) {
    const iconMap = {
      'call': 'call',
      'message': 'chat',
      'meeting': 'usergroup',
      'note': 'edit',
      'default': 'time'
    };
    
    return iconMap[type] || iconMap.default;
  },

  /**
   * 获取互动类型描述
   */
  getInteractionDesc(type) {
    const descMap = {
      'call': '通话记录',
      'message': '消息记录',
      'meeting': '会面记录',
      'note': '备注记录',
      'default': '其他记录'
    };
    
    return descMap[type] || descMap.default;
  },

  /**
   * 切换信息来源展开状态
   */
  onToggleSourceMessages() {
    this.setData({
      showSourceMessages: !this.data.showSourceMessages
    });
  },

  /**
   * 格式化信息来源时间
   */
  formatSourceTime(timestamp) {
    if (!timestamp) return '未知时间';
    try {
      const date = new Date(timestamp);
      return formatDate(date, 'MM-DD HH:mm');
    } catch (error) {
      console.error('格式化时间失败:', error);
      return '时间格式错误';
    }
  },

  /**
   * 格式化消息类型
   */
  formatMessageType(type) {
    const typeMap = {
      'text': '文本',
      'voice': '语音',
      'image': '图片',
      'file': '文件',
      'chat_record': '聊天记录',
      'video': '视频'
    };
    return typeMap[type] || type || '未知';
  }
});