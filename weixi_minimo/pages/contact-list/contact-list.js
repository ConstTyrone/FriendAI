import { UI_CONFIG, PAGE_ROUTES, EVENT_TYPES } from '../../utils/constants';
import { formatContactDisplayName, getNameInitial, getAvatarColor } from '../../utils/format-utils';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';

Page({
  data: {
    // 联系人数据
    contacts: [],
    searchQuery: '',
    
    // 分页数据
    currentPage: 1,
    hasMore: true,
    loading: false,
    loadingMore: false,
    
    // 统计信息
    stats: {},
    
    // 操作菜单
    showActionMenu: false,
    selectedContact: null,
    
    // 搜索防抖定时器
    searchTimer: null
  },

  onLoad(options) {
    console.log('联系人列表页面加载', options);
    
    // 检查登录状态
    if (!authManager.isLoggedIn()) {
      console.log('用户未登录，跳转到设置页面');
      wx.showModal({
        title: '需要登录',
        content: '请先登录后再查看联系人列表',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    }
    
    // 添加数据管理器监听器
    this.addDataListeners();
    
    // 检查登录状态
    this.checkLoginStatus();
  },

  onShow() {
    console.log('联系人列表页面显示');
    
    // 每次显示时刷新数据
    this.refreshData();
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: '联系人'
    });
  },

  onReady() {
    console.log('联系人列表页面准备就绪');
  },

  onHide() {
    console.log('联系人列表页面隐藏');
    
    // 关闭操作菜单
    this.closeActionMenu();
  },

  onUnload() {
    console.log('联系人列表页面卸载');
    
    // 移除监听器
    this.removeDataListeners();
    
    // 清理定时器
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer);
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    console.log('下拉刷新');
    this.refreshData(true);
  },

  /**
   * 上拉加载
   */
  onReachBottom() {
    console.log('触底加载更多');
    this.loadMore();
  },

  /**
   * 检查登录状态
   */
  async checkLoginStatus() {
    try {
      const isLoggedIn = authManager.isLoggedIn();
      
      if (!isLoggedIn) {
        // 尝试自动登录
        const autoLoginSuccess = await authManager.checkAutoLogin();
        
        if (!autoLoginSuccess) {
          // 自动登录失败，跳转到设置页面进行登录
          wx.switchTab({
            url: '/pages/settings/settings'
          });
          return;
        }
      }
      
      // 登录成功，加载数据
      this.loadInitialData();
    } catch (error) {
      console.error('检查登录状态失败:', error);
      wx.showToast({
        title: '登录检查失败',
        icon: 'error'
      });
    }
  },

  /**
   * 加载初始数据
   */
  async loadInitialData(forceRefresh = false) {
    try {
      this.setData({ loading: true });
      
      // 并行加载联系人数据和统计信息
      const [contactsResult] = await Promise.allSettled([
        this.loadContacts(1, false, forceRefresh),
        this.loadStats()
      ]);
      
      if (contactsResult.status === 'fulfilled') {
        console.log('初始数据加载完成');
      } else {
        console.error('加载联系人数据失败:', contactsResult.reason);
        wx.showToast({
          title: '数据加载失败',
          icon: 'error'
        });
      }
    } catch (error) {
      console.error('加载初始数据失败:', error);
      wx.showToast({
        title: '数据加载失败',
        icon: 'error'
      });
    } finally {
      this.setData({ loading: false });
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 加载联系人数据
   */
  async loadContacts(page = 1, append = false, forceRefresh = false) {
    try {
      const params = {
        page,
        pageSize: UI_CONFIG.PAGE_SIZE,
        search: this.data.searchQuery,
        forceRefresh: forceRefresh || (page === 1 && !append)
      };
      
      const result = await dataManager.getContacts(params);
      
      // 处理联系人数据
      const processedContacts = this.processContacts(result.profiles || []);
      
      // 调试：打印第一个联系人的数据
      if (processedContacts.length > 0) {
        console.log('第一个联系人数据:', processedContacts[0]);
        console.log('手机号:', processedContacts[0].phone);
      }
      
      this.setData({
        contacts: append ? [...this.data.contacts, ...processedContacts] : processedContacts,
        currentPage: page,
        hasMore: page < (result.total_pages || 1),
        loading: false,
        loadingMore: false
      });
      
      return result;
    } catch (error) {
      console.error('加载联系人失败:', error);
      throw error;
    }
  },

  /**
   * 处理联系人数据
   */
  processContacts(contacts) {
    return contacts.map(contact => ({
      ...contact,
      displayName: formatContactDisplayName(contact),
      initial: getNameInitial(contact.profile_name || contact.name),
      avatarColor: getAvatarColor(contact.profile_name || contact.name),
      formattedTags: this.formatContactTags(contact)
    }));
  },

  /**
   * 格式化联系人标签
   */
  formatContactTags(contact) {
    const tags = [];
    
    // 添加性别和年龄
    if (contact.gender) tags.push(contact.gender);
    if (contact.age) tags.push(`${contact.age}岁`);
    
    // 添加位置
    if (contact.location) {
      // 简化位置显示，只显示城市
      const location = contact.location.replace(/市.*区/, '').replace(/省/, '');
      tags.push(location);
    }
    
    // 添加公司或职位
    if (contact.position) {
      tags.push(contact.position);
    } else if (contact.company) {
      // 简化公司名，去掉"有限公司"等后缀
      const company = contact.company.replace(/有限公司|股份有限公司|公司/, '');
      tags.push(company);
    }
    
    // 添加婚姻状况
    if (contact.marital_status && contact.marital_status !== '未知') {
      tags.push(contact.marital_status);
    }
    
    // 添加资产水平
    if (contact.asset_level && contact.asset_level !== '未知') {
      tags.push(contact.asset_level);
    }
    
    return tags.slice(0, 4); // 最多显示4个标签
  },

  /**
   * 加载统计信息
   */
  async loadStats() {
    try {
      const stats = await dataManager.getStats();
      this.setData({ stats });
      return stats;
    } catch (error) {
      console.error('加载统计信息失败:', error);
      return {};
    }
  },

  /**
   * 刷新数据
   */
  async refreshData(showToast = false) {
    try {
      this.setData({ 
        currentPage: 1,
        hasMore: true 
      });
      
      // 强制刷新数据，不使用缓存
      await this.loadInitialData(true);
      
      if (showToast) {
        wx.showToast({
          title: '刷新完成',
          icon: 'success',
          duration: 1500
        });
      }
    } catch (error) {
      console.error('刷新数据失败:', error);
      if (showToast) {
        wx.showToast({
          title: '刷新失败',
          icon: 'error'
        });
      }
    }
  },

  /**
   * 加载更多
   */
  async loadMore() {
    if (this.data.loadingMore || !this.data.hasMore) {
      return;
    }
    
    try {
      this.setData({ loadingMore: true });
      
      const nextPage = this.data.currentPage + 1;
      await this.loadContacts(nextPage, true);
      
    } catch (error) {
      console.error('加载更多失败:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    }
  },

  /**
   * 搜索输入变化
   */
  onSearchChange(event) {
    const query = event.detail.value;
    this.setData({ searchQuery: query });
    
    // 防抖搜索
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer);
    }
    
    this.data.searchTimer = setTimeout(() => {
      this.performSearch(query);
    }, UI_CONFIG.SEARCH_DEBOUNCE);
  },

  /**
   * 搜索提交
   */
  onSearchSubmit(event) {
    const query = event.detail.value;
    this.performSearch(query);
  },

  /**
   * 清除搜索
   */
  onSearchClear() {
    this.setData({ searchQuery: '' });
    this.performSearch('');
  },

  /**
   * 执行搜索
   */
  async performSearch(query) {
    try {
      this.setData({ 
        loading: true,
        currentPage: 1,
        hasMore: true 
      });
      
      // 搜索时强制刷新，确保获取最新数据
      await this.loadContacts(1, false, true);
      
      // 保存搜索历史
      if (query.trim()) {
        dataManager.addSearchHistory(query.trim());
      }
      
    } catch (error) {
      console.error('搜索失败:', error);
      wx.showToast({
        title: '搜索失败',
        icon: 'error'
      });
    }
  },

  /**
   * 联系人点击
   */
  onContactTap(event) {
    const contact = event.detail.contact || event.currentTarget.dataset.contact;
    
    if (!contact) return;
    
    console.log('点击联系人:', contact);
    
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_DETAIL}?id=${contact.id}`
    });
  },

  /**
   * 联系人长按
   */
  onContactLongPress(event) {
    const contact = event.detail.contact || event.currentTarget.dataset.contact;
    
    if (!contact) return;
    
    console.log('长按联系人:', contact);
    
    // 显示操作菜单
    this.showActionMenu(contact);
    
    // 触觉反馈
    wx.vibrateShort();
  },

  /**
   * 显示操作菜单
   */
  showActionMenu(contact) {
    this.setData({
      selectedContact: {
        ...contact,
        initial: getNameInitial(contact.profile_name || contact.name),
        avatarColor: getAvatarColor(contact.profile_name || contact.name)
      },
      showActionMenu: true
    });
  },

  /**
   * 关闭操作菜单
   */
  closeActionMenu() {
    this.setData({
      showActionMenu: false,
      selectedContact: null
    });
  },

  /**
   * 操作菜单相关事件
   */
  onCloseActionMenu() {
    this.closeActionMenu();
  },

  onStopPropagation() {
    // 阻止事件冒泡
  },

  /**
   * 查看详情
   */
  onViewDetail() {
    const contact = this.data.selectedContact;
    this.closeActionMenu();
    
    if (contact) {
      wx.navigateTo({
        url: `${PAGE_ROUTES.CONTACT_DETAIL}?id=${contact.id}`
      });
    }
  },

  /**
   * 编辑联系人
   */
  onEditContact() {
    const contact = this.data.selectedContact;
    this.closeActionMenu();
    
    if (contact) {
      wx.navigateTo({
        url: `${PAGE_ROUTES.CONTACT_FORM}?id=${contact.id}&mode=edit`
      });
    }
  },

  /**
   * 删除联系人
   */
  onDeleteContact() {
    const contact = this.data.selectedContact;
    this.closeActionMenu();
    
    if (!contact) return;
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除联系人"${contact.profile_name || contact.name}"吗？`,
      confirmColor: '#ff4757',
      success: (res) => {
        if (res.confirm) {
          this.deleteContact(contact.id);
        }
      }
    });
  },

  /**
   * 执行删除联系人
   */
  async deleteContact(contactId) {
    try {
      wx.showLoading({ title: '删除中...' });
      
      await dataManager.deleteContact(contactId);
      
      wx.hideLoading();
      wx.showToast({
        title: '删除成功',
        icon: 'success'
      });
      
      // 刷新列表
      this.refreshData();
      
    } catch (error) {
      wx.hideLoading();
      console.error('删除联系人失败:', error);
      
      wx.showToast({
        title: '删除失败',
        icon: 'error'
      });
    }
  },

  /**
   * 添加联系人
   */
  onAddContact() {
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_FORM}?mode=add`
    });
  },

  /**
   * 刷新数据按钮点击
   */
  onRefreshData() {
    this.refreshData(true);
  },

  /**
   * 手动加载更多
   */
  onLoadMore() {
    this.loadMore();
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
        tag.includes('深圳') || tag.includes('杭州') || tag.includes('成都') ||
        tag.includes('天津') || tag.includes('重庆')) return 'location';
    
    // 婚姻状况
    if (tag === '已婚' || tag === '未婚' || tag === '离异') return 'marital';
    
    // 资产
    if (tag.includes('万')) return 'asset';
    
    // 默认为职位/公司
    return 'position';
  },

  /**
   * 添加数据监听器
   */
  addDataListeners() {
    this.dataListener = (eventType, data) => {
      switch (eventType) {
        case 'contactsUpdated':
          console.log('联系人数据更新:', data?.length);
          // 更新页面联系人数据
          if (data && Array.isArray(data)) {
            const processedContacts = this.processContacts(data);
            this.setData({ 
              contacts: processedContacts,
              loading: false,
              loadingMore: false 
            });
          }
          break;
          
        case 'contactDeleted':
          console.log('联系人已删除:', data);
          // 从列表中移除已删除的联系人
          if (data && data.id) {
            const updatedContacts = this.data.contacts.filter(contact => contact.id !== data.id);
            this.setData({ contacts: updatedContacts });
          }
          break;
          
        case 'contactCreated':
          console.log('新增联系人:', data);
          // 将新联系人添加到列表开头
          if (data) {
            const processedContact = this.processContacts([data]);
            this.setData({ 
              contacts: [...processedContact, ...this.data.contacts]
            });
          }
          break;
          
        case 'contactUpdated':
          console.log('联系人已更新:', data);
          // 更新列表中的联系人
          if (data && data.id) {
            const updatedContacts = this.data.contacts.map(contact => 
              contact.id === data.id ? this.processContacts([data])[0] : contact
            );
            this.setData({ contacts: updatedContacts });
          }
          break;
          
        case 'statsUpdated':
          console.log('统计信息更新:', data);
          this.setData({ stats: data });
          break;
          
        case 'searchPerformed':
          console.log('搜索执行:', data);
          break;
      }
    };
    
    dataManager.addListener(this.dataListener);
  },

  /**
   * 移除数据监听器
   */
  removeDataListeners() {
    if (this.dataListener) {
      dataManager.removeListener(this.dataListener);
      this.dataListener = null;
    }
  }
});