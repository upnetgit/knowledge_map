#!/usr/bin/env python3
"""
跨模态知识图谱Web查询界面
提供图形化界面查询和可视化
"""

import json
import logging
from typing import List, Dict, Tuple
from neo4j import GraphDatabase
from flask import Flask, request, jsonify, render_template_string
import networkx as nx
from .processors import VideoEditor
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>跨模态知识图谱查询系统</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
            padding: 30px;
        }
        
        .sidebar {
            border-right: 2px solid #eee;
            padding-right: 20px;
        }
        
        .section {
            margin-bottom: 30px;
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            padding: 12px 25px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            transition: background 0.3s;
        }
        
        button:hover {
            background: #764ba2;
        }
        
        .results {
            background: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .result-item {
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            border-radius: 3px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .result-item:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }
        
        .result-item .entity-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        
        .result-item .relation {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .result-item .media-info {
            font-size: 0.85em;
            color: #999;
        }
        
        #graph-container {
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #f8f9fa;
            height: 600px;
            position: relative;
        }
        
        .legend {
            margin-top: 15px;
            font-size: 0.9em;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .legend-color {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .tooltip {
            position: absolute;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 0.9em;
            pointer-events: none;
            z-index: 1000;
        }
        
        .stats {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .stat-item {
            background: white;
            padding: 12px;
            border-radius: 5px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        
        .video-container {
            margin-top: 20px;
            background: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
        }
        
        .video-item {
            margin-bottom: 15px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #5cb85c;
        }
        
        .video-item video {
            width: 100%;
            max-height: 300px;
            border-radius: 5px;
        }
        
        .entity-section {
            margin-bottom: 20px;
        }
        
        .entity-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .entity-tag {
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            color: #495057;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 跨模态知识图谱查询系统</h1>
            <p>连接计算机和思想实体的多模态知识网络</p>
        </div>
        
        <div class="content">
            <div class="sidebar">
                <div class="section">
                    <h2>🔍 查询</h2>
                    <div class="search-box">
                        <input type="text" id="searchInput" placeholder="输入实体名称...">
                        <button onclick="searchEntity()">查询</button>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📊 结果</h2>
                    <div class="results" id="results"></div>
                </div>
                
                <div class="section">
                    <h2>📈 统计</h2>
                    <div id="stats"></div>
                </div>
            </div>
            
            <div class="main">
                <div class="section">
                    <h2>🗺️ 知识图谱可视化</h2>
                    <div id="graph-container"></div>
                    <div class="legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #667eea;"></div>
                            <span>文本实体 (连接媒体数)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #f0ad4e;"></div>
                            <span>图像 (图像标注)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #5cb85c;"></div>
                            <span>视频 (视频标注)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #d9534f;"></div>
                            <span>实体关系</span>
                        </div>
                    </div>
                </div>
                
                <div class="section entity-section">
                    <h2>📂 实体详情</h2>
                    <div id="entityDetails"></div>
                </div>
                
                <div class="section video-container">
                    <h2>📹 视频播放</h2>
                    <div id="videoPlayer"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 初始化知识图谱
        function initializeGraph() {
            fetch('/api/graph')
                .then(response => response.json())
                .then(data => {
                    renderGraph(data);
                    updateStats(data.stats);
                })
                .catch(error => console.error('Error:', error));
        }
        
        // 渲染知识图谱
        function renderGraph(data) {
            const container = document.getElementById('graph-container');
            container.innerHTML = ''; // 清空容器
            
            const width = container.offsetWidth;
            const height = container.offsetHeight;
            
            const svg = d3.select('#graph-container')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const simulation = d3.forceSimulation(data.nodes)
                .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));
            
            const links = svg.selectAll('line')
                .data(data.links)
                .enter()
                .append('line')
                .attr('stroke', '#999')
                .attr('stroke-opacity', 0.6)
                .attr('stroke-width', d => Math.sqrt(d.strength) * 2);
            
            const nodes = svg.selectAll('circle')
                .data(data.nodes)
                .enter()
                .append('circle')
                .attr('r', d => 5 + d.connections * 2)
                .attr('fill', d => {
                    if (d.type === 'image') return '#f0ad4e';
                    if (d.type === 'video') return '#5cb85c';
                    return '#667eea';
                })
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            const labels = svg.selectAll('text')
                .data(data.nodes)
                .enter()
                .append('text')
                .attr('x', 0)
                .attr('y', 0)
                .attr('dy', '.35em')
                .attr('text-anchor', 'middle')
                .text(d => d.id.substring(0, 10))
                .attr('font-size', '12px')
                .attr('fill', '#333');
            
            simulation.on('tick', () => {
                links
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                nodes
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                
                labels
                    .attr('x', d => d.x)
                    .attr('y', d => d.y);
            });
            
            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }
            
            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }
            
            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
        }
        
        // 搜索实体
        function searchEntity() {
            const entity = document.getElementById('searchInput').value;
            if (!entity) return;
            
            fetch(`/api/query?entity=${encodeURIComponent(entity)}`)
                .then(response => response.json())
                .then(data => {
                    displayResults(data);
                    displayEntityDetails(entity);
                })
                .catch(error => console.error('Error:', error));
        }
        
        // 显示搜索结果
        function displayResults(results) {
            const container = document.getElementById('results');
            container.innerHTML = '';
            
            if (results.length === 0) {
                container.innerHTML = '<div style="color: #999;">未找到相关实体</div>';
                return;
            }
            
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'result-item';
                item.innerHTML = `
                    <div class="entity-name">${result.entity}</div>
                    <div class="relation">关系: ${result.relation}</div>
                    <div class="media-info">媒体: ${result.media || 'N/A'}</div>
                `;
                container.appendChild(item);
            });
        }
        
        // 显示实体详情
        function displayEntityDetails(entity) {
            const container = document.getElementById('entityDetails');
            container.innerHTML = `<div style="color: #666;">加载中...</div>`;
            
            fetch(`/api/query_advanced?entity=${encodeURIComponent(entity)}`)
                .then(response => response.json())
                .then(data => {
                    container.innerHTML = '';
                    
                    // 显示相似实体
                    if (data.similar.length > 0) {
                        const similarSection = document.createElement('div');
                        similarSection.className = 'section';
                        similarSection.innerHTML = '<h3>相似实体</h3>';
                        
                        data.similar.forEach(item => {
                            const tag = document.createElement('div');
                            tag.className = 'entity-tag';
                            tag.innerText = item.entity;
                            similarSection.appendChild(tag);
                        });
                        
                        container.appendChild(similarSection);
                    }
                    
                    // 显示相关实体
                    if (data.related.length > 0) {
                        const relatedSection = document.createElement('div');
                        relatedSection.className = 'section';
                        relatedSection.innerHTML = '<h3>相关实体</h3>';
                        
                        data.related.forEach(item => {
                            const tag = document.createElement('div');
                            tag.className = 'entity-tag';
                            tag.innerText = item.entity;
                            relatedSection.appendChild(tag);
                        });
                        
                        container.appendChild(relatedSection);
                    }
                    
                    // 显示视频
                    if (data.videos.length > 0) {
                        const videoSection = document.getElementById('videoPlayer');
                        videoSection.innerHTML = '';
                        
                        data.videos.forEach(video => {
                            const videoItem = document.createElement('div');
                            videoItem.className = 'video-item';
                            videoItem.innerHTML = `
                                <h4>${video.name}</h4>
                                <p>${video.caption}</p>
                                <video controls>
                                    <source src="${video.clip_path}" type="video/mp4">
                                    您的浏览器不支持视频标签。
                                </video>
                            `;
                            videoSection.appendChild(videoItem);
                        });
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    container.innerHTML = `<div style="color: red;">加载失败</div>`;
                });
        }
        
        // 更新统计信息
        function updateStats(stats) {
            const container = document.getElementById('stats');
            container.innerHTML = `
                <div class="stats">
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-value">${stats.total_nodes}</div>
                            <div class="stat-label">实体数量</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${stats.total_edges}</div>
                            <div class="stat-label">关系数量</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', initializeGraph);
    </script>
</body>
</html>
'''


class Neo4jQuery:
    """Neo4j数据库查询器"""
    
    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "password"):
        """
        初始化查询器
        
        Args:
            uri: Neo4j数据库URI
            user: 用户名
            password: 密码
        """
        self.uri = uri
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self._test_connection()
        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            self.driver = None
    
    def _test_connection(self):
        """测试连接"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as num")
                result.single()
            logger.info("Neo4j连接成功")
        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            raise
    
    def query_connected_entities(self, entity: str) -> List[Dict]:
        """
        查询与某个实体相连的所有实体
        
        Args:
            entity: 实体名称
            
        Returns:
            相连实体列表
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (a:Entity {name: $entity})-[r:CONNECTED]->(b:Entity)
                    RETURN b.name as entity, r.type as relation, r.caption as caption
                    LIMIT 20
                """, entity=entity)
                
                return [
                    {
                        "entity": record["entity"],
                        "relation": record["relation"],
                        "caption": record["caption"]
                    }
                    for record in result
                ]
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return []
    
    def get_graph_data(self) -> Dict:
        """
        获取整个知识图谱的可视化数据
        
        Returns:
            包含节点和边的字典
        """
        if not self.driver:
            return {"nodes": [], "links": [], "stats": {"total_nodes": 0, "total_edges": 0}}
        
        try:
            with self.driver.session() as session:
                # 获取所有节点
                nodes_result = session.run("""
                    MATCH (n:Entity)
                    RETURN n.name as name, COUNT {(n)-[]->()} as connections
                    LIMIT 100
                """)
                
                nodes = [
                    {
                        "id": record["name"],
                        "connections": record["connections"],
                        "type": "entity"
                    }
                    for record in nodes_result
                ]
                
                # 获取所有边
                edges_result = session.run("""
                    MATCH (a:Entity)-[r:CONNECTED]->(b:Entity)
                    RETURN a.name as source, b.name as target, r.type as type
                    LIMIT 200
                """)
                
                links = [
                    {
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"],
                        "strength": 1.0
                    }
                    for record in edges_result
                ]
                
                # 获取统计信息
                stats_result = session.run("""
                    MATCH (n:Entity)
                    RETURN COUNT(n) as total_nodes
                """)
                total_nodes = stats_result.single()["total_nodes"]
                
                return {
                    "nodes": nodes,
                    "links": links,
                    "stats": {
                        "total_nodes": total_nodes,
                        "total_edges": len(links)
                    }
                }
        except Exception as e:
            logger.error(f"获取图数据失败: {str(e)}")
            return {"nodes": [], "links": [], "stats": {"total_nodes": 0, "total_edges": 0}}
    
    def query_similar_and_related_entities(self, entity: str, data_dir: str) -> Dict:
        """
        查询相似的计算机实体和相关的思政实体
        
        Args:
            entity: 输入实体名称
            data_dir: 数据目录
            
        Returns:
            包含相似实体、相关实体和视频信息的字典
        """
        if not self.driver:
            return {"similar": [], "related": [], "videos": []}
        
        try:
            with self.driver.session() as session:
                # 查询相似实体（同类实体）
                similar_result = session.run("""
                    MATCH (a:Entity {name: $entity})-[r:SIMILAR]->(b:Entity)
                    RETURN b.name as entity, r.similarity as similarity
                    ORDER BY r.similarity DESC
                    LIMIT 10
                """, entity=entity)
                
                similar_entities = [
                    {
                        "entity": record["entity"],
                        "similarity": record["similarity"]
                    }
                    for record in similar_result
                ]
                
                # 查询相关实体（不同类实体）
                related_result = session.run("""
                    MATCH (a:Entity {name: $entity})-[r:RELATED]->(b:Entity)
                    RETURN b.name as entity, r.similarity as similarity
                    ORDER BY r.similarity DESC
                    LIMIT 10
                """, entity=entity)
                
                related_entities = [
                    {
                        "entity": record["entity"],
                        "similarity": record["similarity"]
                    }
                    for record in related_result
                ]
                
                # 查询相关视频
                video_result = session.run("""
                    MATCH (a:Entity {name: $entity})-[r:CONNECTED]->(v:Entity)
                    WHERE r.type = 'connected_by_video'
                    RETURN v.name as video_name, r.caption as caption, r.media_path as path
                    LIMIT 5
                """, entity=entity)
                
                videos = []
                video_editor = VideoEditor()
                
                for record in video_result:
                    video_name = record["video_name"]
                    video_path = record["path"]
                    
                    # 剪辑1分钟视频片段
                    if video_path and os.path.exists(video_path):
                        duration = video_editor.get_video_duration(video_path)
                        if duration > 60:
                            # 从视频中间剪辑1分钟
                            start_time = max(0, (duration - 60) / 2)
                            clip_path = os.path.join(data_dir, 'clips', f"{video_name}_clip.mp4")
                            os.makedirs(os.path.dirname(clip_path), exist_ok=True)
                            
                            if video_editor.clip_video(video_path, clip_path, start_time, 60):
                                videos.append({
                                    "name": video_name,
                                    "caption": record["caption"],
                                    "clip_path": clip_path
                                })
                        else:
                            # 视频短于1分钟，直接使用原视频
                            videos.append({
                                "name": video_name,
                                "caption": record["caption"],
                                "clip_path": video_path
                            })
                }

                return {
                    "similar": similar_entities,
                    "related": related_entities,
                    "videos": videos
                }
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return {"similar": [], "related": [], "videos": []}
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()


# 全局查询器
neo4j_query = None

def get_neo4j_query():
    """获取或创建Neo4j查询器"""
    global neo4j_query
    if neo4j_query is None:
        neo4j_query = Neo4jQuery(
            uri=app.config.get('NEO4J_URI', 'bolt://localhost:7687'),
            user=app.config.get('NEO4J_USER', 'neo4j'),
            password=app.config.get('NEO4J_PASSWORD', 'password')
        )
    return neo4j_query


# 路由
@app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/query', methods=['GET'])
def query():
    """查询API"""
    entity = request.args.get('entity')
    if not entity:
        return jsonify({"error": "Entity parameter required"}), 400
    
    query_engine = get_neo4j_query()
    results = query_engine.query_connected_entities(entity)
    return jsonify(results)


@app.route('/api/query_advanced', methods=['GET'])
def query_advanced():
    """高级查询API - 查询相似和相关实体"""
    entity = request.args.get('entity')
    data_dir = request.args.get('data_dir', './data')
    if not entity:
        return jsonify({"error": "Entity parameter required"}), 400
    
    query_engine = get_neo4j_query()
    results = query_engine.query_similar_and_related_entities(entity, data_dir)
    return jsonify(results)


@app.route('/api/graph', methods=['GET'])
def get_graph():
    """获取完整知识图谱数据"""
    query_engine = get_neo4j_query()
    graph_data = query_engine.get_graph_data()
    return jsonify(graph_data)


@app.route('/video/<path:filename>')
def serve_video(filename):
    """提供视频文件服务"""
    from flask import send_from_directory
    video_dir = os.path.join(app.root_path, 'data', 'clips')
    return send_from_directory(video_dir, filename)


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({"error": "Internal server error"}), 500


@app.teardown_appcontext
def shutdown_session(exception=None):
    """应用关闭时关闭连接"""
    global neo4j_query
    if neo4j_query:
        neo4j_query.close()


if __name__ == '__main__':
    # 配置
    app.config['NEO4J_URI'] = 'bolt://localhost:7687'
    app.config['NEO4J_USER'] = 'neo4j'
    app.config['NEO4J_PASSWORD'] = 'password'
    
    logger.info("启动Flask服务器...")
    logger.info("访问: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
