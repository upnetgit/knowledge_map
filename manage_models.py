#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型下载脚本 - 用于下载 xmodaler 所需的预训练模型
在 Ubuntu 20.04 上运行

使用示例:
    python download_models.py --model tden_cross_entropy  # 下载单个模型
    python download_models.py --category image_caption    # 下载一个类别的模型
    python download_models.py --all                       # 下载所有模型（不推荐）
"""

import os
import argparse
import sys
from pathlib import Path

# 模型配置：{模型ID: (名称, 任务, Google Drive ID, 输出路径)}
MODELS = {
    # 必需的基础模型
    'resnet152': {
        'name': 'ResNet-152',
        'category': 'Feature Extractor',
        'drive_id': None,  # 需要手动下载或从 torchvision 获取
        'local_path': 'pretrained_models/resnet152-394f9c45.pth',
        'status': '✅ 已有'
    },

    # 图像字幕 - Cross-Entropy Loss (需要下载)
    'ic_ce_lstm': {
        'name': 'LSTM-A3',
        'category': 'Image Captioning (Cross-Entropy)',
        'drive_id': '13fJVIK7ZgQnNMWzIbFicETDx6AgLg0NH',
        'local_path': 'pretrained_models/image_caption_lstm_a3_ce.pth',
        'status': '❌ 需要下载'
    },
    'ic_ce_attention': {
        'name': 'Attention',
        'category': 'Image Captioning (Cross-Entropy)',
        'drive_id': '1aw8lPcDlf8C8UPsphwqbMAsq5-YSHIEf',
        'local_path': 'pretrained_models/image_caption_attention_ce.pth',
        'status': '❌ 需要下载'
    },
    'ic_ce_updown': {
        'name': 'Up-Down',
        'category': 'Image Captioning (Cross-Entropy)',
        'drive_id': '1giOJ5llaNjXz2JClN3Mqe93VIy1Fu5pq',
        'local_path': 'pretrained_models/image_caption_updown_ce.pth',
        'status': '❌ 需要下载'
    },
    'ic_ce_tden': {
        'name': 'TDEN',
        'category': 'Image Captioning (Cross-Entropy)',
        'drive_id': '19alfPj-gIudoL5CHsS4VwhfnU-FhTXW3',
        'local_path': 'pretrained_models/image_caption_tden_ce.pth',
        'status': '❌ 需要下载'
    },

    # 图像字幕 - CIDEr Optimization (部分已有)
    'ic_cider_attention': {
        'name': 'Attention',
        'category': 'Image Captioning (CIDEr Optimization)',
        'drive_id': '1m04qezTUJpdkBI3oIo_5Y9fIZG7_jZ2S',
        'local_path': 'configs/pretrain/Cross-Entropy Loss_Attention.pth',
        'status': '✅ 已有'
    },
    'ic_cider_tden': {
        'name': 'TDEN',
        'category': 'Image Captioning (CIDEr Optimization)',
        'drive_id': '1GTbbwfbJHIu6uDmcLY-pedCiuWHyR7nK',
        'local_path': 'configs/pretrain/CIDEr Score Optimization_TDEN.pth',
        'status': '✅ 已有'
    },

    # 视频字幕 - MSVD (部分已有)
    'vc_msvd_ta': {
        'name': 'TA',
        'category': 'Video Captioning (MSVD)',
        'drive_id': '1SqvugATqHU3Le1jtTQKnL3FADJ7kbJK0',
        'local_path': 'configs/pretrain/Video Captioning on MSVD_TA.pth',
        'status': '✅ 已有'
    },
    'vc_msvd_tdconved': {
        'name': 'TDConvED',
        'category': 'Video Captioning (MSVD)',
        'drive_id': '1Th9FJe8o_4bMULuoCKqDHP_4Faa0RabZ',
        'local_path': 'pretrained_models/video_caption_tdconved_msvd.pth',
        'status': '❌ 需要下载'
    },

    # 视频字幕 - MSR-VTT (部分已有)
    'vc_msrvtt_tdconved': {
        'name': 'TDConvED',
        'category': 'Video Captioning (MSR-VTT)',
        'drive_id': '1A3OGvjCpXUI6p1vy1qbNTVGLy5a0b3Dc',
        'local_path': 'pretrained_models/MSR-VTT_TDConvED.pth',
        'status': '✅ 已有'
    },

    # 视觉问答 (需要下载)
    'vqa_uniter': {
        'name': 'Uniter',
        'category': 'Visual Question Answering',
        'drive_id': '1cjBAeYSuSEN_IlQCnqtIoalkATMSQs87',
        'local_path': 'pretrained_models/vqa_uniter.pth',
        'status': '❌ 需要下载'
    },
    'vqa_tden': {
        'name': 'TDEN',
        'category': 'Visual Question Answering',
        'drive_id': '1hwcDUboyCXghETamS_APJL8eGKY9OgFD',
        'local_path': 'pretrained_models/vqa_tden.pth',
        'status': '❌ 需要下载'
    },

    # 基于字幕的图像检索 (部分已有)
    'ret_tden': {
        'name': 'TDEN',
        'category': 'Caption-based Image Retrieval',
        'drive_id': '1SqYscN6UCbifxhMJ-ScpiLgWepMSx7uq',
        'local_path': 'configs/pretrain/Caption-based image retrieval on Flickr30k_TDEN.pth',
        'status': '✅ 已有'
    },
    'ret_uniter': {
        'name': 'Uniter',
        'category': 'Caption-based Image Retrieval',
        'drive_id': '1hvoWMmHjSvxp3zqW10L7PoBQGbxM9MiF',
        'local_path': 'pretrained_models/retrieval_uniter.pth',
        'status': '❌ 需要下载'
    },

    # 视觉常识推理 (部分已有)
    'vcr_tden': {
        'name': 'TDEN',
        'category': 'Visual Commonsense Reasoning',
        'drive_id': '1WZfvo_PyHQwdO-DU_GRWWjbKSzwfyBFO',
        'local_path': 'configs/pretrain/Visual commonsense reasoning_TDEN.pth',
        'status': '✅ 已有'
    },
    'vcr_uniter': {
        'name': 'Uniter',
        'category': 'Visual Commonsense Reasoning',
        'drive_id': '1Edx9uorwDgI5nZRf9M3XJDRIIoRa5TmP',
        'local_path': 'pretrained_models/vcr_uniter.pth',
        'status': '❌ 需要下载'
    },
}

def print_model_status():
    """打印所有模型状态"""
    print("\n" + "="*80)
    print("模型清单 - X-Modaler 预训练权重")
    print("="*80)

    categories = {}
    for model_id, info in MODELS.items():
        category = info['category']
        if category not in categories:
            categories[category] = []
        categories[category].append((model_id, info))

    for category in sorted(categories.keys()):
        print(f"\n【{category}】")
        print("-" * 80)
        for model_id, info in categories[category]:
            status_symbol = "✅" if "已有" in info['status'] else "❌"
            print(f"  {status_symbol} {info['name']:20s} | {info['status']:15s}")
            if info['drive_id']:
                print(f"     Drive ID: {info['drive_id']}")
            print(f"     保存路径: {info['local_path']}")

    print("\n" + "="*80)
    print("统计信息")
    print("="*80)
    available = sum(1 for info in MODELS.values() if "已有" in info['status'])
    need_download = sum(1 for info in MODELS.values() if "需要下载" in info['status'])
    print(f"✅ 已有模型: {available} 个")
    print(f"❌ 需要下载: {need_download} 个")
    print(f"📊 总计: {len(MODELS)} 个")
    print("="*80 + "\n")

def get_categories():
    """获取所有模型类别"""
    categories = set()
    for info in MODELS.values():
        categories.add(info['category'])
    return sorted(categories)

def list_models_by_category(category):
    """列出指定类别的所有模型"""
    print(f"\n【{category}】模型列表:")
    print("-" * 60)
    for model_id, info in MODELS.items():
        if info['category'] == category:
            status = "✅ 已有" if "已有" in info['status'] else "❌ 需要下载"
            print(f"  {model_id:20s} - {info['name']:20s} [{status}]")
    print("-" * 60 + "\n")

def download_model(model_id):
    """下载单个模型（需要 gdown）"""
    if model_id not in MODELS:
        print(f"❌ 模型 '{model_id}' 不存在")
        return False

    info = MODELS[model_id]

    if "已有" in info['status']:
        print(f"✅ 模型 '{info['name']}' 已在本地")
        return True

    if not info['drive_id']:
        print(f"⚠️  模型 '{info['name']}' 无下载链接（需要手动下载）")
        return False

    print(f"\n开始下载: {info['name']}")
    print(f"Google Drive ID: {info['drive_id']}")
    print(f"保存路径: {info['local_path']}")
    print("\n⚠️  需要 gdown 工具。安装: pip install gdown")
    print(f"命令: gdown {info['drive_id']} -O {info['local_path']}")
    print("\n本脚本目前仅显示下载信息，请手动运行上述命令\n")

    return True

def main():
    parser = argparse.ArgumentParser(description='X-Modaler 模型下载管理工具')
    parser.add_argument('--status', action='store_true', help='显示所有模型状态')
    parser.add_argument('--list-categories', action='store_true', help='列出所有模型类别')
    parser.add_argument('--category', type=str, help='列出指定类别的模型')
    parser.add_argument('--model', type=str, help='下载指定模型')
    parser.add_argument('--all', action='store_true', help='列出所有需要下载的模型')

    args = parser.parse_args()

    if not any(vars(args).values()):
        args.status = True  # 默认显示状态

    if args.status:
        print_model_status()

    if args.list_categories:
        print("可用的模型类别:")
        for category in get_categories():
            print(f"  - {category}")
        print()

    if args.category:
        if args.category in get_categories():
            list_models_by_category(args.category)
        else:
            print(f"❌ 类别 '{args.category}' 不存在")
            print("可用类别:")
            for category in get_categories():
                print(f"  - {category}")

    if args.model:
        download_model(args.model)

    if args.all:
        print("需要下载的模型列表:\n")
        download_needed = {k: v for k, v in MODELS.items() if "需要下载" in v['status']}
        for model_id, info in sorted(download_needed.items()):
            print(f"{model_id:25s} - {info['name']:20s} ({info['category']})")
        print(f"\n总计: {len(download_needed)} 个模型需要下载")

if __name__ == '__main__':
    main()

