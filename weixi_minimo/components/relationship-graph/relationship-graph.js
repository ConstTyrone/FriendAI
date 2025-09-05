import GraphDataProcessor from '../../utils/graph-data-processor';
import AdvancedGraphRenderer from '../../utils/advanced-graph-renderer';
import AdvancedLayoutEngine from '../../utils/advanced-layout-engine';

Component({
  properties: {
    // 关系数据
    relationships: {
      type: Array,
      value: []
    },
    
    // 联系人数据
    profiles: {
      type: Array,
      value: []
    },
    
    // 中心节点ID
    centerNodeId: {
      type: Number,
      value: null
    },
    
    // 组件宽度高度
    width: {
      type: Number,
      value: 350
    },
    
    height: {
      type: Number,
      value: 400
    }
  },
  
  data: {
    // 画布尺寸
    canvasWidth: 350,
    canvasHeight: 400,
    
    // 图谱数据
    graphData: {
      nodes: [],
      links: [],
      stats: {}
    },
    
    // 显示设置
    showStats: true,
    showLegend: true,
    showNodeDetail: false,
    showLinkDetail: false,
    showSettings: false,
    
    // 布局设置
    layoutType: 'circle',
    minConfidence: 0.3,
    maxDepth: 2,
    
    // 交互状态
    loading: false,
    selectedNode: null,
    selectedLink: null,
    
    // 画布状态
    scale: 1,
    translateX: 0,
    translateY: 0,
    
    // 触摸状态
    lastTouchX: 0,
    lastTouchY: 0,
    touching: false,
    multiTouch: false
  },
  
  lifetimes: {
    attached() {
      // 使用传入的尺寸或默认尺寸
      const width = this.data.width || 350;
      const height = this.data.height || 400;
      
      this.setData({
        canvasWidth: width,
        canvasHeight: height
      });
      
      // 初始化触摸检测属性
      this.touchStartTime = null;
      this.touchStartX = null;
      this.touchStartY = null;
      this.hasMoved = false;
      
      // 初始化高级引擎
      this.layoutEngine = new AdvancedLayoutEngine({
        forceLayout: {
          attraction: 0.12,
          repulsion: 1200,
          damping: 0.88,
          iterations: 120,
          threshold: 0.008,
          centerForce: 0.06
        }
      });
    },
    
    ready() {
      // 延迟初始化Canvas，确保DOM已准备好
      this.initCanvasWithRetry();
    },
    
    detached() {
      // 清理资源
      if (this.renderer) {
        this.renderer.destroy();
        this.renderer = null;
      }
      this.layoutEngine = null;
    }
  },
  
  observers: {
    'relationships, profiles, centerNodeId': function(relationships, profiles, centerNodeId) {
      // 确保有数据才处理
      if (!profiles || profiles.length === 0) {
        return;
      }
      
      // 标记数据更新，等待Canvas就绪
      this._pendingDataUpdate = true;
      
      // 确保Canvas已经初始化再处理数据
      if (this.canvas && this.ctx) {
        this._pendingDataUpdate = false;
        this.processGraphData();
      }
      // Canvas未就绪时等待initCanvas完成后处理
    },
    'width, height': function(width, height) {
      if (width && height) {
        this.setData({
          canvasWidth: width,
          canvasHeight: height
        });
        // 重新初始化Canvas
        setTimeout(() => {
          this.initCanvas();
        }, 50);
      }
    }
  },
  
  methods: {
    /**
     * 标准化置信度分数
     * @param {any} value - 原始置信度值
     * @returns {number} - 标准化后的置信度分数 (0-1)
     */
    normalizeConfidenceScore(value) {
      // 处理undefined, null, 空字符串
      if (value === undefined || value === null || value === '') {
        console.warn('置信度值为空，使用默认值0.5');
        return 0.5;
      }
      
      // 转换为数字
      let score = parseFloat(value);
      
      // 处理NaN
      if (isNaN(score)) {
        console.warn('置信度值无法解析为数字:', value, '使用默认值0.5');
        return 0.5;
      }
      
      // 如果值大于1，假设是百分比形式，转换为小数
      if (score > 1) {
        score = score / 100;
      }
      
      // 确保在0-1范围内
      score = Math.max(0, Math.min(1, score));
      
      return score;
    },

    /**
     * 带重试机制的Canvas初始化
     */
    initCanvasWithRetry(retryCount = 0) {
      const maxRetries = 3;
      const retryDelay = [100, 300, 500]; // 递增延迟
      
      this.initCanvas().then((success) => {
        if (success) {
          // 如果有待处理的数据更新，立即处理
          if (this._pendingDataUpdate) {
            this._pendingDataUpdate = false;
            setTimeout(() => {
              this.processGraphData();
            }, 50);
          }
        } else if (retryCount < maxRetries) {
          setTimeout(() => {
            this.initCanvasWithRetry(retryCount + 1);
          }, retryDelay[retryCount]);
        } else {
          console.error('Canvas初始化失败');
          this.setData({ loading: false, error: 'Canvas初始化失败' });
        }
      });
    },
    
    /**
     * 初始化画布
     */
    initCanvas() {
      return new Promise((resolve) => {
        const query = this.createSelectorQuery();
        query.select('.graph-canvas')
          .fields({ node: true, size: true })
          .exec((res) => {
            if (res && res[0] && res[0].node) {
              const canvas = res[0].node;
              
              try {
                const ctx = canvas.getContext('2d');
                if (!ctx) {
                  resolve(false);
                  return;
                }
                
                this.canvas = canvas;
                this.ctx = ctx;
                
                // 设置画布尺寸
                const dpr = wx.getSystemInfoSync().pixelRatio || 1;
                canvas.width = this.data.canvasWidth * dpr;
                canvas.height = this.data.canvasHeight * dpr;
                ctx.scale(dpr, dpr);
                
                // 暂时禁用高级渲染引擎以避免离屏Canvas兼容性问题
                this.renderer = null;
                
                resolve(true);
                
              } catch (error) {
                console.error('Canvas上下文获取失败:', error);
                resolve(false);
              }
            } else {
              resolve(false);
            }
          });
      });
    },
    
    /**
     * 处理图谱数据
     */
    processGraphData() {
      console.log('🔍 processGraphData 开始处理数据:', {
        profiles: this.data.profiles?.length || 0,
        relationships: this.data.relationships?.length || 0,
        canvasWidth: this.data.canvasWidth,
        canvasHeight: this.data.canvasHeight,
        ctx: !!this.ctx
      });
      
      if (!this.data.profiles || this.data.profiles.length === 0) {
        console.log('⚠️ 没有联系人数据，清空画布');
        this.setData({ 
          loading: false,
          graphData: {
            nodes: [],
            links: [],
            stats: {}
          }
        });
        // 清空画布
        if (this.ctx) {
          this.ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight);
        }
        return;
      }
      
      // 即使没有关系数据也要显示联系人节点
      const relationships = this.data.relationships || [];
      this.setData({ loading: true });
      
      // 使用图谱数据处理器处理数据
      console.log('📊 调用GraphDataProcessor.processRelationshipData...');
      const graphData = GraphDataProcessor.processRelationshipData(
        relationships,
        this.data.profiles,
        {
          centerNodeId: this.data.centerNodeId,
          maxDepth: this.data.maxDepth,
          minConfidence: this.data.minConfidence
        }
      );
      
      console.log('📊 GraphDataProcessor返回结果:', {
        nodes: graphData.nodes?.length || 0,
        links: graphData.links?.length || 0
      });
      
      // 使用高级布局引擎计算布局
      let layoutData;
      if (this.layoutEngine) {
        try {
          layoutData = this.layoutEngine.calculateLayout(
            graphData.nodes,
            graphData.links,
            {
              width: this.data.canvasWidth,
              height: this.data.canvasHeight,
              layoutType: this.data.layoutType === 'circle' ? 'radial' : this.data.layoutType
            }
          );
        } catch (error) {
          // 降级到默认布局
          layoutData = GraphDataProcessor.calculateLayout(
            graphData.nodes,
            graphData.links,
            {
              width: this.data.canvasWidth,
              height: this.data.canvasHeight,
              layoutType: this.data.layoutType
            }
          );
        }
      } else {
        // 使用默认布局
        layoutData = GraphDataProcessor.calculateLayout(
          graphData.nodes,
          graphData.links,
          {
            width: this.data.canvasWidth,
            height: this.data.canvasHeight,
            layoutType: this.data.layoutType
          }
        );
      }
      
      // 计算居中偏移
      const centerOffset = this.calculateCenterOffset(layoutData.nodes);
      
      console.log('✅ 设置最终图谱数据:', {
        nodes: layoutData.nodes?.length || 0,
        links: layoutData.links?.length || 0,
        centerOffset
      });
      
      this.setData({
        graphData: {
          ...graphData,
          nodes: layoutData.nodes,
          links: layoutData.links
        },
        translateX: centerOffset.x,
        translateY: centerOffset.y,
        scale: 1, // 重置缩放比例
        loading: false
      }, () => {
        console.log('📊 开始渲染图谱...');
        this.renderGraph();
      });
    },
    
    /**
     * 渲染图谱
     */
    renderGraph() {
      console.log('🎨 renderGraph 开始渲染:', {
        ctx: !!this.ctx,
        canvas: !!this.canvas,
        loading: this.data.loading,
        graphData: !!this.data.graphData
      });
      
      if (!this.ctx) {
        // 尝试重新初始化Canvas
        if (!this.canvas) {
          console.log('⚠️ Canvas不存在，尝试重新初始化');
          this.initCanvasWithRetry();
          return;
        } else {
          try {
            this.ctx = this.canvas.getContext('2d');
            if (!this.ctx) {
              console.error('❌ 无法获取Canvas上下文');
              return;
            }
          } catch (error) {
            console.error('重新获取Canvas上下文异常:', error);
            return;
          }
        }
      }
      
      if (this.data.loading) {
        console.log('⏳ 数据加载中，跳过渲染');
        return;
      }
      
      const { nodes, links } = this.data.graphData;
      const { scale, translateX, translateY } = this.data;
      
      console.log('📊 渲染数据检查:', {
        nodes: nodes?.length || 0,
        links: links?.length || 0,
        transform: { scale, translateX, translateY }
      });
      
      // 添加数据验证
      if (!nodes || !Array.isArray(nodes) || nodes.length === 0) {
        console.log('⚠️ 没有节点数据，清空画布');
        if (this.ctx) {
          this.ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight);
        }
        return;
      }
      
      // 使用高级渲染引擎（如果可用）
      if (this.renderer) {
        try {
          this.renderer.render({
            nodes: nodes,
            links: links || [],
            transform: {
              scale: scale,
              translateX: translateX,
              translateY: translateY
            },
            viewport: {
              x: 0,
              y: 0,
              width: this.data.canvasWidth,
              height: this.data.canvasHeight
            }
          });
          return;
        } catch (error) {
          // 继续使用默认渲染
        }
      }
      
      // 默认渲染逻辑
      console.log('🖼️ 使用默认渲染逻辑');
      const ctx = this.ctx;
      try {
        // 清空画布
        ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight);
        console.log('✅ 画布已清空，尺寸:', this.data.canvasWidth, 'x', this.data.canvasHeight);
        
        // 应用变换
        ctx.save();
        ctx.translate(translateX, translateY);
        ctx.scale(scale, scale);
        console.log('✅ 画布变换已应用');
        
        // 绘制连接线
        if (links && Array.isArray(links) && links.length > 0) {
          console.log('🔗 开始绘制', links.length, '条连线');
          links.forEach((link, index) => {
            try {
              this.drawLink(ctx, link, nodes);
            } catch (error) {
              console.error(`绘制连线 ${index} 失败:`, error);
            }
          });
        } else {
          console.log('⚠️ 没有连线数据');
        }
        
        // 绘制节点
        if (nodes && Array.isArray(nodes) && nodes.length > 0) {
          console.log('⭕ 开始绘制', nodes.length, '个节点');
          nodes.forEach((node, index) => {
            try {
              this.drawNode(ctx, node);
              console.log(`✅ 节点 ${index} (${node.name}) 绘制完成`);
            } catch (error) {
              console.error(`绘制节点 ${index} 失败:`, error);
            }
          });
        } else {
          console.log('⚠️ 没有节点数据');
        }
        
      } catch (error) {
        console.error('renderGraph 渲染失败:', error);
        // 尝试清空画布，避免残留内容
        try {
          ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight);
        } catch (clearError) {
          console.error('清空画布失败:', clearError);
        }
      } finally {
        try {
          ctx.restore();
        } catch (restoreError) {
          console.error('渲染状态恢复失败:', restoreError);
        }
      }
    },
    
    /**
     * 绘制节点
     */
    drawNode(ctx, node) {
      if (!ctx || !node) {
        return;
      }
      
      const { x, y, name, size, color, level } = node;
      
      // 验证坐标
      if (typeof x !== 'number' || typeof y !== 'number' || 
          isNaN(x) || isNaN(y) || 
          !isFinite(x) || !isFinite(y)) {
        return;
      }
      
      // 验证节点名称
      if (!name || typeof name !== 'string') {
        return;
      }
      
      // 节点大小
      const radius = size === 'large' ? 28 : 20;
      
      // 创建阴影效果
      ctx.save();
      try {
        ctx.shadowColor = 'rgba(0, 0, 0, 0.15)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetX = 2;
        ctx.shadowOffsetY = 2;
        
        // 绘制节点圆圈（带渐变）
        let fillColor;
        
        // 创建渐变
        const gradientValid = typeof x === 'number' && typeof y === 'number' && 
                            typeof radius === 'number' && 
                            !isNaN(x) && !isNaN(y) && !isNaN(radius) && 
                            radius > 0;
        
        if (gradientValid) {
          try {
            const x1 = x - radius * 0.3;
            const y1 = y - radius * 0.3;
            const r1 = 0;
            const x2 = x;
            const y2 = y;
            const r2 = radius;
            
            const gradient = ctx.createRadialGradient(x1, y1, r1, x2, y2, r2);
            
            if (level === 0) {
              gradient.addColorStop(0, '#06ae56');
              gradient.addColorStop(1, '#048a44');
            } else {
              const nodeColor = this.validateColor(color) || '#4caf50';
              const darkerColor = this.darkenColor(nodeColor, 0.2);
              gradient.addColorStop(0, nodeColor);
              gradient.addColorStop(1, darkerColor);
            }
            fillColor = gradient;
          } catch (error) {
            fillColor = level === 0 ? '#06ae56' : (this.validateColor(color) || '#4caf50');
          }
        } else {
          fillColor = level === 0 ? '#06ae56' : (this.validateColor(color) || '#4caf50');
        }
        
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = fillColor;
        ctx.fill();
        
        // 绘制边框
        ctx.shadowColor = 'transparent';
        ctx.strokeStyle = level === 0 ? '#ffffff' : 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = level === 0 ? 3 : 2;
        ctx.stroke();
        
        // 绘制节点文字
        ctx.fillStyle = '#ffffff';
        ctx.font = size === 'large' ? 'bold 14px sans-serif' : 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // 绘制姓名首字母
        const initial = name ? name.charAt(0) : '?';
        ctx.fillText(initial, x, y);
        
        // 绘制姓名标签
        if ((size === 'large' || this.data.scale > 1.2) && name) {
          ctx.save();
          ctx.fillStyle = '#333';
          ctx.font = 'bold 12px sans-serif';
          ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
          ctx.shadowBlur = 2;
          ctx.fillText(name, x, y + radius + 18);
          ctx.restore();
        }
        
      } catch (error) {
        console.error('drawNode 绘制失败:', error, node);
      } finally {
        ctx.restore();
      }
    },
    
    /**
     * 绘制连接线
     */
    drawLink(ctx, link, nodes) {
      // 参数验证
      if (!ctx || !link || !nodes || !Array.isArray(nodes)) {
        return;
      }
      
      const sourceNode = nodes.find(n => n.id === link.source);
      const targetNode = nodes.find(n => n.id === link.target);
      
      if (!sourceNode || !targetNode) {
        return;
      }
      
      // 验证节点坐标
      if (!sourceNode.x || !sourceNode.y || !targetNode.x || !targetNode.y ||
          typeof sourceNode.x !== 'number' || typeof sourceNode.y !== 'number' ||
          typeof targetNode.x !== 'number' || typeof targetNode.y !== 'number' ||
          isNaN(sourceNode.x) || isNaN(sourceNode.y) || 
          isNaN(targetNode.x) || isNaN(targetNode.y)) {
        return;
      }
      
      const { x1, y1 } = { x1: sourceNode.x, y1: sourceNode.y };
      const { x2, y2 } = { x2: targetNode.x, y2: targetNode.y };
      
      // 增强连线样式
      ctx.save();
      ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
      ctx.shadowBlur = 2;
      
      // 设置线条样式
      ctx.strokeStyle = link.color;
      ctx.lineWidth = Math.max(link.width, 2);
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      
      // 根据关系强度设置透明度
      ctx.globalAlpha = link.strength === 'strong' ? 1.0 : 
                        link.strength === 'medium' ? 0.8 : 0.6;
      
      if (link.style === 'dashed') {
        ctx.setLineDash([8, 4]);
      } else {
        ctx.setLineDash([]);
      }
      
      // 绘制连接线
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      
      ctx.restore();
      
      // 绘制方向箭头（如果不是双向关系）
      if (link.direction !== 'bidirectional') {
        this.drawArrow(ctx, x1, y1, x2, y2, link.color);
      }
    },
    
    /**
     * 验证颜色格式
     */
    validateColor(color) {
      if (!color || typeof color !== 'string') {
        return null;
      }
      
      // 检查常见颜色格式
      const hexPattern = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
      const rgbPattern = /^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$/;
      const rgbaPattern = /^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-9.]+\s*\)$/;
      
      if (hexPattern.test(color) || rgbPattern.test(color) || rgbaPattern.test(color)) {
        return color;
      }
      
      // 检查预设颜色名
      const namedColors = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'brown', 'gray', 'black', 'white'];
      if (namedColors.includes(color.toLowerCase())) {
        return color;
      }
      
      return null;
    },
    
    /**
     * 颜色变暗辅助函数
     */
    darkenColor(color, amount = 0.2) {
      const validColor = this.validateColor(color);
      if (!validColor) {
        return '#4caf50'; // 默认绿色
      }
      
      // 预设颜色映射
      const colorMap = {
        '#1976d2': '#1565c0',
        '#4caf50': '#388e3c',
        '#ff9800': '#f57c00',
        '#f44336': '#d32f2f',
        '#9c27b0': '#7b1fa2',
        '#607d8b': '#455a64',
        '#06ae56': '#048a44'
      };
      
      // 如果有预设映射，直接返回
      if (colorMap[validColor]) {
        return colorMap[validColor];
      }
      
      // 简单的颜色变暗处理
      if (validColor.startsWith('#') && validColor.length === 7) {
        try {
          const r = parseInt(validColor.substr(1, 2), 16);
          const g = parseInt(validColor.substr(3, 2), 16);
          const b = parseInt(validColor.substr(5, 2), 16);
          
          const darkR = Math.max(0, Math.floor(r * (1 - amount)));
          const darkG = Math.max(0, Math.floor(g * (1 - amount)));
          const darkB = Math.max(0, Math.floor(b * (1 - amount)));
          
          return `#${darkR.toString(16).padStart(2, '0')}${darkG.toString(16).padStart(2, '0')}${darkB.toString(16).padStart(2, '0')}`;
        } catch (e) {
          return '#388e3c'; // 默认深绿色
        }
      }
      
      return validColor; // 无法处理的颜色格式，返回原色
    },
    
    /**
     * 绘制箭头
     */
    drawArrow(ctx, x1, y1, x2, y2, color) {
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const headLength = 10;
      
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(x2 - headLength * Math.cos(angle - Math.PI / 6), 
                 y2 - headLength * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(x2, y2);
      ctx.lineTo(x2 - headLength * Math.cos(angle + Math.PI / 6), 
                 y2 - headLength * Math.sin(angle + Math.PI / 6));
      ctx.fill();
    },
    
    /**
     * 触摸开始
     */
    onTouchStart(e) {
      const touch = e.touches[0];
      const isMultiTouch = e.touches.length > 1;
      
      this.setData({
        lastTouchX: touch.x,
        lastTouchY: touch.y,
        touching: true,
        multiTouch: isMultiTouch
      });
      
      // 记录点击开始状态（用于检测单击）
      this.touchStartTime = Date.now();
      this.touchStartX = touch.x;
      this.touchStartY = touch.y;
      this.hasMoved = false;
      
      // 重置双指缩放距离
      if (isMultiTouch) {
        this.lastPinchDistance = null;
      }
    },
    
    /**
     * 触摸移动
     */
    onTouchMove(e) {
      if (!this.data.touching) return;
      
      const touchCount = e.touches.length;
      
      // 更新多指触摸状态
      if (touchCount > 1 && !this.data.multiTouch) {
        this.setData({ multiTouch: true });
        this.lastPinchDistance = null; // 重置缩放距离
      } else if (touchCount === 1 && this.data.multiTouch) {
        this.setData({ multiTouch: false });
      }
      
      if (touchCount > 1) {
        // 双指缩放
        this.handlePinchZoom(e.touches);
      } else if (touchCount === 1 && !this.data.multiTouch) {
        // 单指拖拽
        const touch = e.touches[0];
        const deltaX = touch.x - this.data.lastTouchX;
        const deltaY = touch.y - this.data.lastTouchY;
        
        // 检查是否为微小移动（可能是点击）
        const moveDistance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        if (moveDistance < 5) {
          return; // 忽略微小移动
        }
        
        // 标记已移动
        this.hasMoved = true;
        
        const newTranslateX = this.data.translateX + deltaX;
        const newTranslateY = this.data.translateY + deltaY;
        
        // 简单的边界限制
        const { canvasWidth, canvasHeight } = this.data;
        const limit = Math.max(canvasWidth, canvasHeight) * 2;
        
        const clampedTranslateX = Math.max(-limit, Math.min(limit, newTranslateX));
        const clampedTranslateY = Math.max(-limit, Math.min(limit, newTranslateY));
        
        this.setData({
          translateX: clampedTranslateX,
          translateY: clampedTranslateY,
          lastTouchX: touch.x,
          lastTouchY: touch.y
        }, () => {
          this.renderGraph();
        });
      }
    },
    
    /**
     * 触摸结束
     */
    onTouchEnd(e) {
      // 检查是否还有触摸点
      const remainingTouches = e.touches.length;
      
      if (remainingTouches === 0) {
        // 检测是否为单击
        this.detectTap();
        
        this.setData({
          touching: false,
          multiTouch: false
        });
        this.lastPinchDistance = null;
      } else if (remainingTouches === 1) {
        // 从双指切换到单指
        this.setData({
          multiTouch: false,
          lastTouchX: e.touches[0].x,
          lastTouchY: e.touches[0].y
        });
        this.lastPinchDistance = null;
      }
    },
    
    /**
     * 检测单击
     */
    detectTap() {
      if (!this.touchStartTime || !this.touchStartX || !this.touchStartY) {
        console.log('单击检测失败：缺少开始触摸数据');
        return;
      }
      
      const touchDuration = Date.now() - this.touchStartTime;
      
      // 检查是否为单击：时间短且没有移动
      if (touchDuration < 300 && !this.hasMoved) {
        console.log('检测到单击:', {
          duration: touchDuration,
          hasMoved: this.hasMoved,
          position: { x: this.touchStartX, y: this.touchStartY }
        });
        
        // 执行命中测试
        this.handleTap(this.touchStartX, this.touchStartY);
      } else {
        console.log('不是单击:', {
          duration: touchDuration,
          hasMoved: this.hasMoved
        });
      }
      
      // 清理状态
      this.touchStartTime = null;
      this.touchStartX = null;
      this.touchStartY = null;
      this.hasMoved = false;
    },
    
    /**
     * 处理单击
     */
    handleTap(x, y) {
      console.log('处理单击:', { x, y });
      
      // 检查坐标有效性
      if (typeof x !== 'number' || typeof y !== 'number') {
        console.warn('无效的点击坐标:', { x, y });
        return;
      }
      
      // 执行命中测试
      const hitNode = this.hitTestNode(x, y);
      const hitLink = this.hitTestLink(x, y);
      
      console.log('命中测试结果:', {
        hitNode: hitNode ? hitNode.name : null,
        hitLink: hitLink ? hitLink.id : null,
        clickPos: { x, y },
        transform: {
          scale: this.data.scale,
          translateX: this.data.translateX,
          translateY: this.data.translateY
        }
      });
      
      if (hitNode) {
        console.log('点击节点:', hitNode.name);
        this.setData({
          selectedNode: hitNode,
          showNodeDetail: true
        });
      } else if (hitLink) {
        console.log('点击连线:', hitLink);
        // 预计算所有显示值避免模板函数调用失败  
        const standardizedConfidence = this.normalizeConfidenceScore(hitLink.confidence_score);
        const linkWithDisplayValues = {
          ...hitLink,
          confidence_score: standardizedConfidence, // 统一使用confidence_score
          confidencePercentage: Math.round(standardizedConfidence * 100),
          relationshipTypeName: this.getRelationshipTypeName(hitLink.relationship_type),
          relationshipStrengthName: this.getRelationshipStrengthName(hitLink.relationship_strength),
          matchedFieldsDisplay: hitLink.evidence_fields || hitLink.matchedFields || ''
        };
        this.setData({
          selectedLink: linkWithDisplayValues,
          showLinkDetail: true
        });
      }
    },
    
    /**
     * 画布点击
     */
    onCanvasTap(e) {
      const { x, y } = e.detail;
      
      if (typeof x !== 'number' || typeof y !== 'number') {
        return;
      }
      
      // 直接处理单击，去除双击逢辑
      const hitNode = this.hitTestNode(x, y);
      const hitLink = this.hitTestLink(x, y);
      
      if (hitNode) {
        this.setData({
          selectedNode: hitNode,
          showNodeDetail: true
        });
      } else if (hitLink) {
        // 预计算所有显示值避免模板函数调用失败  
        const standardizedConfidence = this.normalizeConfidenceScore(hitLink.confidence_score);
        const linkWithDisplayValues = {
          ...hitLink,
          confidence_score: standardizedConfidence, // 统一使用confidence_score
          confidencePercentage: Math.round(standardizedConfidence * 100),
          relationshipTypeName: this.getRelationshipTypeName(hitLink.relationship_type),
          relationshipStrengthName: this.getRelationshipStrengthName(hitLink.relationship_strength),
          matchedFieldsDisplay: hitLink.evidence_fields || hitLink.matchedFields || ''
        };
        this.setData({
          selectedLink: linkWithDisplayValues,
          showLinkDetail: true
        });
      }
    },
    
    /**
     * 节点命中测试
     */
    hitTestNode(x, y) {
      const { nodes } = this.data.graphData;
      if (!nodes || nodes.length === 0) {
        return null;
      }
      
      // 使用高级渲染引擎的空间索引（如果可用）
      if (this.renderer && this.renderer.hitTestNode) {
        try {
          const hitResult = this.renderer.hitTestNode(x, y, {
            scale: this.data.scale,
            translateX: this.data.translateX,
            translateY: this.data.translateY
          });
          
          if (hitResult) {
            return hitResult;
          }
        } catch (error) {
          // 继续使用默认方法
        }
      }
      
      // 默认命中测试逻辑
      const { scale, translateX, translateY } = this.data;
      
      // 转换坐标
      const canvasX = (x - translateX) / scale;
      const canvasY = (y - translateY) / scale;
      
      for (let node of nodes) {
        if (node.x != null && node.y != null) {
          const radius = node.size === 'large' ? 28 : 20;
          const distance = Math.sqrt(
            Math.pow(canvasX - node.x, 2) + Math.pow(canvasY - node.y, 2)
          );
          
          if (distance <= radius) {
            return node;
          }
        }
      }
      
      return null;
    },
    
    /**
     * 连接线命中测试
     */
    hitTestLink(x, y) {
      const { links, nodes } = this.data.graphData;
      if (!links || links.length === 0 || !nodes || nodes.length === 0) {
        return null;
      }
      
      // 使用高级渲染引擎的空间索引（如果可用）
      if (this.renderer && this.renderer.hitTestLink) {
        try {
          const hitResult = this.renderer.hitTestLink(x, y, {
            scale: this.data.scale,
            translateX: this.data.translateX,
            translateY: this.data.translateY
          });
          
          if (hitResult) {
            return hitResult;
          }
        } catch (error) {
          // 继续使用默认方法
        }
      }
      
      // 默认连线命中测试逻辑
      const { scale, translateX, translateY } = this.data;
      
      // 转换坐标
      const canvasX = (x - translateX) / scale;
      const canvasY = (y - translateY) / scale;
      
      for (let link of links) {
        const sourceNode = nodes.find(n => n.id === link.source);
        const targetNode = nodes.find(n => n.id === link.target);
        
        if (!sourceNode || !targetNode) {
          continue;
        }
        
        // 计算点到线段的距离
        const distance = this.pointToLineDistance(
          canvasX, canvasY,
          sourceNode.x, sourceNode.y,
          targetNode.x, targetNode.y
        );
        
        const hitThreshold = Math.max(10, (link.width || 2) * 2 + 5);
        
        if (distance <= hitThreshold) {
          return link;
        }
      }
      
      return null;
    },
    
    /**
     * 计算点到线段的距离
     */
    pointToLineDistance(px, py, x1, y1, x2, y2) {
      const dx = x2 - x1;
      const dy = y2 - y1;
      const length = Math.sqrt(dx * dx + dy * dy);
      
      if (length === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
      
      const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (length * length)));
      const projection = { x: x1 + t * dx, y: y1 + t * dy };
      
      return Math.sqrt((px - projection.x) ** 2 + (py - projection.y) ** 2);
    },
    
    /**
     * 计算图谱内容边界
     */
    calculateContentBounds(nodes) {
      if (!nodes || nodes.length === 0) {
        return {
          minX: 0, maxX: this.data.canvasWidth,
          minY: 0, maxY: this.data.canvasHeight
        };
      }
      
      let minX = Infinity, maxX = -Infinity;
      let minY = Infinity, maxY = -Infinity;
      
      nodes.forEach(node => {
        if (typeof node.x === 'number' && typeof node.y === 'number') {
          const radius = node.size === 'large' ? 28 : 20;
          minX = Math.min(minX, node.x - radius);
          maxX = Math.max(maxX, node.x + radius);
          minY = Math.min(minY, node.y - radius);
          maxY = Math.max(maxY, node.y + radius);
        }
      });
      
      // 如果没有有效节点，返回默认边界
      if (minX === Infinity) {
        return {
          minX: 0, maxX: this.data.canvasWidth,
          minY: 0, maxY: this.data.canvasHeight
        };
      }
      
      return { minX, maxX, minY, maxY };
    },
    
    /**
     * 计算居中偏移
     */
    calculateCenterOffset(nodes) {
      if (!nodes || nodes.length === 0) {
        return { x: 0, y: 0 };
      }
      
      const bounds = this.calculateContentBounds(nodes);
      const { canvasWidth, canvasHeight } = this.data;
      
      // 计算内容中心
      const contentCenterX = (bounds.minX + bounds.maxX) / 2;
      const contentCenterY = (bounds.minY + bounds.maxY) / 2;
      
      // 计算画布中心
      const canvasCenterX = canvasWidth / 2;
      const canvasCenterY = canvasHeight / 2;
      
      // 计算需要的偏移量
      const offsetX = canvasCenterX - contentCenterX;
      const offsetY = canvasCenterY - contentCenterY;
      
      console.log('居中计算:', {
        contentCenter: { x: contentCenterX, y: contentCenterY },
        canvasCenter: { x: canvasCenterX, y: canvasCenterY },
        offset: { x: offsetX, y: offsetY },
        bounds
      });
      
      return { x: offsetX, y: offsetY };
    },
    
    
    /**
     * 处理双指缩放
     */
    handlePinchZoom(touches) {
      if (touches.length !== 2) return;
      
      const touch1 = touches[0];
      const touch2 = touches[1];
      
      const currentDistance = Math.sqrt(
        Math.pow(touch2.x - touch1.x, 2) + Math.pow(touch2.y - touch1.y, 2)
      );
      
      if (this.lastPinchDistance) {
        const rawScaleChange = currentDistance / this.lastPinchDistance;
        
        // 添加阻尼效果，减少敏感度
        const dampingFactor = 0.1;
        const scaleChange = 1 + (rawScaleChange - 1) * dampingFactor;
        
        // 限制单次缩放变化量，避免跳跃性变化
        const maxScaleChange = 1.05;
        const minScaleChange = 0.95;
        const clampedScaleChange = Math.max(minScaleChange, Math.min(maxScaleChange, scaleChange));
        
        const newScale = Math.max(0.3, Math.min(2.5, this.data.scale * clampedScaleChange));
        
        this.setData({
          scale: newScale
        }, () => {
          this.renderGraph();
        });
      }
      
      this.lastPinchDistance = currentDistance;
    },
    
    /**
     * 刷新图谱
     */
    onRefresh() {
      this.processGraphData();
    },
    
    /**
     * 放大
     */
    onZoomIn() {
      const newScale = Math.min(2.5, this.data.scale * 1.1);
      this.setData({ scale: newScale }, () => {
        this.renderGraph();
      });
    },
    
    /**
     * 缩小
     */
    onZoomOut() {
      const newScale = Math.max(0.3, this.data.scale / 1.1);
      this.setData({ scale: newScale }, () => {
        this.renderGraph();
      });
    },
    
    /**
     * 重置视图（居中和重置缩放）
     */
    onResetView() {
      const { nodes } = this.data.graphData;
      if (!nodes || nodes.length === 0) {
        this.setData({
          scale: 1,
          translateX: 0,
          translateY: 0
        }, () => {
          this.renderGraph();
        });
        return;
      }
      
      // 重新计算居中偏移
      const centerOffset = this.calculateCenterOffset(nodes);
      
      this.setData({
        scale: 1,
        translateX: centerOffset.x,
        translateY: centerOffset.y
      }, () => {
        this.renderGraph();
      });
      
      // 给用户反馈
      wx.showToast({
        title: '已重置并居中',
        icon: 'success',
        duration: 1000
      });
    },
    
    /**
     * 全屏显示
     */
    onFullscreen() {
      this.triggerEvent('fullscreen');
    },
    
    /**
     * 打开设置
     */
    onOpenSettings() {
      this.setData({ showSettings: true });
    },
    
    /**
     * 关闭设置
     */
    onSettingsClose() {
      this.setData({ showSettings: false });
    },
    
    /**
     * 显示统计信息改变
     */
    onShowStatsChange(e) {
      this.setData({ showStats: e.detail.value });
    },
    
    /**
     * 显示图例改变
     */
    onShowLegendChange(e) {
      this.setData({ showLegend: e.detail.value });
    },
    
    /**
     * 布局类型改变
     */
    onLayoutTypeChange(e) {
      this.setData({ layoutType: e.detail.value }, () => {
        this.processGraphData();
      });
    },
    
    /**
     * 最小置信度改变
     */
    onMinConfidenceChange(e) {
      this.setData({ minConfidence: e.detail.value / 100 }, () => {
        this.processGraphData();
      });
    },
    
    /**
     * 最大层级改变
     */
    onMaxDepthChange(e) {
      this.setData({ maxDepth: e.detail.value }, () => {
        this.processGraphData();
      });
    },
    
    /**
     * 关闭节点详情
     */
    onNodeDetailClose() {
      this.setData({ 
        showNodeDetail: false,
        selectedNode: null 
      });
    },
    
    /**
     * 关闭关系详情
     */
    onLinkDetailClose() {
      this.setData({ 
        showLinkDetail: false,
        selectedLink: null 
      });
    },
    
    /**
     * 查看节点详情
     */
    onViewNodeDetail() {
      const nodeId = this.data.selectedNode.id;
      this.triggerEvent('nodeDetail', { nodeId });
      this.onNodeDetailClose();
    },
    
    /**
     * 设为中心节点
     */
    onSetAsCenter() {
      const nodeId = this.data.selectedNode.id;
      this.triggerEvent('centerChange', { centerNodeId: nodeId });
      this.onNodeDetailClose();
    },
    
    /**
     * 确认关系
     */
    onConfirmLink() {
      const relationshipId = this.data.selectedLink.relationshipId;
      this.triggerEvent('confirmRelationship', { relationshipId });
      this.onLinkDetailClose();
    },
    
    /**
     * 忽略关系
     */
    onIgnoreLink() {
      const relationshipId = this.data.selectedLink.relationshipId;
      this.triggerEvent('ignoreRelationship', { relationshipId });
      this.onLinkDetailClose();
    },
    
    /**
     * 获取连接颜色
     */
    getLinkColor(type) {
      return GraphDataProcessor.getLinkColor(type);
    },
    
    /**
     * 获取关系类型名称
     */
    getRelationshipTypeName(type) {
      const typeNames = {
        'colleague': '同事',
        'friend': '朋友',
        'family': '家人',
        'partner': '合作伙伴',
        'client': '客户',
        'supplier': '供应商',
        'alumni': '校友',
        'neighbor': '邻居',
        'same_location': '同地区',
        'competitor': '竞争对手',
        'investor': '投资人'
      };
      
      return typeNames[type] || type;
    },
    
    /**
     * 获取关系强度名称
     */
    getRelationshipStrengthName(strength) {
      const strengthNames = {
        'strong': '强关系',
        'medium': '中等关系',
        'weak': '弱关系'
      };
      
      return strengthNames[strength] || strength;
    },
    
    /**
     * 获取连接源节点名称
     */
    getLinkSourceName(link) {
      const sourceNode = this.data.graphData.nodes.find(n => n.id === link.source);
      return sourceNode ? sourceNode.name : '未知';
    },
    
    /**
     * 获取连接目标节点名称
     */
    getLinkTargetName(link) {
      const targetNode = this.data.graphData.nodes.find(n => n.id === link.target);
      return targetNode ? targetNode.name : '未知';
    },
    
    /**
     * 格式化置信度
     */
    formatConfidence(confidence) {
      console.log('relationship-graph formatConfidence调用:', confidence, '结果:', (confidence * 100).toFixed(1));
      return (confidence * 100).toFixed(1);
    },
    
    /**
     * 格式化最小置信度
     */
    formatMinConfidence(minConfidence) {
      return (minConfidence * 100).toFixed(0);
    }
  }
});