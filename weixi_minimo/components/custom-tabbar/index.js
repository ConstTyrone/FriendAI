import themeManager from '../../utils/theme-manager';

Component({
  properties: {
    current: {
      type: String,
      value: 'contact-list'
    }
  },
  
  data: {
    tabs: [
      {
        key: 'contact-list',
        text: '联系人',
        icon: 'usergroup',
        path: '/pages/contact-list/contact-list'
      },
      {
        key: 'intent-manager',
        text: '意图',
        icon: 'filter',  // 使用筛选图标表示意图匹配
        path: '/pages/intent-manager/intent-manager',
        highlight: true  // 突出显示这个重要功能
      },
      {
        key: 'ai-search', 
        text: '搜索',
        icon: 'search',  // 改为搜索图标更直观
        path: '/pages/ai-search/ai-search'
      },
      {
        key: 'settings',
        text: '设置',
        icon: 'tools',
        path: '/pages/settings/settings'
      }
    ]
  },

  lifetimes: {
    attached() {
      // 应用主题
      themeManager.applyToPage(this);
    }
  },

  methods: {
    onTabTap(event) {
      const { key, path } = event.currentTarget.dataset;
      
      if (key === this.properties.current) {
        return; // 当前页面不需要跳转
      }

      // 触发自定义事件
      this.triggerEvent('tabchange', { key, path });

      // 获取当前页面栈
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      const currentRoute = currentPage.route;

      // 如果是主要页面之间的跳转，使用redirectTo避免页面栈积累
      const mainPages = [
        'pages/contact-list/contact-list',
        'pages/intent-manager/intent-manager',
        'pages/ai-search/ai-search', 
        'pages/settings/settings'
      ];

      if (mainPages.includes(currentRoute)) {
        wx.redirectTo({
          url: path
        });
      } else {
        // 从其他页面跳转到主页面，使用navigateTo
        wx.navigateTo({
          url: path
        });
      }
    }
  }
});