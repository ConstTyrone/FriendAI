/**
 * 高性能关系图谱渲染引擎
 * 支持分层渲染、智能重绘、高效交互检测
 */

class AdvancedGraphRenderer {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    
    // 渲染配置
    this.config = {
      // 性能设置
      enableLayeredRendering: true,    // 启用分层渲染
      enableViewportCulling: true,     // 启用视窗裁剪
      enableAnimations: true,          // 启用动画效果
      maxFPS: 60,                     // 最大帧率
      
      // 视觉设置
      nodeRadius: {
        small: 16,
        medium: 20,
        large: 28
      },
      confidenceColors: {
        high: { start: '#06ae56', end: '#048a44' },      // 高置信度：绿色
        medium: { start: '#2196F3', end: '#1976D2' },    // 中置信度：蓝色
        low: { start: '#FF9800', end: '#F57C00' },       // 低置信度：橙色
        veryLow: { start: '#9E9E9E', end: '#757575' }    // 极低置信度：灰色
      },
      
      // 交互设置
      clickTolerance: 10,             // 点击容差
      hoverEffect: true,              // 悬停效果
      zoomRange: { min: 0.2, max: 3.0 },
      
      ...options
    };
    
    // 渲染层管理
    this.layers = {
      background: { dirty: true, canvas: null },
      links: { dirty: true, canvas: null },
      nodes: { dirty: true, canvas: null },
      labels: { dirty: true, canvas: null },
      interaction: { dirty: true, canvas: null }
    };
    
    // 渲染状态
    this.renderState = {
      scale: 1,
      translateX: 0,
      translateY: 0,
      hoveredNode: null,
      selectedNode: null,
      animation: null
    };
    
    // 性能监控
    this.performance = {
      lastFrameTime: 0,
      frameCount: 0,
      fps: 0,
      renderTime: 0
    };
    
    // 数据缓存
    this.dataCache = {
      nodes: [],
      links: [],
      spatialIndex: null,    // 空间索引用于快速点击检测
      bounds: { minX: 0, minY: 0, maxX: 0, maxY: 0 }
    };
    
    this.initLayers();
    this.bindEvents();
  }
  
  /**
   * 初始化分层渲染画布
   */
  initLayers() {
    if (!this.config.enableLayeredRendering) return;
    
    const { width, height } = this.canvas;
    
    Object.keys(this.layers).forEach(layerName => {
      const offscreenCanvas = wx.createOffscreenCanvas ? 
        wx.createOffscreenCanvas({ width, height }) : 
        null;
      
      if (offscreenCanvas) {
        this.layers[layerName].canvas = offscreenCanvas;
        this.layers[layerName].ctx = offscreenCanvas.getContext('2d');
      }
    });
  }
  
  /**
   * 绑定事件监听
   */
  bindEvents() {
    // 使用防抖优化触摸事件
    this.debouncedRender = this.debounce(this.render.bind(this), 16); // ~60fps
  }
  
  /**
   * 更新图谱数据
   */
  updateData(nodes, links) {
    const startTime = performance.now();
    
    // 数据预处理
    this.dataCache.nodes = this.preprocessNodes(nodes);
    this.dataCache.links = this.preprocessLinks(links);
    
    // 更新空间索引
    this.updateSpatialIndex();
    
    // 计算边界
    this.calculateBounds();
    
    // 标记所有层需要重绘
    Object.keys(this.layers).forEach(layer => {
      this.layers[layer].dirty = true;
    });
    
    console.log(`数据更新耗时: ${(performance.now() - startTime).toFixed(2)}ms`);
    
    // 触发重绘
    this.render();
  }
  
  /**
   * 预处理节点数据
   */
  preprocessNodes(nodes) {
    return nodes.map(node => ({
      ...node,
      // 基于置信度确定视觉样式
      visualStyle: this.getNodeVisualStyle(node),
      // 添加渲染缓存
      renderCache: {
        lastScale: null,
        cachedRadius: null,
        cachedColor: null
      }
    }));
  }
  
  /**
   * 预处理连线数据
   */
  preprocessLinks(links) {
    return links.map(link => ({
      ...link,
      // 基于置信度确定连线样式
      visualStyle: this.getLinkVisualStyle(link),
      // 添加渲染缓存
      renderCache: {
        cachedPath: null,
        cachedStyle: null
      }
    }));
  }
  
  /**
   * 获取节点视觉样式
   */
  getNodeVisualStyle(node) {
    const confidence = node.confidence_score || 0.5;
    let colorScheme;
    let size = 'medium';
    
    // 根据置信度确定颜色
    if (confidence >= 0.8) {
      colorScheme = this.config.confidenceColors.high;
      size = 'large';
    } else if (confidence >= 0.6) {
      colorScheme = this.config.confidenceColors.medium;
    } else if (confidence >= 0.4) {
      colorScheme = this.config.confidenceColors.low;
    } else {
      colorScheme = this.config.confidenceColors.veryLow;
      size = 'small';
    }
    
    // 中心节点特殊处理
    if (node.level === 0) {
      size = 'large';
      colorScheme = this.config.confidenceColors.high;
    }
    
    return {
      size,
      colorScheme,
      confidence,
      radius: this.config.nodeRadius[size],
      // 添加置信度环效果
      showConfidenceRing: confidence > 0.6,
      ringOpacity: Math.min(confidence, 0.8)
    };
  }
  
  /**
   * 获取连线视觉样式
   */
  getLinkVisualStyle(link) {
    const confidence = link.confidence_score || link.confidence || 0.5;
    
    return {
      confidence,
      width: Math.max(1, confidence * 4),  // 置信度越高线越粗
      opacity: Math.max(0.3, confidence), // 置信度越高越不透明
      color: this.getRelationshipColor(link.type),
      style: confidence > 0.7 ? 'solid' : 'dashed',
      showLabel: confidence > 0.6  // 高置信度显示关系类型标签
    };
  }
  
  /**
   * 获取关系类型颜色
   */
  getRelationshipColor(relationshipType) {
    const colorMap = {
      'colleague': '#4CAF50',
      'friend': '#2196F3',
      'family': '#FF5722',
      'partner': '#FF9800',
      'client': '#9C27B0',
      'supplier': '#795548',
      'alumni': '#607D8B',
      'neighbor': '#FFC107',
      'same_location': '#E91E63',
      'competitor': '#F44336',
      'investor': '#3F51B5'
    };
    return colorMap[relationshipType] || '#9E9E9E';
  }
  
  /**
   * 更新空间索引（用于快速点击检测）
   */
  updateSpatialIndex() {
    // 简化的空间索引：按网格划分
    const gridSize = 50;
    const index = {};
    
    this.dataCache.nodes.forEach(node => {
      const gridX = Math.floor(node.x / gridSize);
      const gridY = Math.floor(node.y / gridSize);
      const key = `${gridX},${gridY}`;
      
      if (!index[key]) index[key] = [];
      index[key].push(node);
    });
    
    this.dataCache.spatialIndex = { gridSize, index };
  }
  
  /**
   * 计算图谱边界
   */
  calculateBounds() {
    const nodes = this.dataCache.nodes;
    if (nodes.length === 0) return;
    
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    
    nodes.forEach(node => {
      const radius = node.visualStyle.radius;
      minX = Math.min(minX, node.x - radius);
      minY = Math.min(minY, node.y - radius);
      maxX = Math.max(maxX, node.x + radius);
      maxY = Math.max(maxY, node.y + radius);
    });
    
    this.dataCache.bounds = { minX, minY, maxX, maxY };
  }
  
  /**
   * 主渲染函数
   */
  render() {
    const startTime = performance.now();
    
    // 清空主画布
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    if (this.config.enableLayeredRendering) {
      this.renderLayered();
    } else {
      this.renderDirect();
    }
    
    // 性能统计
    this.updatePerformanceStats(startTime);
  }
  
  /**
   * 分层渲染
   */
  renderLayered() {
    const { scale, translateX, translateY } = this.renderState;
    
    // 应用变换
    this.ctx.save();
    this.ctx.scale(scale, scale);
    this.ctx.translate(translateX, translateY);
    
    // 渲染各层
    this.renderLayer('background');
    this.renderLayer('links');
    this.renderLayer('nodes');
    this.renderLayer('labels');
    this.renderLayer('interaction');
    
    this.ctx.restore();
  }
  
  /**
   * 渲染指定层
   */
  renderLayer(layerName) {
    const layer = this.layers[layerName];
    if (!layer.dirty || !layer.canvas) return;
    
    const layerCtx = layer.ctx;
    layerCtx.clearRect(0, 0, layer.canvas.width, layer.canvas.height);
    
    switch (layerName) {
      case 'background':
        this.renderBackground(layerCtx);
        break;
      case 'links':
        this.renderLinks(layerCtx);
        break;
      case 'nodes':
        this.renderNodes(layerCtx);
        break;
      case 'labels':
        this.renderLabels(layerCtx);
        break;
      case 'interaction':
        this.renderInteraction(layerCtx);
        break;
    }
    
    // 将离屏画布绘制到主画布
    this.ctx.drawImage(layer.canvas, 0, 0);
    layer.dirty = false;
  }
  
  /**
   * 渲染背景
   */
  renderBackground(ctx) {
    // 绘制网格背景（可选）
    if (this.config.showGrid) {
      this.drawGrid(ctx);
    }
  }
  
  /**
   * 渲染连线
   */
  renderLinks(ctx) {
    const links = this.dataCache.links;
    const nodes = this.dataCache.nodes;
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    
    links.forEach(link => {
      const sourceNode = nodeMap.get(link.source);
      const targetNode = nodeMap.get(link.target);
      
      if (!sourceNode || !targetNode) return;
      
      // 视窗裁剪检测
      if (this.config.enableViewportCulling && !this.isLinkVisible(sourceNode, targetNode)) {
        return;
      }
      
      this.drawLink(ctx, link, sourceNode, targetNode);
    });
  }
  
  /**
   * 渲染节点
   */
  renderNodes(ctx) {
    const nodes = this.dataCache.nodes;
    
    // 按层级排序，确保中心节点在最上层
    const sortedNodes = [...nodes].sort((a, b) => a.level - b.level);
    
    sortedNodes.forEach(node => {
      // 视窗裁剪检测
      if (this.config.enableViewportCulling && !this.isNodeVisible(node)) {
        return;
      }
      
      this.drawNode(ctx, node);
    });
  }
  
  /**
   * 绘制节点（增强版）
   */
  drawNode(ctx, node) {
    const { x, y, visualStyle } = node;
    const { size, colorScheme, radius, showConfidenceRing, ringOpacity } = visualStyle;
    
    ctx.save();
    
    // 阴影效果
    ctx.shadowColor = 'rgba(0, 0, 0, 0.2)';
    ctx.shadowBlur = 8;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;
    
    // 置信度环（如果需要）
    if (showConfidenceRing) {
      ctx.beginPath();
      ctx.arc(x, y, radius + 6, 0, 2 * Math.PI);
      ctx.strokeStyle = `rgba(6, 174, 86, ${ringOpacity})`;
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    
    // 节点渐变填充
    const gradient = ctx.createRadialGradient(
      x - radius * 0.3, y - radius * 0.3, 0,
      x, y, radius
    );
    gradient.addColorStop(0, colorScheme.start);
    gradient.addColorStop(1, colorScheme.end);
    
    // 绘制主体
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // 悬停效果
    if (node === this.renderState.hoveredNode) {
      ctx.strokeStyle = '#FFD700';
      ctx.lineWidth = 4;
      ctx.stroke();
    }
    
    // 选中效果
    if (node === this.renderState.selectedNode) {
      ctx.strokeStyle = '#FF4444';
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    
    // 绘制边框
    ctx.shadowColor = 'transparent';
    ctx.strokeStyle = node.level === 0 ? '#ffffff' : 'rgba(255, 255, 255, 0.8)';
    ctx.lineWidth = node.level === 0 ? 3 : 2;
    ctx.stroke();
    
    // 绘制节点文字
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${size === 'large' ? '14px' : '11px'} sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    const initial = node.name ? node.name.charAt(0) : '?';
    ctx.fillText(initial, x, y);
    
    ctx.restore();
  }
  
  /**
   * 绘制连线（增强版）
   */
  drawLink(ctx, link, sourceNode, targetNode) {
    const { visualStyle } = link;
    const { width, opacity, color, style } = visualStyle;
    
    ctx.save();
    
    // 计算连线位置（避开节点）
    const sourceRadius = sourceNode.visualStyle.radius;
    const targetRadius = targetNode.visualStyle.radius;
    
    const dx = targetNode.x - sourceNode.x;
    const dy = targetNode.y - sourceNode.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    if (distance === 0) return;
    
    const unitX = dx / distance;
    const unitY = dy / distance;
    
    const startX = sourceNode.x + unitX * sourceRadius;
    const startY = sourceNode.y + unitY * sourceRadius;
    const endX = targetNode.x - unitX * targetRadius;
    const endY = targetNode.y - unitY * targetRadius;
    
    // 设置连线样式
    ctx.strokeStyle = `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`;
    ctx.lineWidth = width;
    
    if (style === 'dashed') {
      ctx.setLineDash([5, 5]);
    }
    
    // 绘制连线
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    
    // 绘制箭头（表示方向性）
    if (link.direction !== 'bidirectional') {
      this.drawArrow(ctx, endX, endY, unitX, unitY, width);
    }
    
    ctx.restore();
  }
  
  /**
   * 绘制箭头
   */
  drawArrow(ctx, x, y, unitX, unitY, lineWidth) {
    const arrowSize = Math.max(8, lineWidth * 2);
    
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(
      x - arrowSize * unitX + arrowSize * 0.5 * unitY,
      y - arrowSize * unitY - arrowSize * 0.5 * unitX
    );
    ctx.lineTo(
      x - arrowSize * unitX - arrowSize * 0.5 * unitY,
      y - arrowSize * unitY + arrowSize * 0.5 * unitX
    );
    ctx.closePath();
    ctx.fill();
  }
  
  /**
   * 快速点击检测
   */
  hitTest(x, y) {
    // 使用空间索引加速检测
    const { gridSize, index } = this.dataCache.spatialIndex;
    const gridX = Math.floor(x / gridSize);
    const gridY = Math.floor(y / gridSize);
    
    // 检查周围9个网格
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const key = `${gridX + dx},${gridY + dy}`;
        const cellNodes = index[key] || [];
        
        for (const node of cellNodes) {
          const distance = Math.sqrt(
            (x - node.x) ** 2 + (y - node.y) ** 2
          );
          
          if (distance <= node.visualStyle.radius + this.config.clickTolerance) {
            return { type: 'node', data: node };
          }
        }
      }
    }
    
    return null;
  }
  
  /**
   * 视窗裁剪检测
   */
  isNodeVisible(node) {
    const { x, y, visualStyle } = node;
    const radius = visualStyle.radius;
    const { scale, translateX, translateY } = this.renderState;
    
    // 转换到屏幕坐标
    const screenX = (x + translateX) * scale;
    const screenY = (y + translateY) * scale;
    const screenRadius = radius * scale;
    
    return screenX + screenRadius > 0 &&
           screenX - screenRadius < this.canvas.width &&
           screenY + screenRadius > 0 &&
           screenY - screenRadius < this.canvas.height;
  }
  
  /**
   * 连线可见性检测
   */
  isLinkVisible(sourceNode, targetNode) {
    // 简化：如果任一节点可见，连线就可见
    return this.isNodeVisible(sourceNode) || this.isNodeVisible(targetNode);
  }
  
  /**
   * 性能统计更新
   */
  updatePerformanceStats(startTime) {
    const renderTime = performance.now() - startTime;
    this.performance.renderTime = renderTime;
    this.performance.frameCount++;
    
    const now = performance.now();
    if (now - this.performance.lastFrameTime >= 1000) {
      this.performance.fps = this.performance.frameCount;
      this.performance.frameCount = 0;
      this.performance.lastFrameTime = now;
    }
  }
  
  /**
   * 防抖函数
   */
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  /**
   * 直接渲染（回退模式）
   */
  renderDirect() {
    const { scale, translateX, translateY } = this.renderState;
    
    this.ctx.save();
    this.ctx.scale(scale, scale);
    this.ctx.translate(translateX, translateY);
    
    this.renderLinks(this.ctx);
    this.renderNodes(this.ctx);
    
    this.ctx.restore();
  }
  
  // 设置渲染状态
  setRenderState(newState) {
    const changed = Object.keys(newState).some(key => 
      this.renderState[key] !== newState[key]
    );
    
    if (changed) {
      Object.assign(this.renderState, newState);
      
      // 标记需要重绘的层
      if ('scale' in newState || 'translateX' in newState || 'translateY' in newState) {
        Object.keys(this.layers).forEach(layer => {
          this.layers[layer].dirty = true;
        });
      }
      
      this.debouncedRender();
    }
  }
  
  // 获取性能信息
  getPerformanceInfo() {
    return { ...this.performance };
  }
  
  // 销毁渲染器
  destroy() {
    // 清理资源
    this.dataCache = null;
    Object.keys(this.layers).forEach(layer => {
      if (this.layers[layer].canvas) {
        this.layers[layer].canvas = null;
      }
    });
  }
}

export default AdvancedGraphRenderer;