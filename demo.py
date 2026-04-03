#!/usr/bin/env python3
"""
跨模态知识图谱演示脚本
展示如何构建和使用知识图谱
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("开始跨模态知识图谱演示...")

    # 示例实体
    computer_entities = [
        "编程语言", "数据结构", "算法", "操作系统", "数据库",
        "计算机网络", "软件工程", "人工智能", "机器学习", "深度学习"
    ]

    ideology_entities = [
        "马克思主义", "社会主义", "爱国主义", "集体主义", "创新精神",
        "科学精神", "人文素养", "社会责任", "职业道德", "终身学习"
    ]

    # 示例关系
    custom_relations = [
        ("编程语言", "创新精神", "related"),
        ("算法", "科学精神", "related"),
        ("人工智能", "社会责任", "related"),
        ("机器学习", "终身学习", "related"),
        ("软件工程", "职业道德", "related")
    ]

    # 构建知识图谱
    try:
        from xmodaler.kg import KGBuilder

        logger.info("初始化知识图谱构建器...")

        builder = KGBuilder(
            neo4j_uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            language="zh"
        )

        # 构建知识图谱
        builder.build_kg(
            data_dir="./data",
            output_dir="./kg_output",
            computer_entities=computer_entities,
            ideology_entities=ideology_entities,
            custom_relations=custom_relations
        )

        # 关闭连接
        builder.close()

        logger.info("✓ 知识图谱构建完成!")
        logger.info("✓ 运行 'python app.py' 启动Web界面")

    except Exception as e:
        logger.error(f"构建失败: {str(e)}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
