/**
 * 主题管理器 - 统一管理深色模式
 */

const STORAGE_KEY = 'app_theme';
const ACCENT_COLOR_KEY = 'app_accent_color';

class ThemeManager {
  constructor() {
    this.currentTheme = 'light'; // 默认浅色主题
    this.currentAccentColor = 'default'; // 默认主题色
    this.listeners = [];
    
    // 可用的主题色配置
    this.accentColors = {
      default: {
        name: '微信绿',
        primary: '#07c160',
        primaryDark: '#06ae56',
        secondary: '#05994d',
        light: 'rgba(7, 193, 96, 0.1)',
        description: '经典微信绿色主题'
      },
      blue: {
        name: '天空蓝',
        primary: '#1890ff',
        primaryDark: '#1677ff',
        secondary: '#0958d9',
        light: 'rgba(24, 144, 255, 0.1)',
        description: '清新天空蓝色主题'
      },
      purple: {
        name: '优雅紫',
        primary: '#722ed1',
        primaryDark: '#531dab',
        secondary: '#391085',
        light: 'rgba(114, 46, 209, 0.1)',
        description: '优雅紫色主题'
      },
      orange: {
        name: '活力橙',
        primary: '#fa8c16',
        primaryDark: '#d46b08',
        secondary: '#ad4e00',
        light: 'rgba(250, 140, 22, 0.1)',
        description: '活力橙色主题'
      },
      pink: {
        name: '温馨粉',
        primary: '#eb2f96',
        primaryDark: '#c41d7f',
        secondary: '#9e1068',
        light: 'rgba(235, 47, 150, 0.1)',
        description: '温馨粉色主题'
      },
      red: {
        name: '激情红',
        primary: '#f5222d',
        primaryDark: '#cf1322',
        secondary: '#a8071a',
        light: 'rgba(245, 34, 45, 0.1)',
        description: '激情红色主题'
      }
    };
  }

  /**
   * 初始化主题
   */
  init() {
    // 从存储中读取主题设置
    try {
      const savedTheme = wx.getStorageSync(STORAGE_KEY);
      if (savedTheme === 'dark' || savedTheme === 'light') {
        this.currentTheme = savedTheme;
      } else {
        // 检查系统主题（如果支持）
        const systemInfo = wx.getSystemInfoSync();
        if (systemInfo.theme) {
          this.currentTheme = systemInfo.theme;
        }
      }
      
      // 读取主题色设置
      const savedAccentColor = wx.getStorageSync(ACCENT_COLOR_KEY);
      if (savedAccentColor && this.accentColors[savedAccentColor]) {
        this.currentAccentColor = savedAccentColor;
      }
    } catch (e) {
      console.error('读取主题设置失败:', e);
    }
    
    // 监听系统主题变化
    if (wx.onThemeChange) {
      wx.onThemeChange((result) => {
        console.log('系统主题变化:', result.theme);
        // 如果用户没有手动设置，跟随系统
        const manualTheme = wx.getStorageSync(STORAGE_KEY + '_manual');
        if (!manualTheme) {
          this.setTheme(result.theme);
        }
      });
    }
    
    return this.currentTheme;
  }

  /**
   * 获取当前主题
   */
  getTheme() {
    return this.currentTheme;
  }

  /**
   * 设置主题
   */
  setTheme(theme) {
    if (theme !== 'light' && theme !== 'dark') {
      console.error('无效的主题:', theme);
      return false;
    }
    
    this.currentTheme = theme;
    
    // 保存到存储
    try {
      wx.setStorageSync(STORAGE_KEY, theme);
      wx.setStorageSync(STORAGE_KEY + '_manual', true); // 标记为手动设置
    } catch (e) {
      console.error('保存主题设置失败:', e);
    }
    
    // 通知所有监听器
    this.notifyListeners(theme);
    
    // 更新导航栏颜色
    this.updateNavigationBar(theme);
    
    return true;
  }

  /**
   * 切换主题
   */
  toggleTheme() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    return this.setTheme(newTheme);
  }

  /**
   * 获取当前主题色
   */
  getAccentColor() {
    return this.currentAccentColor;
  }

  /**
   * 设置主题色
   */
  setAccentColor(colorKey) {
    if (!this.accentColors[colorKey]) {
      console.error('无效的主题色:', colorKey);
      return false;
    }
    
    this.currentAccentColor = colorKey;
    
    // 保存到存储
    try {
      wx.setStorageSync(ACCENT_COLOR_KEY, colorKey);
    } catch (e) {
      console.error('保存主题色设置失败:', e);
    }
    
    // 通知所有监听器主题色变化
    this.notifyListeners(this.currentTheme, colorKey);
    
    return true;
  }

  /**
   * 获取所有可用的主题色
   */
  getAvailableAccentColors() {
    return Object.keys(this.accentColors).map(key => ({
      key,
      ...this.accentColors[key]
    }));
  }

  /**
   * 获取当前主题色配置
   */
  getCurrentAccentColorConfig() {
    return this.accentColors[this.currentAccentColor] || this.accentColors.default;
  }

  /**
   * 添加主题变化监听器
   */
  addListener(callback) {
    if (typeof callback === 'function') {
      this.listeners.push(callback);
    }
  }

  /**
   * 移除监听器
   */
  removeListener(callback) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  /**
   * 通知所有监听器
   */
  notifyListeners(theme, accentColor) {
    this.listeners.forEach(callback => {
      try {
        callback(theme, accentColor || this.currentAccentColor);
      } catch (e) {
        console.error('主题监听器执行失败:', e);
      }
    });
  }

  /**
   * 更新导航栏颜色
   */
  updateNavigationBar(theme) {
    const isDark = theme === 'dark';
    wx.setNavigationBarColor({
      frontColor: isDark ? '#ffffff' : '#000000',
      backgroundColor: isDark ? '#1a1a1a' : '#ffffff',
      animation: {
        duration: 200,
        timingFunc: 'easeInOut'
      }
    });
  }

  /**
   * 获取主题相关的样式类名
   */
  getThemeClass() {
    return `theme-${this.currentTheme}`;
  }

  /**
   * 获取主题色彩配置
   */
  getThemeColors() {
    const accentConfig = this.getCurrentAccentColorConfig();
    const isDark = this.currentTheme === 'dark';
    
    const baseColors = {
      light: {
        // 基础颜色
        bgPrimary: '#ffffff',
        bgSecondary: '#f5f5f5',
        bgTertiary: '#fafafa',
        bgCard: '#ffffff',
        
        // 文字颜色
        textPrimary: '#333333',
        textSecondary: '#666666',
        textTertiary: '#999999',
        textPlaceholder: '#cccccc',
        
        // 边框和分割线
        border: '#e5e5e5',
        divider: '#eeeeee',
        
        // 系统功能色
        warning: '#ff976a',
        error: '#ee0a24',
        info: '#1989fa',
        
        // 阴影
        shadow: 'rgba(0, 0, 0, 0.08)',
        shadowLight: 'rgba(0, 0, 0, 0.04)'
      },
      dark: {
        // 基础颜色
        bgPrimary: '#1a1a1a',
        bgSecondary: '#252525',
        bgTertiary: '#2a2a2a',
        bgCard: '#2d2d2d',
        
        // 文字颜色
        textPrimary: '#ffffff',
        textSecondary: '#cccccc',
        textTertiary: '#999999',
        textPlaceholder: '#666666',
        
        // 边框和分割线
        border: '#3a3a3a',
        divider: '#333333',
        
        // 系统功能色
        warning: '#ff8f5a',
        error: '#dc0a1a',
        info: '#1080e8',
        
        // 阴影
        shadow: 'rgba(0, 0, 0, 0.3)',
        shadowLight: 'rgba(0, 0, 0, 0.2)'
      }
    };
    
    const colors = { ...baseColors[this.currentTheme] };
    
    // 应用当前主题色
    colors.primary = isDark ? accentConfig.primaryDark : accentConfig.primary;
    colors.primaryLight = accentConfig.light;
    colors.primarySecondary = accentConfig.secondary;
    colors.success = colors.primary;
    
    return colors;
  }

  /**
   * 应用主题到页面
   */
  applyToPage(page) {
    if (!page) return;
    
    const theme = this.currentTheme;
    const colors = this.getThemeColors();
    const accentColor = this.currentAccentColor;
    
    // 设置页面数据
    page.setData({
      theme: theme,
      themeClass: this.getThemeClass(),
      themeColors: colors,
      accentColor: accentColor,
      accentColorConfig: this.getCurrentAccentColorConfig()
    });
    
    // 添加主题变化监听
    const listener = (newTheme, newAccentColor) => {
      page.setData({
        theme: newTheme,
        themeClass: `theme-${newTheme}`,
        themeColors: this.getThemeColors(),
        accentColor: newAccentColor || this.currentAccentColor,
        accentColorConfig: this.getCurrentAccentColorConfig()
      });
    };
    
    this.addListener(listener);
    
    // 页面卸载时移除监听
    const originalOnUnload = page.onUnload;
    page.onUnload = function() {
      themeManager.removeListener(listener);
      if (originalOnUnload) {
        originalOnUnload.call(this);
      }
    };
  }
}

// 创建单例
const themeManager = new ThemeManager();

// 自动初始化
themeManager.init();

module.exports = themeManager;