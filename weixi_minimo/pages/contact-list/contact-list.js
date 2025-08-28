import { UI_CONFIG, PAGE_ROUTES, EVENT_TYPES } from '../../utils/constants';
import { formatContactDisplayName, getNameInitial, getAvatarColor } from '../../utils/format-utils';
import { isValidSearchQuery } from '../../utils/validator';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import themeManager from '../../utils/theme-manager';
import semanticSearchEngine from '../../utils/semantic-search';
import contactImporter from '../../utils/contact-importer';

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
    searchTimer: null,
    
    // 智能搜索相关
    showSearchPanel: false,
    searchPanelStyle: '', // 搜索面板的动态样式
    searchSuggestions: [
      '30岁的程序员',
      '在北京做金融的',
      '年轻的设计师',
      '有经验的销售',
      '做医生的朋友',
      '互联网行业',
      '从事教育工作',
      '上海的律师'
    ],
    searchHistory: [],
    searchAnalysis: '',
    allContacts: [], // 缓存所有联系人用于本地搜索
    isSearching: false,
    searchFocused: false,
    
    // 手势操作状态
    swipeStates: {}, // 每个item的滑动状态 {index: boolean}
    touchStartX: 0,
    touchStartY: 0,
    touchStartTime: 0,
    currentSwipeIndex: -1, // 当前正在滑动的item索引
    
    // 导入进度状态
    showImportProgress: false,
    importProgress: {},
    
    // 添加菜单状态
    showAddMenu: false,
    
    // 弹窗状态
    showDeleteModal: false,
    deleteContactName: '',
    pendingDeleteContact: null,
    
  },

  onLoad(options) {
    console.log('联系人列表页面加载', options);
    
    // 应用主题
    themeManager.applyToPage(this);
    
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
    console.log('当前showAddMenu状态:', this.data.showAddMenu);
    
    // 每次显示时强制刷新数据（绕过缓存）
    this.refreshData();
    
    // 加载搜索历史
    this.loadSearchHistory();
    
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
      const [contactsResult, statsResult] = await Promise.allSettled([
        this.loadContacts(1, false, forceRefresh),
        this.loadStats()
      ]);
      
      if (contactsResult.status === 'fulfilled') {
        console.log('初始数据加载完成');
        
        // 在后台预加载所有联系人数据用于智能搜索
        this.ensureAllContactsLoaded().catch(error => {
          console.error('预加载搜索数据失败:', error);
        });
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
   * 执行智能搜索
   */
  async performSearch(query) {
    try {
      this.setData({ 
        isSearching: true,
        showSearchPanel: false
      });

      if (!query.trim()) {
        // 空查询，显示所有联系人
        this.setData({
          contacts: this.data.allContacts,
          searchAnalysis: '',
          isSearching: false
        });
        return;
      }

      // 确保有完整的联系人数据用于本地搜索
      await this.ensureAllContactsLoaded();

      // 使用语义搜索引擎进行本地搜索
      const searchResult = semanticSearchEngine.search(this.data.allContacts, query.trim());
      
      // 处理搜索结果，添加显示所需的字段
      const processedResults = searchResult.results.map(contact => ({
        ...contact,
        displayName: formatContactDisplayName(contact),
        initial: getNameInitial(contact.profile_name || contact.name),
        avatarColor: getAvatarColor(contact.profile_name || contact.name),
        matchPercentage: Math.round(contact.matchScore * 100),
        isHighMatch: contact.matchScore > 0.7,
        formattedTags: this.formatContactTags(contact)
      }));

      this.setData({
        contacts: processedResults,
        searchAnalysis: searchResult.analysis,
        isSearching: false,
        hasMore: false // 搜索结果不分页
      });

      // 保存搜索历史
      dataManager.addSearchHistory(query.trim());
      this.loadSearchHistory();

      // 显示搜索完成提示
      wx.showToast({
        title: `找到${processedResults.length}个结果`,
        icon: 'success',
        duration: 1500
      });
      
    } catch (error) {
      console.error('智能搜索失败:', error);
      
      this.setData({
        isSearching: false,
        contacts: [],
        searchAnalysis: ''
      });
      
      wx.showToast({
        title: '搜索失败，请重试',
        icon: 'error'
      });
    }
  },

  /**
   * 确保所有联系人都已加载到本地缓存
   */
  async ensureAllContactsLoaded() {
    if (this.data.allContacts.length > 0) {
      return; // 已有缓存数据
    }

    try {
      // 获取所有联系人数据（不分页）
      const result = await dataManager.getContacts({
        page: 1,
        pageSize: 1000, // 获取足够大的数量
        search: '', // 空搜索获取所有数据
        forceRefresh: false
      });

      const processedContacts = this.processContacts(result.profiles || []);
      
      this.setData({
        allContacts: processedContacts
      });

      console.log(`已缓存 ${processedContacts.length} 个联系人用于本地搜索`);
      
    } catch (error) {
      console.error('加载所有联系人失败:', error);
      throw error;
    }
  },


  /**
   * 加载搜索历史
   */
  loadSearchHistory() {
    try {
      const history = dataManager.getSearchHistory();
      this.setData({
        searchHistory: history.slice(0, 10) // 最多显示10条历史
      });
      
      console.log('搜索历史加载完成:', history.length);
    } catch (error) {
      console.error('加载搜索历史失败:', error);
    }
  },


  /**
   * 搜索面板切换
   */
  onToggleSearchPanel() {
    if (!this.data.showSearchPanel) {
      this.showSearchPanelWithPosition();
    } else {
      this.setData({ 
        showSearchPanel: false 
      });
    }
  },

  /**
   * 搜索框聚焦
   */
  onSearchFocus() {
    this.setData({ 
      searchFocused: true
    });
    this.showSearchPanelWithPosition();
  },

  /**
   * 显示搜索面板并设置正确位置
   */
  showSearchPanelWithPosition() {
    // 获取搜索框位置
    const query = wx.createSelectorQuery();
    query.select('.ai-search-header').boundingClientRect();
    query.exec((res) => {
      if (res[0]) {
        const searchHeaderRect = res[0];
        const panelTop = searchHeaderRect.bottom + 10; // 搜索框底部 + 10px间距
        
        // 动态设置搜索面板位置
        const updateData = {
          showSearchPanel: true,
          searchPanelTop: panelTop
        };
        
        this.setData(updateData);
        
        // 更新搜索面板的top位置
        this.updateSearchPanelStyle(panelTop);
      } else {
        // 如果获取位置失败，使用默认显示
        this.setData({ 
          showSearchPanel: true 
        });
      }
    });
  },

  /**
   * 更新搜索面板样式
   */
  updateSearchPanelStyle(top) {
    // 使用setData更新样式
    this.setData({
      searchPanelStyle: `top: ${top}px;`
    });
  },

  /**
   * 搜索框失焦
   */
  onSearchBlur() {
    // 延迟设置，避免点击建议时立即失焦
    setTimeout(() => {
      this.setData({ 
        searchFocused: false,
        showSearchPanel: false 
      });
    }, 200);
  },

  /**
   * 搜索建议点击
   */
  onSuggestionTap(event) {
    const suggestion = event.currentTarget.dataset.text;
    this.setData({ 
      searchQuery: suggestion
    });
    this.performSearch(suggestion);
  },

  /**
   * 搜索历史点击
   */
  onHistoryTap(event) {
    const history = event.currentTarget.dataset.text;
    this.setData({ 
      searchQuery: history
    });
    this.performSearch(history);
  },

  /**
   * 清除搜索历史
   */
  onClearHistory() {
    wx.showModal({
      title: '确认清除',
      content: '确定要清除所有搜索历史吗？',
      success: (res) => {
        if (res.confirm) {
          dataManager.clearSearchHistory();
          this.setData({ searchHistory: [] });
          
          wx.showToast({
            title: '已清除历史',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * 联系人点击
   */
  onContactTap(event) {
    const contact = event.detail.contact || event.currentTarget.dataset.contact;
    
    if (!contact) return;
    
    // 检查是否有打开的滑动菜单，如果有则先关闭
    const hasOpenMenus = Object.values(this.data.swipeStates).some(state => state);
    if (hasOpenMenus) {
      this.closeAllSwipeMenus();
      return; // 第一次点击关闭菜单，不跳转
    }
    
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
  onEditContact(e) {
    e && e.stopPropagation && e.stopPropagation(); // 阻止事件冒泡
    
    let contact;
    
    console.log('编辑联系人调用，检查来源');
    console.log('currentSwipeIndex:', this.data.currentSwipeIndex);
    console.log('selectedContact:', this.data.selectedContact);
    
    // 优先检查是否有滑动菜单打开
    const swipeIndex = this.data.currentSwipeIndex;
    if (swipeIndex >= 0 && swipeIndex < this.data.contacts.length) {
      // 从滑动菜单点击
      contact = this.data.contacts[swipeIndex];
      console.log('从滑动菜单编辑联系人:', contact);
      this.closeAllSwipeMenus();
    } else if (this.data.selectedContact) {
      // 从长按菜单点击
      contact = this.data.selectedContact;
      console.log('从长按菜单编辑联系人:', contact);
      this.closeActionMenu();
    } else {
      console.error('无法确定操作来源，currentSwipeIndex:', swipeIndex);
    }
    
    if (contact && contact.id) {
      wx.navigateTo({
        url: `${PAGE_ROUTES.CONTACT_FORM}?id=${contact.id}&mode=edit`
      });
    } else {
      console.error('编辑联系人失败：联系人数据不完整', contact);
      wx.showToast({
        title: '联系人数据错误',
        icon: 'none'
      });
    }
  },

  /**
   * 删除联系人
   */
  onDeleteContact(e) {
    e && e.stopPropagation && e.stopPropagation(); // 阻止事件冒泡
    
    let contact;
    
    console.log('删除联系人调用，检查来源');
    console.log('currentSwipeIndex:', this.data.currentSwipeIndex);
    console.log('selectedContact:', this.data.selectedContact);
    
    // 优先检查是否有滑动菜单打开
    const swipeIndex = this.data.currentSwipeIndex;
    if (swipeIndex >= 0 && swipeIndex < this.data.contacts.length) {
      // 从滑动菜单点击
      contact = this.data.contacts[swipeIndex];
      console.log('从滑动菜单删除联系人:', contact);
      this.closeAllSwipeMenus();
    } else if (this.data.selectedContact) {
      // 从长按菜单点击
      contact = this.data.selectedContact;
      console.log('从长按菜单删除联系人:', contact);
      this.closeActionMenu();
    } else {
      console.error('无法确定操作来源，currentSwipeIndex:', swipeIndex);
    }
    
    if (!contact || !contact.id) {
      console.error('删除联系人失败：联系人数据不完整', contact);
      wx.showToast({
        title: '联系人数据错误',
        icon: 'none'
      });
      return;
    }
    
    // 显示自定义删除确认弹窗
    this.setData({
      showDeleteModal: true,
      deleteContactName: contact.profile_name || contact.name || '未知',
      pendingDeleteContact: contact
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
    // 关闭添加菜单
    this.setData({ showAddMenu: false });
    
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_FORM}?mode=add`
    });
  },

  /**
   * 切换添加菜单显示状态
   */
  onToggleAddMenu(e) {
    // 阻止事件冒泡，防止触发onPageTap
    e && e.stopPropagation && e.stopPropagation();
    
    const newState = !this.data.showAddMenu;
    console.log('切换添加菜单:', { 
      current: this.data.showAddMenu, 
      newState: newState 
    });
    
    // 添加触觉反馈
    wx.vibrateShort();
    
    this.setData({
      showAddMenu: newState
    });
    
    // 延迟检查DOM状态
    setTimeout(() => {
      console.log('菜单状态最终确认:', this.data.showAddMenu);
      const query = wx.createSelectorQuery();
      query.select('.add-menu').boundingClientRect((rect) => {
        console.log('菜单元素信息:', rect);
      }).exec();
    }, 100);
  },

  /**
   * 关闭添加菜单
   */
  onCloseAddMenu() {
    this.setData({ showAddMenu: false });
  },

  /**
   * 阻止事件冒泡
   */
  onStopPropagation(e) {
    // 阻止事件冒泡，防止点击菜单内容时关闭菜单
    e.stopPropagation && e.stopPropagation();
  },



  /**
   * 删除弹窗 - 确认
   */
  async onConfirmDelete() {
    console.log('删除弹窗确认按钮点击');
    
    this.setData({
      showDeleteModal: false
    });
    
    if (this.data.pendingDeleteContact) {
      console.log('执行删除联系人:', this.data.pendingDeleteContact);
      await this.deleteContact(this.data.pendingDeleteContact.id);
      this.setData({
        pendingDeleteContact: null,
        deleteContactName: ''
      });
    }
  },

  /**
   * 删除弹窗 - 取消
   */
  onCancelDelete() {
    console.log('删除弹窗取消按钮点击');
    
    this.setData({
      showDeleteModal: false,
      pendingDeleteContact: null,
      deleteContactName: ''
    });
  },

  /**
   * 删除弹窗 - 关闭
   */
  onCloseDeleteModal() {
    console.log('删除弹窗关闭按钮点击');
    
    this.setData({
      showDeleteModal: false,
      pendingDeleteContact: null,
      deleteContactName: ''
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
          
        case 'dataUpdated':
          console.log('数据更新事件:', data);
          // 暂时禁用自动刷新提示，避免频繁弹窗
          // 只在真正有新数据时才提示
          if (data?.type === 'auto_refresh' && data?.updateCount > 0) {
            // 自动刷新页面数据，但不弹窗提示
            this.loadInitialData(true);
          }
          break;
      }
    };
    
    dataManager.addListener(this.dataListener);
  },

  /**
   * 移除数据监听器
   */
  removeDataListeners() {
    if (this.dataListener && dataManager.removeListener) {
      try {
        dataManager.removeListener(this.dataListener);
        this.dataListener = null;
        console.log('联系人页面监听器已移除');
      } catch (error) {
        console.error('移除监听器失败:', error);
        this.dataListener = null;
      }
    }
  },

  /**
   * 手势操作 - 触摸开始
   */
  onTouchStart(e) {
    const { clientX, clientY } = e.touches[0];
    const index = parseInt(e.currentTarget.dataset.index);
    
    this.setData({
      touchStartX: clientX,
      touchStartY: clientY,
      touchStartTime: Date.now(),
      isMoving: false
    });
    
    console.log('触摸开始:', { index, x: clientX, y: clientY });
  },

  /**
   * 手势操作 - 触摸移动
   */
  onTouchMove(e) {
    // 只记录移动状态，不进行任何滑动判断
    this.setData({ isMoving: true });
  },

  /**
   * 手势操作 - 触摸结束
   */
  onTouchEnd(e) {
    const { clientX, clientY } = e.changedTouches[0];
    const index = parseInt(e.currentTarget.dataset.index);
    const { touchStartX, touchStartY, touchStartTime, isMoving } = this.data;
    
    // 重置移动状态
    this.setData({ isMoving: false });
    
    if (isNaN(index)) return;
    
    const deltaX = clientX - touchStartX;
    const deltaY = clientY - touchStartY;
    const deltaTime = Date.now() - touchStartTime;
    
    console.log('触摸结束:', { 
      index, 
      deltaX, 
      deltaY, 
      deltaTime,
      isMoving,
      currentState: this.data.swipeStates[index]
    });
    
    // 严格的滑动检测条件
    const isValidSwipe = 
      isMoving && // 确实有移动
      deltaTime < 500 && // 滑动时间不超过500ms
      deltaX < -100 && // 左滑距离至少100rpx
      Math.abs(deltaY) < 50 && // 垂直偏移不超过50rpx
      Math.abs(deltaX) > Math.abs(deltaY) * 2; // 水平距离是垂直距离的2倍以上
    
    if (isValidSwipe && !this.data.swipeStates[index]) {
      // 关闭其他所有菜单
      this.closeAllSwipeMenus();
      
      // 打开当前菜单
      const newSwipeStates = { ...this.data.swipeStates };
      newSwipeStates[index] = true;
      
      this.setData({
        swipeStates: newSwipeStates,
        currentSwipeIndex: index
      });
      
      console.log('有效左滑，打开菜单:', index);
    } else if (this.data.swipeStates[index] && deltaX > 40) {
      // 右滑关闭菜单
      const newSwipeStates = { ...this.data.swipeStates };
      newSwipeStates[index] = false;
      
      this.setData({
        swipeStates: newSwipeStates,
        currentSwipeIndex: -1
      });
      
      console.log('右滑关闭菜单:', index);
    }
  },

  /**
   * 关闭所有滑动菜单
   */
  closeAllSwipeMenus() {
    const hasOpenMenus = Object.values(this.data.swipeStates).some(state => state);
    
    if (hasOpenMenus) {
      this.setData({
        swipeStates: {},
        currentSwipeIndex: -1
      });
      console.log('关闭所有滑动菜单');
    }
  },


  /**
   * 页面点击事件 - 关闭滑动菜单
   */
  onPageTap(e) {
    // 检查点击目标是否在滑动菜单区域
    const { target } = e;
    if (target && target.dataset && (target.dataset.contact || target.dataset.index !== undefined)) {
      return; // 点击的是联系人项或操作按钮
    }
    
    // 检查是否点击的是添加按钮或添加菜单
    if (target) {
      const classList = target.className || '';
      const parentClassList = target.parentNode?.className || '';
      
      if (classList.includes('add-button') || 
          classList.includes('add-text') ||
          classList.includes('add-menu') ||
          classList.includes('add-menu-item') ||
          classList.includes('menu-icon') ||
          classList.includes('menu-text') ||
          parentClassList.includes('add-button') ||
          parentClassList.includes('add-menu') ||
          parentClassList.includes('add-menu-item')) {
        return; // 点击的是添加按钮或菜单，不关闭
      }
    }
    
    // 关闭所有滑动菜单和添加菜单
    this.closeAllSwipeMenus();
    this.setData({ showAddMenu: false });
  },

  /**
   * 从通讯录导入联系人
   */
  async onImportFromPhoneBook() {
    console.log('从通讯录导入联系人');
    
    // 关闭添加菜单
    this.setData({ showAddMenu: false });
    
    try {
      // 检查是否正在导入
      if (contactImporter && contactImporter.isCurrentlyImporting()) {
        wx.showToast({
          title: '正在导入中...',
          icon: 'none',
          duration: 1500
        });
        return;
      }
      
      // 直接执行导入
      await this.executeImportFromPhoneBook();

    } catch (error) {
      console.error('通讯录导入失败:', error);
      wx.showModal({
        title: '导入失败',
        content: `导入过程中发生错误：${error.message || '未知错误'}`,
        showCancel: false
      });
    }
  },

  /**
   * 执行从通讯录导入
   */
  async executeImportFromPhoneBook() {
    try {
      if (!contactImporter) {
        wx.showModal({
          title: '错误',
          content: '导入模块不可用，请重试',
          showCancel: false
        });
        return;
      }

      wx.showLoading({
        title: '正在导入...',
        mask: true
      });

      // 开始导入流程
      const result = await contactImporter.importFromPhoneBook();
      console.log('导入结果:', result);

      wx.hideLoading();

      if (result && result.success) {
        wx.showToast({
          title: '导入成功！',
          icon: 'success',
          duration: 2000
        });

        // 导入完成后刷新列表
        await this.refreshData();
      } else {
        wx.showModal({
          title: '导入失败',
          content: result?.message || '未能成功导入联系人',
          showCancel: false
        });
      }

    } catch (error) {
      wx.hideLoading();
      console.error('导入执行失败:', error);
      
      wx.showModal({
        title: '导入失败',
        content: `导入过程中发生错误：${error.message || '未知错误'}`,
        showCancel: false
      });
    }
  },

  /**
   * 快速批量导入从通讯录
   */
  async onQuickBatchImport() {
    console.log('🚀 [调试] onQuickBatchImport 方法被调用');
    
    try {
      console.log('🔍 [调试] 检查 contactImporter 对象:', typeof contactImporter);
      
      if (!contactImporter) {
        console.error('❌ [调试] contactImporter 未正确导入');
        wx.showModal({
          title: '错误',
          content: 'contactImporter 模块导入失败',
          showCancel: false
        });
        return;
      }
      
      console.log('🔍 [调试] contactImporter 快速批量导入方法检查:', {
        isCurrentlyImporting: typeof contactImporter.isCurrentlyImporting,
        quickBatchImportFromPhoneBook: typeof contactImporter.quickBatchImportFromPhoneBook
      });
      
      // 检查是否正在导入
      if (contactImporter.isCurrentlyImporting()) {
        console.log('⚠️ [调试] 检测到导入状态异常，询问用户是否重置');
        
        // 询问用户是否重置导入状态
        const resetResult = await new Promise((resolve) => {
          wx.showModal({
            title: '导入状态异常',
            content: '检测到上次导入可能未正常结束，是否重置导入状态并继续？',
            confirmText: '重置并继续',
            cancelText: '取消',
            success: (res) => {
              resolve(res.confirm);
            },
            fail: () => {
              resolve(false);
            }
          });
        });
        
        if (!resetResult) {
          console.log('⚠️ [调试] 用户取消导入');
          return;
        }
        
        // 重置导入状态
        console.log('🔄 [调试] 用户确认重置导入状态');
        if (typeof contactImporter.resetImportState === 'function') {
          contactImporter.resetImportState();
        } else {
          console.log('⚠️ [调试] resetImportState 方法不存在，跳过重置');
        }
      }

      console.log('✅ [调试] 开始快速批量导入联系人');
      
      // 设置进度回调
      const progressCallback = (progress) => {
        console.log('📊 [调试] 进度回调:', progress);
        this.handleImportProgress(progress);
      };
      
      // 开始快速批量导入流程
      console.log('🚀 [调试] 调用 quickBatchImportFromPhoneBook');
      const result = await contactImporter.quickBatchImportFromPhoneBook(progressCallback);
      console.log('🔍 [调试] 快速批量导入结果:', result);
      
      if (result && result.success) {
        console.log('✅ [调试] 导入成功，开始刷新数据');
        // 导入成功，刷新列表
        await this.refreshData();
        
        // 显示性能统计（仅在开发模式下）
        if (wx.getAccountInfoSync().miniProgram.envVersion === 'develop') {
          const perfStats = contactImporter.getPerformanceStats();
          console.log('📊 [调试] 导入性能统计:', perfStats);
        }
      } else {
        console.log('⚠️ [调试] 导入未成功或被取消');
      }
      
    } catch (error) {
      console.error('❌ [调试] 快速批量导入失败:', error);
      console.error('❌ [调试] 错误堆栈:', error.stack);
      
      wx.showModal({
        title: '❌ 批量导入失败',
        content: `导入过程中遇到问题：\n\n${error.message || '未知错误'}\n\n请查看控制台获取详细错误信息`,
        showCancel: false,
        confirmText: '知道了',
        confirmColor: '#ff4757'
      });
    }
  },

  /**
   * 直接开始快速批量导入（跳过说明）
   */
  async onQuickBatchImportDirect() {
    console.log('🚀 [调试] onQuickBatchImportDirect 方法被调用 - 跳过说明');
    
    try {
      // 检查导入器
      if (!contactImporter) {
        throw new Error('contactImporter 模块不可用');
      }
      
      // 检查是否正在导入
      if (contactImporter.isCurrentlyImporting()) {
        console.log('⚠️ [调试] 检测到导入状态异常，询问用户是否重置');
        
        const resetResult = await new Promise((resolve) => {
          wx.showModal({
            title: '导入状态异常',
            content: '检测到上次导入可能未正常结束，是否重置导入状态并继续？',
            confirmText: '重置并继续',
            cancelText: '取消',
            success: (res) => {
              resolve(res.confirm);
            },
            fail: () => {
              resolve(false);
            }
          });
        });
        
        if (!resetResult) {
          console.log('⚠️ [调试] 用户取消导入');
          return;
        }
        
        if (typeof contactImporter.resetImportState === 'function') {
          contactImporter.resetImportState();
        }
      }

      console.log('✅ [调试] 直接开始快速批量导入联系人（跳过说明）');
      
      // 设置进度回调
      const progressCallback = this.handleImportProgress.bind(this);
      
      // 直接调用快速批量导入，但跳过说明
      console.log('🚀 [调试] 调用 quickBatchImportFromPhoneBookDirect (直接模式)');
      
      // 使用新的跳过说明弹窗的批量导入方法
      const result = await contactImporter.quickBatchImportFromPhoneBookDirect(progressCallback);
      console.log('🔍 [调试] 直接快速批量导入结果:', result);
      
      if (result && result.success) {
        console.log('✅ [调试] 导入成功');
        this.refreshData();
      } else {
        console.log('⚠️ [调试] 导入未成功或被取消');
      }
      
    } catch (error) {
      console.error('❌ [调试] 直接快速批量导入失败:', error);
      
      wx.showModal({
        title: '❌ 批量导入失败',
        content: `导入过程中遇到问题：\n\n${error.message || '未知错误'}\n\n请查看控制台获取详细错误信息`,
        showCancel: false,
        confirmText: '知道了',
        confirmColor: '#ff4757'
      });
    }
  },

  /**
   * 处理导入进度回调
   */
  handleImportProgress(progress) {
    console.log('导入进度更新:', progress);
    
    // 如果是开始阶段，显示进度组件
    if (progress.phase === 'starting') {
      this.setData({
        showImportProgress: true,
        importProgress: progress
      });
    } else {
      // 更新进度数据
      this.setData({
        importProgress: progress
      });
    }
    
    // 如果是完成或错误阶段，3秒后自动隐藏进度组件
    if (progress.phase === 'completed' || progress.phase === 'error') {
      setTimeout(() => {
        this.setData({
          showImportProgress: false,
          importProgress: {}
        });
      }, 3000);
    }
  },

  /**
   * 关闭导入进度显示
   */
  onCloseImportProgress() {
    this.setData({
      showImportProgress: false,
      importProgress: {}
    });
  },

  /**
   * 批量导入联系人（文本/文件）
   */
  async onBatchImport() {
    // 关闭添加菜单
    this.setData({ showAddMenu: false });
    
    try {
      // 检查是否正在导入
      if (contactImporter.isCurrentlyImporting()) {
        wx.showToast({
          title: '正在导入中...',
          icon: 'none',
          duration: 1500
        });
        return;
      }

      // 显示批量导入引导
      const userConfirmed = await contactImporter.showBatchImportGuide();
      if (!userConfirmed) {
        return;
      }

      // 显示文本输入对话框
      wx.showModal({
        title: '批量导入联系人',
        content: '请粘贴联系人数据，每行一个联系人：\n姓名,手机,公司,职位',
        editable: true,
        placeholderText: '张三,13800138000,阿里巴巴,工程师\n李四,13900139000,腾讯,设计师',
        confirmText: '开始解析',
        cancelText: '取消',
        success: async (res) => {
          if (res.confirm && res.content) {
            await this.processBatchImportText(res.content.trim());
          }
        }
      });

    } catch (error) {
      console.error('批量导入失败:', error);
      
      wx.showToast({
        title: '导入失败: ' + (error.message || '未知错误'),
        icon: 'none',
        duration: 3000
      });
    }
  },

  /**
   * 处理批量导入文本
   */
  async processBatchImportText(text) {
    try {
      if (!text || !text.trim()) {
        wx.showToast({
          title: '请输入联系人数据',
          icon: 'none',
          duration: 2000
        });
        return;
      }

      // 解析文本数据
      const contacts = contactImporter.parseTextContacts(text);
      
      if (contacts.length === 0) {
        wx.showToast({
          title: '未能解析到有效联系人',
          icon: 'none',
          duration: 2000
        });
        return;
      }

      // 显示解析结果预览
      await this.showBatchImportPreview(contacts);

    } catch (error) {
      console.error('处理批量导入文本失败:', error);
      wx.showToast({
        title: '解析失败: ' + (error.message || '未知错误'),
        icon: 'none',
        duration: 3000
      });
    }
  },

  /**
   * 显示批量导入预览
   */
  async showBatchImportPreview(contacts) {
    try {
      // 生成预览文本
      let previewText = `解析到 ${contacts.length} 个联系人：\n\n`;
      contacts.slice(0, 5).forEach((contact, index) => {
        previewText += `${index + 1}. ${contact.name}`;
        if (contact.phone) previewText += ` - ${contact.phone}`;
        if (contact.company) previewText += ` - ${contact.company}`;
        if (contact.position) previewText += ` - ${contact.position}`;
        previewText += '\n';
      });
      
      if (contacts.length > 5) {
        previewText += `...\n还有 ${contacts.length - 5} 个联系人`;
      }
      
      previewText += '\n\n确认批量导入这些联系人吗？';

      // 显示确认对话框
      wx.showModal({
        title: '确认批量导入',
        content: previewText,
        confirmText: '确认导入',
        cancelText: '取消',
        success: async (res) => {
          if (res.confirm) {
            await this.executeBatchImport(contacts);
          }
        }
      });

    } catch (error) {
      console.error('显示批量导入预览失败:', error);
      throw error;
    }
  },

  /**
   * 执行批量导入
   */
  async executeBatchImport(contacts) {
    try {
      wx.showLoading({
        title: '正在批量导入...',
        mask: true
      });

      // 执行批量导入
      const result = await contactImporter.batchImportContacts(contacts, 'create');
      
      wx.hideLoading();

      // 显示导入结果
      const stats = result.stats;
      let message = `导入完成！\n`;
      message += `总计: ${stats.total}个\n`;
      message += `成功: ${stats.success}个\n`;
      if (stats.errors > 0) message += `失败: ${stats.errors}个\n`;
      if (stats.duplicates > 0) message += `跳过: ${stats.duplicates}个`;

      wx.showModal({
        title: '批量导入结果',
        content: message,
        showCancel: false,
        confirmText: '知道了',
        success: () => {
          // 刷新联系人列表
          this.refreshData();
        }
      });

      console.log('批量导入完成:', result);

    } catch (error) {
      wx.hideLoading();
      console.error('执行批量导入失败:', error);
      
      wx.showModal({
        title: '批量导入失败',
        content: error.message || '导入过程中出现错误，请重试',
        showCancel: false
      });
    }
  },

});