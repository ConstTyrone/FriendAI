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
    showSourceMessages: false,
    
    // 关系相关数据
    relationshipStats: {
      total: 0,
      confirmed: 0,
      discovered: 0
    },
    recentRelationships: [], // 最近关系预览（最多显示3个）
    relationshipsLoading: false
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
      
      // 同时加载互动记录和关系数据
      await this.loadInteractions();
      await this.loadRelationships();
      
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
  },

  // ========== 关系相关方法 ==========

  /**
   * 加载关系数据
   */
  async loadRelationships() {
    try {
      console.log('开始加载关系数据:', this.data.contactId);
      
      this.setData({ relationshipsLoading: true });
      
      // 获取关系数据
      const response = await dataManager.getContactRelationships(this.data.contactId);
      
      if (response && response.success && response.relationships) {
        const relationships = response.relationships;
        console.log('关系数据加载成功:', relationships);
        
        // 计算统计信息
        const stats = {
          total: relationships.length,
          confirmed: relationships.filter(rel => rel.status === 'confirmed').length,
          discovered: relationships.filter(rel => rel.status === 'discovered').length
        };
        
        // 处理关系预览数据（最多显示3个最近的）
        const recentRelationships = this.processRelationshipsPreview(relationships.slice(0, 3));
        
        this.setData({
          relationshipStats: stats,
          recentRelationships,
          relationshipsLoading: false
        });
        
        console.log('关系统计信息:', stats);
      } else {
        // 没有关系数据
        this.setData({
          relationshipStats: { total: 0, confirmed: 0, discovered: 0 },
          recentRelationships: [],
          relationshipsLoading: false
        });
      }
      
    } catch (error) {
      console.error('加载关系数据失败:', error);
      
      // 设置默认值
      this.setData({
        relationshipStats: { total: 0, confirmed: 0, discovered: 0 },
        recentRelationships: [],
        relationshipsLoading: false
      });
    }
  },

  /**
   * 处理关系预览数据
   */
  processRelationshipsPreview(relationships) {
    const currentContactId = this.data.contactId;
    
    return relationships.map(rel => {
      // 确定对方是谁
      const isSource = rel.source_profile_id == currentContactId;
      const otherProfile = isSource ? rel.targetProfile : rel.sourceProfile;
      const otherName = otherProfile?.profile_name || '未知联系人';
      
      // 生成头像首字母
      const otherInitial = this.getAvatarText(otherName);
      
      // 格式化关系类型
      const relationshipLabel = this.formatRelationshipType(rel.relationship_type);
      
      // 格式化状态
      const statusLabel = this.formatRelationshipStatus(rel.status);
      
      return {
        id: rel.id,
        otherName,
        otherInitial,
        relationshipLabel,
        status: rel.status,
        statusLabel,
        confidenceScore: Math.round((rel.confidence_score || 0) * 100)
      };
    });
  },

  /**
   * 格式化关系类型
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
   * 格式化关系状态
   */
  formatRelationshipStatus(status) {
    const statusMap = {
      'discovered': '待确认',
      'confirmed': '已确认',
      'ignored': '已忽略'
    };
    return statusMap[status] || status;
  },

  /**
   * 查看所有关系
   */
  onViewAllRelationships() {
    console.log('查看所有关系，联系人ID:', this.data.contactId);
    
    const { contactInfo } = this.data;
    const contactName = contactInfo?.profile_name || contactInfo?.name || '联系人';
    
    wx.navigateTo({
      url: `/pages/relationship-list/relationship-list?contactId=${this.data.contactId}&contactName=${encodeURIComponent(contactName)}`
    });
  },

  /**
   * 查看关系详情
   */
  onViewRelationshipDetail(e) {
    const { relationshipId } = e.currentTarget.dataset;
    console.log('查看关系详情，关系ID:', relationshipId);
    
    wx.navigateTo({
      url: `/pages/relationship-detail/relationship-detail?relationshipId=${relationshipId}`
    });
  },

  /**
   * 立即分析关系
   */
  async onAnalyzeRelationships() {
    console.log('立即分析关系');
    
    wx.showLoading({
      title: '正在分析...',
      mask: true
    });
    
    try {
      // 调用关系重新分析API
      const response = await dataManager.reanalyzeContactRelationships(this.data.contactId);
      
      if (response && response.success) {
        wx.hideLoading();
        
        wx.showToast({
          title: '分析完成',
          icon: 'success'
        });
        
        // 重新加载关系数据
        await this.loadRelationships();
        
        // 如果发现了新关系，提示用户
        if (this.data.relationshipStats.total > 0) {
          setTimeout(() => {
            wx.showModal({
              title: '发现关系',
              content: `发现 ${this.data.relationshipStats.total} 个相关关系，是否查看？`,
              success: (res) => {
                if (res.confirm) {
                  this.onViewAllRelationships();
                }
              }
            });
          }, 1500);
        }
        
      } else {
        throw new Error(response?.message || '分析失败');
      }
      
    } catch (error) {
      wx.hideLoading();
      console.error('分析关系失败:', error);
      
      wx.showToast({
        title: '分析失败，请重试',
        icon: 'none'
      });
    }
  }
});