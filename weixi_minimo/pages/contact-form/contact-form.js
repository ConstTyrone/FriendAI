import { PAGE_ROUTES } from '../../utils/constants';
import { isPhone, isEmail, isNotEmpty, isValidMaritalStatus, isValidAssetLevel, isValidGender } from '../../utils/validator';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';

Page({
  data: {
    // 表单模式：'add' 新增，'edit' 编辑
    mode: 'add',
    contactId: '',
    
    // 表单数据
    formData: {
      name: '',
      phone: '',
      wechat_id: '',
      email: '',
      company: '',
      position: '',
      address: '',
      notes: '',
      tags: [],
      // 新增字段
      gender: '',
      age: '',
      marital_status: '',
      education: '',
      asset_level: '',
      personality: ''
    },
    
    // 原始数据（编辑模式下用于比较变化）
    originalData: {},
    
    // 表单验证状态
    formErrors: {},
    
    // 页面状态
    loading: false,
    saving: false, // 确保初始状态为false
    
    // 标签相关
    tagInputValue: '',
    showTagInput: false,
    
    // 对话框状态
    showCancelDialog: false,
    
    // 选择器选项
    genderOptions: ['男', '女', '未知'],
    genderIndex: -1,
    maritalOptions: ['未婚', '已婚已育', '已婚未育', '离异', '未知'],
    maritalIndex: -1,
    assetOptions: ['高', '中', '低', '未知'],
    assetIndex: -1
  },

  onLoad(options) {
    console.log('========= 联系人表单页面加载 =========', options);
    
    const mode = options.mode || 'add';
    const contactId = options.id || '';
    
    this.setData({ 
      mode, 
      contactId,
      saving: false // 确保按钮可点击
    });
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: mode === 'edit' ? '编辑联系人' : '新增联系人'
    });
    
    // 初始化页面数据
    this.initPageData();
  },

  onShow() {
    console.log('========= 联系人表单页面显示 =========');
    // 确保按钮状态正确
    console.log('saving状态:', this.data.saving);
  },

  onReady() {
    console.log('联系人表单页面准备就绪');
  },

  onHide() {
    console.log('联系人表单页面隐藏');
  },

  onUnload() {
    console.log('联系人表单页面卸载');
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
          content: '请先登录再编辑联系人',
          showCancel: false,
          success: () => {
            wx.navigateBack();
          }
        });
        return;
      }
      
      // 如果是编辑模式，加载联系人数据
      if (this.data.mode === 'edit' && this.data.contactId) {
        await this.loadContactData();
      }
      
      console.log('页面数据初始化完成');
    } catch (error) {
      console.error('初始化页面数据失败:', error);
      
      wx.showModal({
        title: '加载失败',
        content: error.message || '无法加载联系人信息',
        showCancel: false,
        success: () => {
          wx.navigateBack();
        }
      });
    }
  },

  /**
   * 加载联系人数据（编辑模式）
   */
  async loadContactData() {
    try {
      this.setData({ loading: true });
      
      const contact = await dataManager.getContactDetail(this.data.contactId);
      
      if (!contact) {
        throw new Error('联系人不存在');
      }
      
      // 处理联系人数据 - 适配后端字段名
      const formData = {
        name: contact.profile_name || contact.name || '',
        phone: contact.phone || '',
        wechat_id: contact.wechat_id || '',
        email: contact.email || '',
        company: contact.company || '',
        position: contact.position || '',
        address: contact.location || contact.address || '',
        notes: contact.ai_summary || contact.notes || '',
        tags: Array.isArray(contact.tags) ? contact.tags : [],
        // 额外字段
        gender: contact.gender || '',
        age: contact.age || '',
        marital_status: contact.marital_status || '',
        education: contact.education || '',
        asset_level: contact.asset_level || '',
        personality: contact.personality || ''
      };
      
      // 设置选择器索引
      const genderIndex = this.data.genderOptions.indexOf(formData.gender);
      const maritalIndex = this.data.maritalOptions.indexOf(formData.marital_status);
      const assetIndex = this.data.assetOptions.indexOf(formData.asset_level);
      
      this.setData({
        formData,
        originalData: JSON.parse(JSON.stringify(formData)),
        loading: false,
        genderIndex: genderIndex >= 0 ? genderIndex : -1,
        maritalIndex: maritalIndex >= 0 ? maritalIndex : -1,
        assetIndex: assetIndex >= 0 ? assetIndex : -1
      });
      
      console.log('联系人数据加载完成:', formData);
    } catch (error) {
      console.error('加载联系人数据失败:', error);
      
      this.setData({ loading: false });
      
      throw error;
    }
  },

  /**
   * 表单字段变化处理
   */
  onFieldChange(event) {
    const { field } = event.currentTarget.dataset;
    const value = event.detail.value;
    
    this.setData({
      [`formData.${field}`]: value,
      [`formErrors.${field}`]: '' // 清除该字段的错误信息
    });
    
    console.log(`字段 ${field} 更新为:`, value);
  },

  /**
   * 添加标签
   */
  onAddTag() {
    console.log('点击添加标签按钮');
    this.setData({ showTagInput: true });
  },

  /**
   * 标签输入变化
   */
  onTagInputChange(event) {
    this.setData({
      tagInputValue: event.detail.value
    });
  },
  
  /**
   * 选择器变化处理
   */
  onPickerChange(event) {
    const { field } = event.currentTarget.dataset;
    const index = event.detail.value;
    
    if (field === 'gender') {
      this.setData({
        [`formData.gender`]: this.data.genderOptions[index],
        genderIndex: index
      });
    } else if (field === 'marital_status') {
      this.setData({
        [`formData.marital_status`]: this.data.maritalOptions[index],
        maritalIndex: index
      });
    } else if (field === 'asset_level') {
      this.setData({
        [`formData.asset_level`]: this.data.assetOptions[index],
        assetIndex: index
      });
    }
    
    console.log(`${field} 更新为:`, event.detail.value);
  },

  /**
   * 确认添加标签
   */
  onConfirmAddTag() {
    console.log('点击确认添加标签按钮');
    const tagValue = this.data.tagInputValue.trim();
    console.log('标签值:', tagValue);
    
    if (!tagValue) {
      wx.showToast({
        title: '请输入标签内容',
        icon: 'none'
      });
      return;
    }
    
    const currentTags = this.data.formData.tags;
    
    // 检查标签是否已存在
    if (currentTags.includes(tagValue)) {
      wx.showToast({
        title: '标签已存在',
        icon: 'none'
      });
      return;
    }
    
    // 添加标签
    const newTags = [...currentTags, tagValue];
    
    this.setData({
      'formData.tags': newTags,
      tagInputValue: '',
      showTagInput: false
    });
    
    console.log('添加标签:', tagValue);
  },

  /**
   * 取消添加标签
   */
  onCancelAddTag() {
    this.setData({
      tagInputValue: '',
      showTagInput: false
    });
  },

  /**
   * 删除标签
   */
  onDeleteTag(event) {
    const { index } = event.currentTarget.dataset;
    const currentTags = this.data.formData.tags;
    const newTags = currentTags.filter((_, i) => i !== index);
    
    this.setData({
      'formData.tags': newTags
    });
    
    console.log('删除标签，索引:', index);
  },

  /**
   * 验证表单
   */
  validateForm() {
    const { formData } = this.data;
    const errors = {};
    
    // 验证必填字段
    if (!isNotEmpty(formData.name)) {
      errors.name = '请输入联系人姓名';
    }
    
    // 验证手机号
    if (formData.phone && !isPhone(formData.phone)) {
      errors.phone = '请输入正确的手机号码';
    }
    
    // 验证邮箱
    if (formData.email && !isEmail(formData.email)) {
      errors.email = '请输入正确的邮箱地址';
    }
    
    // 验证微信号
    if (formData.wechat_id && formData.wechat_id.length < 6) {
      errors.wechat_id = '微信号长度至少6位';
    }
    
    // 验证性别
    if (formData.gender && !isValidGender(formData.gender)) {
      errors.gender = '请选择正确的性别';
    }
    
    // 验证婚姻状况
    if (formData.marital_status && !isValidMaritalStatus(formData.marital_status)) {
      errors.marital_status = '请选择正确的婚姻状况';
    }
    
    // 验证资产水平
    if (formData.asset_level && !isValidAssetLevel(formData.asset_level)) {
      errors.asset_level = '请选择正确的资产水平';
    }
    
    console.log('表单验证结果:', { errors, hasErrors: Object.keys(errors).length > 0 });
    
    this.setData({ formErrors: errors });
    
    return Object.keys(errors).length === 0;
  },

  /**
   * 检查表单是否有变化
   */
  hasFormChanged() {
    if (this.data.mode === 'add') {
      // 新增模式下，检查是否有任何非空字段
      const { formData } = this.data;
      return Object.values(formData).some(value => {
        if (Array.isArray(value)) {
          return value.length > 0;
        }
        return value && value.trim();
      });
    } else {
      // 编辑模式下，比较与原始数据的差异
      return JSON.stringify(this.data.formData) !== JSON.stringify(this.data.originalData);
    }
  },

  /**
   * 保存联系人
   */
  async onSave() {
    console.log('🚀🚀🚀========= onSave方法被调用 =========🚀🚀🚀');
    console.log('当前时间:', new Date().toISOString());
    console.log('保存状态:', this.data.saving);
    console.log('表单模式:', this.data.mode);
    
    // 立即显示一个toast确保方法被调用
    wx.showToast({
      title: 'onSave被调用了',
      icon: 'none',
      duration: 1000
    });
    
    if (this.data.saving) {
      console.log('正在保存中，忽略重复点击');
      return;
    }
    
    console.log('当前表单数据:', JSON.stringify(this.data.formData, null, 2));
    
    // 验证表单
    if (!this.validateForm()) {
      console.log('表单验证失败:', this.data.formErrors);
      wx.showToast({
        title: '请检查表单内容',
        icon: 'none'
      });
      return;
    }
    
    try {
      console.log('开始保存联系人...');
      this.setData({ saving: true });
      
      wx.showLoading({
        title: this.data.mode === 'edit' ? '保存中...' : '创建中...',
        mask: true
      });
      
      const { formData } = this.data;
      
      // 准备提交的数据 - 安全处理字符串
      const submitData = {
        name: (formData.name || '').trim(),
        phone: (formData.phone || '').trim(),
        wechat_id: (formData.wechat_id || '').trim(),
        email: (formData.email || '').trim(),
        company: (formData.company || '').trim(),
        position: (formData.position || '').trim(),
        address: (formData.address || '').trim(),
        notes: (formData.notes || '').trim(),
        tags: formData.tags || [],
        // 新增字段
        gender: formData.gender || '未知',
        age: (formData.age || '').trim(),
        marital_status: formData.marital_status || '未知',
        education: (formData.education || '').trim(),
        asset_level: formData.asset_level || '未知',
        personality: (formData.personality || '').trim()
      };
      
      console.log('提交数据:', submitData);
      
      let result;
      
      if (this.data.mode === 'edit') {
        console.log('编辑模式，联系人ID:', this.data.contactId);
        result = await dataManager.updateProfile(this.data.contactId, submitData);
      } else {
        console.log('创建模式');
        result = await dataManager.createProfile(submitData);
      }
      
      console.log('API调用成功，结果:', result);
      
      wx.hideLoading();
      
      wx.showToast({
        title: this.data.mode === 'edit' ? '保存成功' : '创建成功',
        icon: 'success',
        duration: 2000
      });
      
      // 延迟返回，让用户看到成功提示
      setTimeout(() => {
        wx.navigateBack();
      }, 2000);
      
      console.log('联系人保存成功:', result);
    } catch (error) {
      console.error('保存联系人失败:', error);
      console.error('错误详情:', {
        message: error.message,
        stack: error.stack,
        data: error.data
      });
      
      wx.hideLoading();
      
      this.setData({ saving: false });
      
      wx.showModal({
        title: '保存失败',
        content: error.message || '请检查网络连接后重试',
        showCancel: false
      });
    }
  },

  /**
   * 取消编辑
   */
  onCancel() {
    // 检查是否有未保存的变化
    if (this.hasFormChanged()) {
      this.setData({ showCancelDialog: true });
    } else {
      wx.navigateBack();
    }
  },

  /**
   * 确认取消
   */
  onConfirmCancel() {
    this.setData({ showCancelDialog: false });
    wx.navigateBack();
  },

  /**
   * 取消取消
   */
  onCancelCancel() {
    this.setData({ showCancelDialog: false });
  },

  /**
   * 清空表单
   */
  onClearForm() {
    wx.showModal({
      title: '清空表单',
      content: '确定要清空所有表单内容吗？',
      success: (res) => {
        if (res.confirm) {
          const emptyFormData = {
            name: '',
            phone: '',
            wechat_id: '',
            email: '',
            company: '',
            position: '',
            address: '',
            notes: '',
            tags: []
          };
          
          this.setData({
            formData: emptyFormData,
            formErrors: {}
          });
          
          wx.showToast({
            title: '表单已清空',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * 获取错误信息
   */
  getFieldError(field) {
    return this.data.formErrors[field] || '';
  },

  /**
   * 获取标签颜色主题
   */
  getTagTheme(index) {
    const themes = ['primary', 'success', 'warning', 'danger', 'default'];
    return themes[index % themes.length];
  },

  /**
   * 阻止事件冒泡
   */
  onStopPropagation() {
    // 阻止事件冒泡
  },

  /**
   * 测试按钮点击
   */
  testButtonClick() {
    console.log('========= 测试按钮被点击了！ =========');
    wx.showToast({
      title: '测试按钮工作正常！',
      icon: 'success'
    });
  }
});