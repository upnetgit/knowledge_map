#!/usr/bin/env python3
"""
改进的知识图谱构建器
支持文本、图像、视频的多模态处理
"""

import os
import json
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime

try:
    import spacy
except ImportError:
    spacy = None

from neo4j import GraphDatabase
import networkx as nx

from .processors import TextProcessor, ImageProcessor, VideoProcessor, CaptionGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KGBuilder:
    """知识图谱构建器"""
    
    def __init__(self, 
                 neo4j_uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "password",
                 language: str = "zh"):
        """
        初始化知识图谱构建器

        Args:
            neo4j_uri: Neo4j数据库URI
            user: 数据库用户名
            password: 数据库密码
            language: 语言（zh或en）
        """
        self.neo4j_uri = neo4j_uri
        self.user = user
        self.password = password
        self.language = language
        
        # 初始化处理器
        try:
            nlp = spacy.load("zh_core_web_sm" if language == "zh" else "en_core_web_sm")
        except:
            logger.warning("无法加载spaCy模型，尝试默认模型")
            nlp = None
        
        self.text_processor = TextProcessor(nlp_model=nlp)
        self.image_processor = ImageProcessor()
        self.video_processor = VideoProcessor()
        self.caption_generator = CaptionGenerator()
        
        # 知识图谱数据结构
        self.graph = nx.DiGraph()  # 有向图
        self.entity_metadata = {}
        self.relations = defaultdict(list)
        
        # 预定义实体类型
        self.entity_types = {
            'computer_science': [],  # 计算机核心知识点
            'ideology': []  # 思政元素
        }

        # 连接Neo4j
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
            self._test_connection()
            logger.info("已连接到Neo4j数据库")
        except Exception as e:
            logger.error(f"连接Neo4j失败: {str(e)}")
            self.driver = None
    
    def _test_connection(self):
        """测试Neo4j连接"""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return False
    
    def _load_known_entities(self, txt_dir: str) -> Dict[str, Dict]:
        """
        从文本文件加载已知实体
        
        Args:
            txt_dir: 文本目录
            
        Returns:
            实体字典 {entity_name: {type, source, keywords}}
        """
        logger.info("正在加载已知实体...")
        known_entities = {}
        
        txt_data = self.text_processor.load_txt_files(txt_dir)
        
        for filename, data in txt_data.items():
            # 处理所有实体
            for entity_type, entities in data['entities'].items():
                for entity in entities:
                    if entity not in known_entities:
                        known_entities[entity] = {
                            'type': entity_type,
                            'source': filename,
                            'keywords': set(),
                            'count': 0
                        }
                    known_entities[entity]['count'] += 1
                    known_entities[entity]['keywords'].update(data['keywords'])
        
        logger.info(f"已加载 {len(known_entities)} 个已知实体")
        return known_entities
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """
        从文本提取实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        entities_dict = self.text_processor.extract_entities(text)
        entities = []
        for entity_list in entities_dict.values():
            entities.extend(entity_list)
        return list(set(entities))
    
    def _match_entities(self, 
                       caption_entities: List[str],
                       known_entities: Dict[str, Dict]) -> List[Tuple[str, float]]:
        """
        将图像/视频描述中的实体与已知实体匹配
        
        Args:
            caption_entities: 描述中的实体
            known_entities: 已知实体字典
            
        Returns:
            匹配的实体及相似度列表
        """
        matches = []
        
        # 精确匹配
        for entity in caption_entities:
            if entity in known_entities:
                matches.append((entity, 1.0))
        
        # 模糊匹配（子串匹配）
        for caption_entity in caption_entities:
            for known_entity in known_entities:
                if caption_entity.lower() in known_entity.lower() or \
                   known_entity.lower() in caption_entity.lower():
                    if (known_entity, 1.0) not in matches:
                        matches.append((known_entity, 0.8))
        
        return matches
    
    def build_kg(self, data_dir: str, output_dir: str = 'kg_output', 
                computer_entities: List[str] = None, ideology_entities: List[str] = None,
                custom_relations: List[Tuple[str, str, str]] = None):
        """
        构建完整的知识图谱
        
        Args:
            data_dir: 数据目录
            output_dir: 输出目录
            computer_entities: 计算机核心知识点实体列表
            ideology_entities: 思政元素实体列表
            custom_relations: 自定义关系列表 [(entity1, entity2, relation_type), ...]
        """
        logger.info("=" * 50)
        logger.info("开始构建知识图谱")
        logger.info("=" * 50)
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 第一步：预先插入实体
        if computer_entities and ideology_entities:
            self.insert_predefined_entities(computer_entities, ideology_entities)
        
        # 第二步：创建自定义关系
        if custom_relations:
            self.create_custom_relations(custom_relations)
        
        # 第三步：加载已知实体
        txt_dir = os.path.join(data_dir, 'txt')
        known_entities = self._load_known_entities(txt_dir)
        
        # 保存已知实体
        self._save_entities_to_json(
            known_entities,
            os.path.join(output_dir, 'known_entities.json')
        )
        
        # 第四步：处理图像
        img_dir = os.path.join(data_dir, 'img')
        if os.path.exists(img_dir):
            logger.info("\n处理图像数据...")
            self._process_images(img_dir, known_entities, output_dir)
        
        # 第五步：处理视频
        video_dir = os.path.join(data_dir, 'video')
        if os.path.exists(video_dir):
            logger.info("\n处理视频数据...")
            self._process_videos(video_dir, known_entities, output_dir)
        
        # 第六步：存储到Neo4j
        if self.driver:
            logger.info("\n存储到Neo4j数据库...")
            self._store_to_neo4j()
        
        # 第七步：保存图谱统计
        self._save_kg_stats(output_dir)
        
        logger.info("\n" + "=" * 50)
        logger.info("知识图谱构建完成")
        logger.info("=" * 50)
    
    def _process_images(self, 
                       img_dir: str,
                       known_entities: Dict[str, Dict],
                       output_dir: str):
        """处理图像并建立实体关系"""
        image_relations = {}
        images = self.image_processor.load_images(img_dir)
        
        for img_name, img_data in images.items():
            # 生成图像描述
            caption = self.caption_generator.generate_image_caption(img_data['path'])
            
            if caption:
                logger.info(f"[{img_name}] 描述: {caption}")
                
                # 从描述提取实体
                caption_entities = self._extract_entities_from_text(caption)
                
                # 匹配到已知实体
                matches = self._match_entities(caption_entities, known_entities)
                
                # 建立关系
                for matched_entity, similarity in matches:
                    relation_key = f"{matched_entity}--{img_name}"
                    image_relations[relation_key] = {
                        'source_entity': matched_entity,
                        'media': img_name,
                        'media_type': 'image',
                        'media_path': img_data['path'],
                        'category': img_data.get('category', 'unknown'),
                        'caption': caption,
                        'similarity': similarity
                    }
                    
                    # 添加到图中
                    self.graph.add_edge(matched_entity, img_name,
                                      relation='connected_by_image',
                                      similarity=similarity,
                                      caption=caption)
                    
                    self.relations['connected_by_image'].append(
                        (matched_entity, img_name, similarity)
                    )
        
        # 保存图像关系
        self._save_relations_to_json(
            image_relations,
            os.path.join(output_dir, 'image_relations.json')
        )
    
    def _process_videos(self,
                       video_dir: str,
                       known_entities: Dict[str, Dict],
                       output_dir: str):
        """处理视频并建立实体关系"""
        video_relations = {}
        videos = self.video_processor.load_videos(video_dir)
        
        for video_name, video_data in videos.items():
            # 生成视频描述
            caption = self.caption_generator.generate_video_caption(video_data['path'])
            
            if caption:
                logger.info(f"[{video_name}] 描述: {caption}")
                
                # 从描述提取实体
                caption_entities = self._extract_entities_from_text(caption)
                
                # 匹配到已知实体
                matches = self._match_entities(caption_entities, known_entities)
                
                # 建立关系
                for matched_entity, similarity in matches:
                    relation_key = f"{matched_entity}--{video_name}"
                    video_relations[relation_key] = {
                        'source_entity': matched_entity,
                        'media': video_name,
                        'media_type': 'video',
                        'media_path': video_data['path'],
                        'caption': caption,
                        'similarity': similarity,
                        'metadata': video_data['metadata']
                    }
                    
                    # 添加到图中
                    self.graph.add_edge(matched_entity, video_name,
                                      relation='connected_by_video',
                                      similarity=similarity,
                                      caption=caption)
                    
                    self.relations['connected_by_video'].append(
                        (matched_entity, video_name, similarity)
                    )
        
        # 保存视频关系
        self._save_relations_to_json(
            video_relations,
            os.path.join(output_dir, 'video_relations.json')
        )
    
    def _store_to_neo4j(self):
        """将知识图谱存储到Neo4j"""
        if not self.driver:
            logger.warning("Neo4j驱动未初始化")
            return
        
        try:
            with self.driver.session() as session:
                # 清空现有数据（可选）
                # session.run("MATCH (n) DETACH DELETE n")
                
                # 创建实体节点
                for entity_id, entity_name in enumerate(self.graph.nodes()):
                    session.run("""
                        MERGE (n:Entity {name: $name})
                        SET n.id = $id, n.created_at = $created_at
                    """, name=entity_name, id=entity_id, 
                        created_at=datetime.now().isoformat())
                
                # 创建关系
                for source, target, data in self.graph.edges(data=True):
                    session.run("""
                        MATCH (a:Entity {name: $source}), (b:Entity {name: $target})
                        MERGE (a)-[r:CONNECTED {type: $type, similarity: $similarity}]->(b)
                        SET r.caption = $caption, r.created_at = $created_at
                    """, source=source, target=target,
                        type=data.get('relation', 'CONNECTED'),
                        similarity=data.get('similarity', 0.0),
                        caption=data.get('caption', ''),
                        created_at=datetime.now().isoformat())
                
                logger.info("已存储到Neo4j数据库")
        except Exception as e:
            logger.error(f"存储到Neo4j失败: {str(e)}")
    
    def _save_entities_to_json(self, entities: Dict, filepath: str):
        """保存实体到JSON文件"""
        data = {}
        for entity_name, entity_info in entities.items():
            data[entity_name] = {
                'type': entity_info['type'],
                'source': entity_info['source'],
                'keywords': list(entity_info['keywords']),
                'count': entity_info['count']
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存实体到: {filepath}")
    
    def _save_relations_to_json(self, relations: Dict, filepath: str):
        """保存关系到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(relations, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存关系到: {filepath}")
    
    def _save_kg_stats(self, output_dir: str):
        """保存知识图谱统计信息"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'relation_types': list(self.relations.keys()),
            'relation_counts': {
                rel_type: len(rel_list)
                for rel_type, rel_list in self.relations.items()
            },
            'density': nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0
        }
        
        with open(os.path.join(output_dir, 'kg_stats.json'), 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"\n知识图谱统计:")
        logger.info(f"  - 节点数: {stats['total_nodes']}")
        logger.info(f"  - 边数: {stats['total_edges']}")
        logger.info(f"  - 密度: {stats['density']:.4f}")
        for rel_type, count in stats['relation_counts'].items():
            logger.info(f"  - {rel_type}: {count}")
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            logger.info("已关闭Neo4j连接")
    
    def insert_predefined_entities(self, computer_entities: List[str], ideology_entities: List[str]):
        """
        预先插入实体到知识图谱
        
        Args:
            computer_entities: 计算机核心知识点实体列表
            ideology_entities: 思政元素实体列表
        """
        logger.info("正在预先插入实体...")
        
        self.entity_types['computer_science'] = computer_entities
        self.entity_types['ideology'] = ideology_entities
        
        # 添加到图中
        for entity in computer_entities + ideology_entities:
            self.graph.add_node(entity, type='computer_science' if entity in computer_entities else 'ideology')
        
        # 创建相似关系（同类实体间）
        for i, entity1 in enumerate(computer_entities):
            for j, entity2 in enumerate(computer_entities):
                if i != j:
                    self.graph.add_edge(entity1, entity2, relation='similar', similarity=0.5)
                    self.relations['similar'].append((entity1, entity2, 0.5))
        
        for i, entity1 in enumerate(ideology_entities):
            for j, entity2 in enumerate(ideology_entities):
                if i != j:
                    self.graph.add_edge(entity1, entity2, relation='similar', similarity=0.5)
                    self.relations['similar'].append((entity1, entity2, 0.5))
        
        logger.info(f"已插入 {len(computer_entities)} 个计算机实体和 {len(ideology_entities)} 个思政实体")
    
    def create_custom_relations(self, relations_data: List[Tuple[str, str, str]]):
        """
        创建自定义关系
        
        Args:
            relations_data: 关系数据 [(entity1, entity2, relation_type), ...]
        """
        logger.info("正在创建自定义关系...")
        
        for entity1, entity2, rel_type in relations_data:
            if rel_type == 'related':
                similarity = 0.8
            elif rel_type == 'similar':
                similarity = 0.6
            else:
                similarity = 0.5
            
            self.graph.add_edge(entity1, entity2, relation=rel_type, similarity=similarity)
            self.relations[rel_type].append((entity1, entity2, similarity))
        
        logger.info(f"已创建 {len(relations_data)} 个自定义关系")
