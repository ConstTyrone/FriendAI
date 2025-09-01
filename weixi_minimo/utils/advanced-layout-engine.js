/**
 * 高级图谱布局引擎
 * 支持多种智能布局算法和动态优化
 */

class AdvancedLayoutEngine {
  constructor(options = {}) {
    this.config = {
      // 力导向布局参数
      forceLayout: {
        attraction: 0.1,        // 连接引力
        repulsion: 1000,        // 节点斥力
        damping: 0.9,          // 阻尼系数
        iterations: 100,        // 最大迭代次数
        threshold: 0.01,        // 停止阈值
        centerForce: 0.05,     // 中心引力
        avoidOverlap: true     // 避免重叠
      },
      
      // 层次布局参数
      hierarchical: {
        levelSeparation: 120,   // 层级间距
        nodeSeparation: 80,     // 节点间距
        direction: 'vertical',  // 'vertical' | 'horizontal'
        sortMethod: 'directed'  // 'hubsize' | 'directed'
      },
      
      // 聚类布局参数
      cluster: {
        clusterSeparation: 150, // 集群间距
        clusterPadding: 30,     // 集群内边距
        avoidOverlap: true
      },
      
      ...options
    };
    
    // 布局计算缓存
    this.cache = {
      lastLayout: null,
      forces: new Map(),
      positions: new Map()
    };
  }
  
  /**
   * 计算布局
   */
  calculateLayout(nodes, links, layoutType = 'force', options = {}) {
    const startTime = this.getHighResTime();
    
    // 合并配置
    const config = { ...this.config, ...options };
    
    let result;
    
    switch (layoutType) {
      case 'force':
        result = this.forceDirectedLayout(nodes, links, config);
        break;
      case 'hierarchical':
        result = this.hierarchicalLayout(nodes, links, config);
        break;
      case 'circular':
        result = this.circularLayout(nodes, links, config);
        break;
      case 'radial':
        result = this.radialLayout(nodes, links, config);
        break;
      case 'cluster':
        result = this.clusterLayout(nodes, links, config);
        break;
      case 'grid':
        result = this.gridLayout(nodes, links, config);
        break;
      default:
        result = this.forceDirectedLayout(nodes, links, config);
    }
    
    console.log(`${layoutType}布局计算耗时: ${(this.getHighResTime() - startTime).toFixed(2)}ms`);
    
    return result;
  }
  
  /**
   * 真正的力导向布局算法
   */
  forceDirectedLayout(nodes, links, config) {
    const { width = 350, height = 400, centerX = width / 2, centerY = height / 2 } = config;
    const { forceLayout } = config;
    
    // 克隆节点数据，避免修改原数据
    const layoutNodes = nodes.map(node => ({
      ...node,
      vx: 0,  // x方向速度
      vy: 0,  // y方向速度
      fx: node.level === 0 ? centerX : null,  // 固定x坐标（中心节点）
      fy: node.level === 0 ? centerY : null   // 固定y坐标（中心节点）
    }));
    
    // 初始化位置
    this.initializePositions(layoutNodes, centerX, centerY);
    
    // 构建连接映射
    const linkMap = this.buildLinkMap(links);
    
    // 迭代计算
    let iteration = 0;
    let maxMovement = Infinity;
    
    while (iteration < forceLayout.iterations && maxMovement > forceLayout.threshold) {
      maxMovement = this.forceIteration(layoutNodes, linkMap, forceLayout, width, height);
      iteration++;
    }
    
    console.log(`力导向布局收敛: ${iteration}次迭代, 最大移动: ${maxMovement.toFixed(4)}`);
    
    // 后处理：避免重叠
    if (forceLayout.avoidOverlap) {
      this.resolveOverlaps(layoutNodes);
    }
    
    return {
      nodes: layoutNodes.map(node => ({
        ...node,
        x: Math.round(node.x),
        y: Math.round(node.y)
      })),
      links
    };
  }
  
  /**
   * 初始化节点位置
   */
  initializePositions(nodes, centerX, centerY) {
    const centerNode = nodes.find(n => n.level === 0);
    const otherNodes = nodes.filter(n => n.level > 0);
    
    // 中心节点固定位置
    if (centerNode && (centerNode.x === undefined || centerNode.y === undefined)) {
      centerNode.x = centerX;
      centerNode.y = centerY;
      centerNode.vx = 0;
      centerNode.vy = 0;
    }
    
    // 其他节点随机分布（但避免太靠近中心）
    otherNodes.forEach((node, index) => {
      if (node.x === undefined || node.y === undefined) {
        const angle = (index / otherNodes.length) * 2 * Math.PI;
        const radius = 80 + Math.random() * 60;
        node.x = centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 40;
        node.y = centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 40;
      }
      // 确保所有节点都有初始速度
      if (node.vx === undefined) node.vx = 0;
      if (node.vy === undefined) node.vy = 0;
    });
    
    console.log('节点初始化完成:', {
      centerNode: centerNode ? { x: centerNode.x, y: centerNode.y } : null,
      otherNodes: otherNodes.map(n => ({ name: n.name, x: n.x, y: n.y }))
    });
  }
  
  /**
   * 构建连接映射
   */
  buildLinkMap(links) {
    const linkMap = new Map();
    
    links.forEach(link => {
      const sourceId = link.source;
      const targetId = link.target;
      
      if (!linkMap.has(sourceId)) {
        linkMap.set(sourceId, []);
      }
      if (!linkMap.has(targetId)) {
        linkMap.set(targetId, []);
      }
      
      linkMap.get(sourceId).push({ 
        node: targetId, 
        strength: link.confidence_score || 0.5,
        distance: this.calculateDesiredDistance(link)
      });
      
      linkMap.get(targetId).push({ 
        node: sourceId, 
        strength: link.confidence_score || 0.5,
        distance: this.calculateDesiredDistance(link)
      });
    });
    
    return linkMap;
  }
  
  /**
   * 计算理想连接距离
   */
  calculateDesiredDistance(link) {
    const confidence = link.confidence_score || 0.5;
    // 高置信度的关系应该更靠近
    return 60 + (1 - confidence) * 80;  // 60-140px
  }
  
  /**
   * 单次力导向迭代
   */
  forceIteration(nodes, linkMap, config, width, height) {
    const { attraction, repulsion, damping, centerForce } = config;
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    
    // 确保所有节点都有速度属性
    nodes.forEach(node => {
      if (node.vx === undefined) node.vx = 0;
      if (node.vy === undefined) node.vy = 0;
    });
    
    let maxMovement = 0;
    let forceCalculatedNodes = 0;
    
    // 计算所有节点的受力
    nodes.forEach(node => {
      // 跳过明确标记为固定的节点
      if (node.fx !== undefined && node.fx !== null) return;
      if (node.fy !== undefined && node.fy !== null) return;
      
      let fx = 0, fy = 0;
      
      // 1. 连接引力（弹簧力）
      const connections = linkMap.get(node.id) || [];
      connections.forEach(conn => {
        const other = nodeMap.get(conn.node);
        if (!other) return;
        
        const dx = other.x - node.x;
        const dy = other.y - node.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // 数值稳定性：避免除零和极小距离
        if (distance > 1.0) {
          const force = attraction * conn.strength * (distance - conn.distance);
          fx += (dx / distance) * force;
          fy += (dy / distance) * force;
        }
      });
      
      // 2. 节点斥力（库伦力）
      nodes.forEach(other => {
        if (other === node) return;
        
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // 数值稳定性：最小距离保护，避免过强斥力
        const minDistance = 10;
        const maxDistance = 200;
        if (distance > minDistance && distance < maxDistance) {
          const safeDistance = Math.max(distance, minDistance);
          const force = repulsion / (safeDistance * safeDistance);
          fx += (dx / safeDistance) * force;
          fy += (dy / safeDistance) * force;
        }
      });
      
      // 3. 中心引力
      const centerX = width / 2;
      const centerY = height / 2;
      const toCenterX = centerX - node.x;
      const toCenterY = centerY - node.y;
      fx += toCenterX * centerForce;
      fy += toCenterY * centerForce;
      
      // 4. 边界约束力
      const margin = 50;
      if (node.x < margin) fx += (margin - node.x) * 0.1;
      if (node.x > width - margin) fx -= (node.x - (width - margin)) * 0.1;
      if (node.y < margin) fy += (margin - node.y) * 0.1;
      if (node.y > height - margin) fy -= (node.y - (height - margin)) * 0.1;
      
      // 更新速度（带阻尼）
      node.vx = (node.vx + fx) * damping;
      node.vy = (node.vy + fy) * damping;
      
      // 速度限制
      const maxVelocity = 10;
      const velocity = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      if (velocity > maxVelocity) {
        node.vx = (node.vx / velocity) * maxVelocity;
        node.vy = (node.vy / velocity) * maxVelocity;
      }
      
      // 更新位置
      node.x += node.vx;
      node.y += node.vy;
      
      // 记录最大移动距离
      const movement = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      maxMovement = Math.max(maxMovement, movement);
      forceCalculatedNodes++;
    });
    
    // 调试信息：每10次迭代输出一次状态
    if (Math.random() < 0.1) { // 10%概率输出，避免刷屏
      console.log('力导向迭代状态:', {
        计算节点数: forceCalculatedNodes,
        总节点数: nodes.length,
        最大移动: maxMovement.toFixed(4),
        配置: { attraction, repulsion, damping, centerForce }
      });
    }
    
    return maxMovement;
  }
  
  /**
   * 解决节点重叠
   */
  resolveOverlaps(nodes) {
    const iterations = 10;
    
    for (let i = 0; i < iterations; i++) {
      let hasOverlap = false;
      
      for (let a = 0; a < nodes.length; a++) {
        for (let b = a + 1; b < nodes.length; b++) {
          const nodeA = nodes[a];
          const nodeB = nodes[b];
          
          const dx = nodeB.x - nodeA.x;
          const dy = nodeB.y - nodeA.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          const minDistance = 45; // 最小距离
          
          if (distance < minDistance && distance > 0) {
            hasOverlap = true;
            
            const overlap = minDistance - distance;
            const separationX = (dx / distance) * (overlap * 0.5);
            const separationY = (dy / distance) * (overlap * 0.5);
            
            // 移动两个节点以解决重叠
            if (nodeA.fx === null) {
              nodeA.x -= separationX;
              nodeA.y -= separationY;
            }
            if (nodeB.fx === null) {
              nodeB.x += separationX;
              nodeB.y += separationY;
            }
          }
        }
      }
      
      if (!hasOverlap) break;
    }
  }
  
  /**
   * 层次布局（树形布局）
   */
  hierarchicalLayout(nodes, links, config) {
    const { width = 350, height = 400 } = config;
    const { hierarchical } = config;
    
    // 找到根节点（level为0的节点）
    const rootNode = nodes.find(n => n.level === 0);
    if (!rootNode) {
      return this.circularLayout(nodes, links, config);
    }
    
    // 按层级分组
    const levels = {};
    nodes.forEach(node => {
      const level = node.level || 0;
      if (!levels[level]) levels[level] = [];
      levels[level].push(node);
    });
    
    const maxLevel = Math.max(...Object.keys(levels).map(Number));
    const levelHeight = hierarchical.direction === 'vertical' ? 
      (height - 60) / (maxLevel || 1) : hierarchical.levelSeparation;
    
    // 计算每层节点位置
    Object.entries(levels).forEach(([level, levelNodes]) => {
      const levelNum = parseInt(level);
      const nodeCount = levelNodes.length;
      
      if (hierarchical.direction === 'vertical') {
        const y = 30 + levelNum * levelHeight;
        const startX = (width - (nodeCount - 1) * hierarchical.nodeSeparation) / 2;
        
        levelNodes.forEach((node, index) => {
          node.x = Math.max(30, Math.min(width - 30, startX + index * hierarchical.nodeSeparation));
          node.y = y;
        });
      } else {
        // 水平布局
        const x = 30 + levelNum * levelHeight;
        const startY = (height - (nodeCount - 1) * hierarchical.nodeSeparation) / 2;
        
        levelNodes.forEach((node, index) => {
          node.x = x;
          node.y = Math.max(30, Math.min(height - 30, startY + index * hierarchical.nodeSeparation));
        });
      }
    });
    
    return { nodes, links };
  }
  
  /**
   * 改进的环形布局
   */
  circularLayout(nodes, links, config) {
    const { width = 350, height = 400, centerX = width / 2, centerY = height / 2 } = config;
    
    const centerNode = nodes.find(n => n.level === 0);
    const otherNodes = nodes.filter(n => n.level > 0);
    
    // 中心节点
    if (centerNode) {
      centerNode.x = centerX;
      centerNode.y = centerY;
    }
    
    // 按关系强度分组
    const groupedNodes = this.groupNodesByRelationshipStrength(otherNodes, links);
    
    let currentRadius = 80;
    const radiusIncrement = 60;
    
    groupedNodes.forEach(group => {
      const nodeCount = group.length;
      if (nodeCount === 0) return;
      
      // 确保有足够空间
      const circumference = 2 * Math.PI * currentRadius;
      const neededSpace = nodeCount * 50; // 每个节点需要50px空间
      
      if (neededSpace > circumference) {
        currentRadius = neededSpace / (2 * Math.PI);
      }
      
      const angleStep = (2 * Math.PI) / nodeCount;
      
      group.forEach((node, index) => {
        const angle = angleStep * index;
        node.x = centerX + currentRadius * Math.cos(angle);
        node.y = centerY + currentRadius * Math.sin(angle);
      });
      
      currentRadius += radiusIncrement;
    });
    
    return { nodes, links };
  }
  
  /**
   * 径向布局（考虑连接密度）
   */
  radialLayout(nodes, links, config) {
    const { width = 350, height = 400, centerX = width / 2, centerY = height / 2 } = config;
    
    // 计算节点度数（连接数）
    const nodeDegree = new Map();
    nodes.forEach(node => nodeDegree.set(node.id, 0));
    
    links.forEach(link => {
      nodeDegree.set(link.source, (nodeDegree.get(link.source) || 0) + 1);
      nodeDegree.set(link.target, (nodeDegree.get(link.target) || 0) + 1);
    });
    
    // 按度数排序
    const sortedNodes = [...nodes].sort((a, b) => {
      const degreeA = nodeDegree.get(a.id) || 0;
      const degreeB = nodeDegree.get(b.id) || 0;
      return degreeB - degreeA; // 降序
    });
    
    // 中心节点或度数最高的节点
    const centerNode = nodes.find(n => n.level === 0) || sortedNodes[0];
    centerNode.x = centerX;
    centerNode.y = centerY;
    
    // 其他节点按度数分层放置
    const otherNodes = sortedNodes.filter(n => n !== centerNode);
    let currentRadius = 70;
    const maxNodesPerLayer = 8;
    
    for (let i = 0; i < otherNodes.length; i += maxNodesPerLayer) {
      const layerNodes = otherNodes.slice(i, i + maxNodesPerLayer);
      const angleStep = (2 * Math.PI) / layerNodes.length;
      
      layerNodes.forEach((node, index) => {
        const angle = angleStep * index;
        node.x = centerX + currentRadius * Math.cos(angle);
        node.y = centerY + currentRadius * Math.sin(angle);
      });
      
      currentRadius += 70;
    }
    
    return { nodes, links };
  }
  
  /**
   * 聚类布局
   */
  clusterLayout(nodes, links, config) {
    const { width = 350, height = 400 } = config;
    const { cluster } = config;
    
    // 按关系类型聚类
    const clusters = this.clusterNodesByRelationshipType(nodes, links);
    
    // 计算聚类布局
    const clusterPositions = this.calculateClusterPositions(clusters, width, height, cluster);
    
    // 为每个聚类内的节点布局
    Object.entries(clusters).forEach(([type, clusterNodes]) => {
      const clusterPos = clusterPositions[type];
      this.layoutNodesInCluster(clusterNodes, clusterPos, cluster);
    });
    
    return { nodes, links };
  }
  
  /**
   * 按关系强度分组节点
   */
  groupNodesByRelationshipStrength(nodes, links) {
    const nodeStrengths = new Map();
    
    // 计算每个节点的平均关系强度
    links.forEach(link => {
      const strength = link.confidence_score || 0.5;
      const source = link.source;
      const target = link.target;
      
      nodeStrengths.set(source, (nodeStrengths.get(source) || 0) + strength);
      nodeStrengths.set(target, (nodeStrengths.get(target) || 0) + strength);
    });
    
    // 按强度分组
    const groups = [[], [], []]; // 高、中、低三组
    
    nodes.forEach(node => {
      const avgStrength = (nodeStrengths.get(node.id) || 0) / Math.max(1, 
        links.filter(l => l.source === node.id || l.target === node.id).length
      );
      
      if (avgStrength > 0.7) groups[0].push(node);
      else if (avgStrength > 0.4) groups[1].push(node);
      else groups[2].push(node);
    });
    
    return groups.filter(group => group.length > 0);
  }
  
  /**
   * 按关系类型聚类节点
   */
  clusterNodesByRelationshipType(nodes, links) {
    const clusters = {};
    const nodeTypes = new Map();
    
    // 分析每个节点的主要关系类型
    links.forEach(link => {
      const type = link.type || 'unknown';
      
      [link.source, link.target].forEach(nodeId => {
        if (!nodeTypes.has(nodeId)) {
          nodeTypes.set(nodeId, new Map());
        }
        const typeCount = nodeTypes.get(nodeId);
        typeCount.set(type, (typeCount.get(type) || 0) + 1);
      });
    });
    
    // 将节点分配到主要关系类型的聚类中
    nodes.forEach(node => {
      const typeCounts = nodeTypes.get(node.id) || new Map();
      let mainType = 'unknown';
      let maxCount = 0;
      
      typeCounts.forEach((count, type) => {
        if (count > maxCount) {
          maxCount = count;
          mainType = type;
        }
      });
      
      if (!clusters[mainType]) clusters[mainType] = [];
      clusters[mainType].push(node);
    });
    
    return clusters;
  }
  
  /**
   * 计算聚类位置
   */
  calculateClusterPositions(clusters, width, height, config) {
    const clusterCount = Object.keys(clusters).length;
    const positions = {};
    
    // 使用圆形分布聚类
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.3;
    
    Object.keys(clusters).forEach((type, index) => {
      const angle = (2 * Math.PI * index) / clusterCount;
      positions[type] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
    
    return positions;
  }
  
  /**
   * 在聚类内布局节点
   */
  layoutNodesInCluster(nodes, clusterCenter, config) {
    const nodeCount = nodes.length;
    const radius = Math.max(30, Math.sqrt(nodeCount) * 15);
    
    if (nodeCount === 1) {
      nodes[0].x = clusterCenter.x;
      nodes[0].y = clusterCenter.y;
      return;
    }
    
    const angleStep = (2 * Math.PI) / nodeCount;
    nodes.forEach((node, index) => {
      const angle = angleStep * index;
      node.x = clusterCenter.x + radius * Math.cos(angle);
      node.y = clusterCenter.y + radius * Math.sin(angle);
    });
  }
  
  /**
   * 网格布局
   */
  gridLayout(nodes, links, config) {
    const { width = 350, height = 400 } = config;
    const margin = 40;
    
    // 计算网格尺寸
    const nodeCount = nodes.length;
    const cols = Math.ceil(Math.sqrt(nodeCount));
    const rows = Math.ceil(nodeCount / cols);
    
    const cellWidth = (width - 2 * margin) / cols;
    const cellHeight = (height - 2 * margin) / rows;
    
    // 按重要性排序（中心节点优先）
    const sortedNodes = [...nodes].sort((a, b) => {
      if (a.level === 0) return -1;
      if (b.level === 0) return 1;
      return 0;
    });
    
    sortedNodes.forEach((node, index) => {
      const row = Math.floor(index / cols);
      const col = index % cols;
      
      node.x = margin + col * cellWidth + cellWidth / 2;
      node.y = margin + row * cellHeight + cellHeight / 2;
    });
    
    return { nodes, links };
  }

  /**
   * 获取高精度时间戳（毫秒） - 兼容微信小程序
   */
  getHighResTime() {
    // 微信小程序环境下 performance 对象可能不存在
    if (typeof performance !== 'undefined' && performance.now) {
      return performance.now();
    }
    
    // 降级到 Date.now()
    return Date.now();
  }
}

export default AdvancedLayoutEngine;