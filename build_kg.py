#!/usr/bin/env python3
"""
知识图谱构建主脚本
使用方式:
    python build_kg.py          # 使用默认配置
    python build_kg.py --data-dir ./data --output-dir ./kg_output
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='构建跨模态知识图谱',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 使用默认配置
  python build_kg.py
  
  # 自定义数据目录
  python build_kg.py --data-dir /path/to/data --output-dir ./output
  
  # 跳过图像处理
  python build_kg.py --skip-images
  
  # 跳过视频处理
  python build_kg.py --skip-videos
        '''
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='./data',
        help='数据目录路径 (默认: ./data)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./kg_output',
        help='输出目录路径 (默认: ./kg_output)'
    )
    
    parser.add_argument(
        '--neo4j-uri',
        type=str,
        default='bolt://localhost:7687',
        help='Neo4j数据库URI (默认: bolt://localhost:7687)'
    )
    
    parser.add_argument(
        '--neo4j-user',
        type=str,
        default='neo4j',
        help='Neo4j用户名 (默认: neo4j)'
    )
    
    parser.add_argument(
        '--neo4j-password',
        type=str,
        default='password',
        help='Neo4j密码 (默认: password)'
    )
    
    parser.add_argument(
        '--skip-images',
        action='store_true',
        help='跳过图像处理'
    )
    
    parser.add_argument(
        '--skip-videos',
        action='store_true',
        help='跳过视频处理'
    )
    
    parser.add_argument(
        '--language',
        type=str,
        choices=['zh', 'en'],
        default='zh',
        help='语言选择 (默认: zh)'
    )
    
    parser.add_argument(
        '--computer-entities',
        type=str,
        default='',
        help='计算机核心知识点实体列表，用逗号分隔 (默认: 空)'
    )
    
    parser.add_argument(
        '--ideology-entities',
        type=str,
        default='',
        help='思政元素实体列表，用逗号分隔 (默认: 空)'
    )
    
    parser.add_argument(
        '--custom-relations',
        type=str,
        default='',
        help='自定义关系列表，格式: entity1-entity2:relation_type，用分号分隔 (默认: 空)'
    )
    
    args = parser.parse_args()
    
    # 验证数据目录
    if not os.path.exists(args.data_dir):
        logger.error(f"数据目录不存在: {args.data_dir}")
        sys.exit(1)
    
    # 验证txt目录
    txt_dir = os.path.join(args.data_dir, 'txt')
    if not os.path.exists(txt_dir):
        logger.error(f"文本目录不存在: {txt_dir}")
        logger.info("请在data/txt/目录下放置.txt文件")
        sys.exit(1)
    
    try:
        # 导入KG构建器
        from xmodaler.kg import KGBuilder
        
        logger.info("初始化知识图谱构建器...")
        
        # 创建构建器
        builder = KGBuilder(
            neo4j_uri=args.neo4j_uri,
            user=args.neo4j_user,
            password=args.neo4j_password,
            language=args.language
        )
        
        logger.info(f"数据目录: {args.data_dir}")
        logger.info(f"输出目录: {args.output_dir}")
        logger.info(f"处理图像: {not args.skip_images}")
        logger.info(f"处理视频: {not args.skip_videos}")
        logger.info(f"语言: {args.language}")
        
        computer_entities = args.computer_entities.split(',') if args.computer_entities else []
        ideology_entities = args.ideology_entities.split(',') if args.ideology_entities else []
        custom_relations = []
        if args.custom_relations:
            for rel in args.custom_relations.split(';'):
                if ':' in rel:
                    entities, rel_type = rel.split(':', 1)
                    if '-' in entities:
                        entity1, entity2 = entities.split('-', 1)
                        custom_relations.append((entity1.strip(), entity2.strip(), rel_type.strip()))
        
        # 构建知识图谱
        builder.build_kg(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            computer_entities=computer_entities,
            ideology_entities=ideology_entities,
            custom_relations=custom_relations
        )
        
        # 关闭连接
        builder.close()
        
        logger.info("✓ 知识图谱构建完成!")
        logger.info(f"✓ 结果已保存到: {args.output_dir}")
        logger.info("")
        logger.info("后续步骤:")
        logger.info("1. 检查kg_output/目录下的JSON文件")
        logger.info("2. 运行 'python app.py' 启动Web服务")
        logger.info("3. 访问 http://localhost:5000 查询知识图谱")
        
        return 0
    
    except ImportError as e:
        logger.error(f"导入错误: {str(e)}")
        logger.error("请确保已安装所有依赖: pip install -r requirements.txt")
        return 1
    
    except Exception as e:
        logger.error(f"构建失败: {str(e)}")
        logger.error("请检查:")
        logger.error("  1. Neo4j数据库是否正在运行")
        logger.error("  2. 数据目录结构是否正确")
        logger.error("  3. 数据文件是否完整")
        return 1


if __name__ == '__main__':
    sys.exit(main())

