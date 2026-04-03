#!/usr/bin/env python3
"""
多模态数据处理器模块
处理文本、图像、视频数据的特征提取和描述生成
"""

import os
import json
import cv2
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextProcessor:
    """文本数据处理器"""
    
    def __init__(self, nlp_model=None):
        """
        初始化文本处理器
        
        Args:
            nlp_model: spaCy模型对象
        """
        self.nlp = nlp_model
        self.entity_types = {
            'PERSON': '人物',
            'ORG': '组织',
            'GPE': '地点',
            'PRODUCT': '产品',
            'EVENT': '事件',
            'LAW': '法律',
            'LANGUAGE': '语言',
            'WORK_OF_ART': '艺术作品'
        }
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        从文本提取命名实体
        
        Args:
            text: 输入文本
            
        Returns:
            按类型分类的实体字典
        """
        if not self.nlp:
            return {}
        
        doc = self.nlp(text)
        entities = {}
        
        for ent in doc.ents:
            ent_type = self.entity_types.get(ent.label_, ent.label_)
            if ent_type not in entities:
                entities[ent_type] = []
            entities[ent_type].append(ent.text)
        
        return entities
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        从文本提取关键词（基于TF-IDF）
        
        Args:
            text: 输入文本
            top_k: 返回前k个关键词
            
        Returns:
            关键词列表
        """
        from collections import Counter
        
        # 简单实现：词频统计
        if not self.nlp:
            words = text.lower().split()
        else:
            doc = self.nlp(text)
            words = [token.text.lower() for token in doc if not token.is_stop]
        
        word_freq = Counter(words)
        keywords = [word for word, _ in word_freq.most_common(top_k)]
        
        return keywords
    
    def load_txt_files(self, txt_dir: str) -> Dict[str, Dict[str, any]]:
        """
        批量加载txt文件
        
        Args:
            txt_dir: txt文件目录
            
        Returns:
            文件内容字典 {filename: {entities, keywords, raw_text}}
        """
        result = {}
        
        if not os.path.exists(txt_dir):
            logger.warning(f"目录不存在: {txt_dir}")
            return result
        
        for filename in os.listdir(txt_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(txt_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    result[filename] = {
                        'raw_text': text,
                        'entities': self.extract_entities(text),
                        'keywords': self.extract_keywords(text),
                        'length': len(text)
                    }
                    logger.info(f"已加载: {filename}")
                except Exception as e:
                    logger.error(f"加载失败 {filename}: {str(e)}")
        
        return result


class ImageProcessor:
    """图像数据处理器"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化图像处理器
        
        Args:
            model_path: 预训练模型路径
        """
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载预训练模型"""
        try:
            # 尝试加载ResNet152用于特征提取
            import torch
            import torchvision.models as models
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = models.resnet152(pretrained=True).to(device)
            self.model.eval()
            self.device = device
            logger.info("已加载ResNet152模型")
        except Exception as e:
            logger.warning(f"无法加载预训练模型: {str(e)}")
            self.model = None
    
    def extract_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        从图像提取特征向量
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            特征向量
        """
        if not self.model:
            return None
        
        try:
            from PIL import Image
            import torch
            import torchvision.transforms as transforms
            
            # 加载并预处理图像
            image = Image.open(image_path).convert('RGB')
            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            input_tensor = preprocess(image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            # 提取特征
            with torch.no_grad():
                features = self.model(input_batch)
            
            return features.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"特征提取失败 {image_path}: {str(e)}")
            return None
    
    def get_image_metadata(self, image_path: str) -> Dict[str, any]:
        """
        获取图像元数据
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            元数据字典
        """
        try:
            from PIL import Image
            
            image = Image.open(image_path)
            metadata = {
                'size': image.size,
                'mode': image.mode,
                'format': image.format,
                'path': image_path,
                'filename': os.path.basename(image_path)
            }
            
            return metadata
        except Exception as e:
            logger.error(f"获取元数据失败: {str(e)}")
            return {}
    
    def load_images(self, img_dir: str) -> Dict[str, Dict[str, any]]:
        """
        批量加载图像
        
        Args:
            img_dir: 图像目录
            
        Returns:
            图像数据字典 {filename: {metadata, features}}
        """
        result = {}
        
        if not os.path.exists(img_dir):
            logger.warning(f"目录不存在: {img_dir}")
            return result
        
        for root, dirs, files in os.walk(img_dir):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    filepath = os.path.join(root, filename)
                    try:
                        category = os.path.basename(root)
                        result[filename] = {
                            'path': filepath,
                            'category': category,
                            'metadata': self.get_image_metadata(filepath),
                            'features': self.extract_features(filepath)
                        }
                        logger.info(f"已加载图像: {filename}")
                    except Exception as e:
                        logger.error(f"加载失败 {filename}: {str(e)}")
        
        return result


class VideoProcessor:
    """视频数据处理器"""
    
    def __init__(self, frames_per_video: int = 8):
        """
        初始化视频处理器
        
        Args:
            frames_per_video: 每个视频采样帧数
        """
        self.frames_per_video = frames_per_video
        self.image_processor = ImageProcessor()
    
    def extract_frames(self, video_path: str) -> List[np.ndarray]:
        """
        从视频均匀采样帧
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            帧列表
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"无法打开视频: {video_path}")
                return []
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                return []
            
            frame_indices = np.linspace(0, total_frames - 1, 
                                       self.frames_per_video, dtype=int)
            
            frames = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
            
            cap.release()
            return frames
        except Exception as e:
            logger.error(f"帧提取失败: {str(e)}")
            return []
    
    def extract_video_features(self, video_path: str) -> Optional[List[np.ndarray]]:
        """
        从视频帧提取特征
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            特征列表
        """
        frames = self.extract_frames(video_path)
        if not frames:
            return None
        
        features = []
        for frame in frames:
            # 临时保存帧为图像
            temp_path = '/tmp/temp_frame.jpg'
            cv2.imwrite(temp_path, frame)
            
            feature = self.image_processor.extract_features(temp_path)
            if feature is not None:
                features.append(feature)
            
            os.remove(temp_path)
        
        return features if features else None
    
    def get_video_metadata(self, video_path: str) -> Dict[str, any]:
        """
        获取视频元数据
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            元数据字典
        """
        try:
            cap = cv2.VideoCapture(video_path)
            metadata = {
                'path': video_path,
                'filename': os.path.basename(video_path),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            }
            
            cap.release()
            return metadata
        except Exception as e:
            logger.error(f"获取元数据失败: {str(e)}")
            return {}
    
    def load_videos(self, video_dir: str) -> Dict[str, Dict[str, any]]:
        """
        批量加载视频
        
        Args:
            video_dir: 视频目录
            
        Returns:
            视频数据字典
        """
        result = {}
        
        if not os.path.exists(video_dir):
            logger.warning(f"目录不存在: {video_dir}")
            return result
        
        for filename in os.listdir(video_dir):
            if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                filepath = os.path.join(video_dir, filename)
                try:
                    result[filename] = {
                        'path': filepath,
                        'metadata': self.get_video_metadata(filepath),
                        'features': self.extract_video_features(filepath)
                    }
                    logger.info(f"已加载视频: {filename}")
                except Exception as e:
                    logger.error(f"加载失败 {filename}: {str(e)}")
        
        return result


class CaptionGenerator:
    """图像和视频描述生成器"""
    
    def __init__(self, model_name: str = "blip-image-captioning-base"):
        """
        初始化描述生成器
        
        Args:
            model_name: HuggingFace模型名称
        """
        self.model_name = model_name
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """加载预训练的图像描述模型"""
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.processor = BlipProcessor.from_pretrained(self.model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(
                self.model_name
            ).to(device)
            self.device = device
            logger.info(f"已加载模型: {self.model_name}")
        except Exception as e:
            logger.warning(f"无法加载图像描述模型: {str(e)}")
    
    def generate_image_caption(self, image_path: str) -> Optional[str]:
        """
        为图像生成描述
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            图像描述
        """
        if not self.model or not self.processor:
            return None
        
        try:
            from PIL import Image
            import torch
            
            image = Image.open(image_path).convert('RGB')
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                out = self.model.generate(**inputs, max_length=50)
            
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            return caption
        except Exception as e:
            logger.error(f"描述生成失败 {image_path}: {str(e)}")
            return None
    
    def generate_video_caption(self, video_path: str) -> Optional[str]:
        """
        为视频生成描述（基于关键帧）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频描述
        """
        try:
            video_processor = VideoProcessor()
            frames = video_processor.extract_frames(video_path)
            
            if not frames:
                return None
            
            # 对中间帧生成描述
            middle_frame_idx = len(frames) // 2
            temp_path = '/tmp/temp_frame.jpg'
            cv2.imwrite(temp_path, frames[middle_frame_idx])
            
            caption = self.generate_image_caption(temp_path)
            os.remove(temp_path)
            
            return caption
        except Exception as e:
            logger.error(f"视频描述生成失败: {str(e)}")
            return None


class VideoEditor:
    """视频编辑器"""
    
    def __init__(self):
        """初始化视频编辑器"""
        pass
    
    def clip_video(self, input_path: str, output_path: str, start_time: float = 0, duration: float = 60):
        """
        剪辑视频片段
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
        """
        try:
            import subprocess
            
            # 使用ffmpeg剪辑视频
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"视频剪辑成功: {output_path}")
                return True
            else:
                logger.error(f"视频剪辑失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"视频剪辑异常: {str(e)}")
            return False
    
    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长
        
        Args:
            video_path: 视频路径
            
        Returns:
            时长（秒）
        """
        try:
            import subprocess
            import json
            
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                return duration
            else:
                logger.error(f"获取视频时长失败: {result.stderr}")
                return 0
        except Exception as e:
            logger.error(f"获取视频时长异常: {str(e)}")
            return 0

