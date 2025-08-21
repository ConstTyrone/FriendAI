/**
 * 联系人多选组件
 * 提供真正的批量选择界面，支持多选、全选、搜索等功能
 */
Component({
  properties: {
    // 是否显示选择器
    visible: {
      type: Boolean,
      value: false
    },
    // 最大选择数量
    maxCount: {
      type: Number,
      value: 20
    }
  },

  data: {
    // 所有联系人列表
    allContacts: [],
    // 显示的联系人列表（搜索过滤后）
    displayContacts: [],
    // 已选择的联系人ID集合
    selectedIds: new Set(),
    // 搜索关键词
    searchKeyword: '',
    // 是否全选状态
    isAllSelected: false,
    // 加载状态
    loading: false
  },

  methods: {
    /**
     * 显示选择器
     */
    show() {
      this.setData({ visible: true });
      this.loadPhoneContacts();
    },

    /**
     * 隐藏选择器
     */
    hide() {
      this.setData({ visible: false });
      this.resetData();
    },

    /**
     * 重置数据
     */
    resetData() {
      this.setData({
        allContacts: [],
        displayContacts: [],
        selectedIds: new Set(),
        searchKeyword: '',
        isAllSelected: false,
        loading: false
      });
    },

    /**
     * 加载手机通讯录联系人
     * 注意：微信小程序无法直接获取所有联系人，这里模拟实现
     */
    async loadPhoneContacts() {
      this.setData({ loading: true });

      try {
        // 由于微信限制，我们创建一个引导用户选择的界面
        const mockContacts = [
          { id: '1', name: '张三', phone: '13800138001' },
          { id: '2', name: '李四', phone: '13800138002' },
          { id: '3', name: '王五', phone: '13800138003' },
          { id: '4', name: '赵六', phone: '13800138004' },
          { id: '5', name: '钱七', phone: '13800138005' },
          { id: '6', name: '孙八', phone: '13800138006' },
          { id: '7', name: '周九', phone: '13800138007' },
          { id: '8', name: '吴十', phone: '13800138008' }
        ];

        this.setData({
          allContacts: mockContacts,
          displayContacts: mockContacts,
          loading: false
        });

      } catch (error) {
        console.error('加载联系人失败:', error);
        this.setData({ loading: false });
        
        wx.showToast({
          title: '加载联系人失败',
          icon: 'none'
        });
      }
    },

    /**
     * 搜索联系人
     */
    onSearchInput(e) {
      const keyword = e.detail.value.toLowerCase();
      this.setData({ searchKeyword: keyword });
      
      const filtered = this.data.allContacts.filter(contact => 
        contact.name.toLowerCase().includes(keyword) ||
        contact.phone.includes(keyword)
      );
      
      this.setData({ displayContacts: filtered });
    },

    /**
     * 切换联系人选择状态
     */
    onContactToggle(e) {
      const contactId = e.currentTarget.dataset.id;
      const selectedIds = new Set(this.data.selectedIds);
      
      if (selectedIds.has(contactId)) {
        selectedIds.delete(contactId);
      } else {
        if (selectedIds.size >= this.properties.maxCount) {
          wx.showToast({
            title: `最多选择${this.properties.maxCount}个联系人`,
            icon: 'none'
          });
          return;
        }
        selectedIds.add(contactId);
      }
      
      const isAllSelected = selectedIds.size === this.data.displayContacts.length && 
                           this.data.displayContacts.length > 0;
      
      this.setData({
        selectedIds: selectedIds,
        isAllSelected: isAllSelected
      });
    },

    /**
     * 全选/取消全选
     */
    onToggleAll() {
      const selectedIds = new Set();
      const isAllSelected = !this.data.isAllSelected;
      
      if (isAllSelected) {
        // 检查数量限制
        if (this.data.displayContacts.length > this.properties.maxCount) {
          wx.showToast({
            title: `最多选择${this.properties.maxCount}个联系人`,
            icon: 'none'
          });
          return;
        }
        
        // 全选当前显示的联系人
        this.data.displayContacts.forEach(contact => {
          selectedIds.add(contact.id);
        });
      }
      
      this.setData({
        selectedIds: selectedIds,
        isAllSelected: isAllSelected
      });
    },

    /**
     * 确认选择
     */
    onConfirm() {
      const selectedContacts = this.data.allContacts.filter(contact => 
        this.data.selectedIds.has(contact.id)
      );
      
      if (selectedContacts.length === 0) {
        wx.showToast({
          title: '请选择至少一个联系人',
          icon: 'none'
        });
        return;
      }
      
      // 触发选择完成事件
      this.triggerEvent('confirm', {
        contacts: selectedContacts,
        count: selectedContacts.length
      });
      
      this.hide();
    },

    /**
     * 取消选择
     */
    onCancel() {
      this.triggerEvent('cancel');
      this.hide();
    }
  }
});