from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import os
import random
import shutil
from pathlib import Path
import aiohttp
import uuid
from typing import List, Optional

@register("astrbot_plugin_maodie", "腾天", "耄耋来咯表情包插件", "1.1.0")
class MaodiePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 创建表情包文件夹
        plugin_dir = Path(__file__).parent
        self.images_dir = plugin_dir / "maodie_images"
        self.images_dir.mkdir(exist_ok=True)
        
        logger.info(f"表情包插件初始化完成，目录: {self.images_dir}")

    async def get_replied_message_images(self, event: AstrMessageEvent) -> List[str]:
        """专门处理回复消息中的图片获取 - 改进版本"""
        images = []
        
        try:
            # 获取回复消息的ID和图片信息
            for msg_seg in event.message_obj.message:
                logger.info(f"检查消息段: {type(msg_seg)} - {msg_seg}")
                
                # 检查是否是回复组件
                if hasattr(msg_seg, 'type') and getattr(msg_seg, 'type', None) == Comp.ComponentType.Reply:
                    reply_id = getattr(msg_seg, 'id', None)
                    logger.info(f"从消息对象找到回复ID: {reply_id}")
                    
                    # 关键改进：直接从回复组件的chain中提取图片
                    chain = getattr(msg_seg, 'chain', [])
                    logger.info(f"回复组件包含chain: {chain}")
                    
                    for chain_item in chain:
                        logger.info(f"检查chain_item: {type(chain_item)} - {chain_item}")
                        
                        # 检查是否是图片组件
                        if hasattr(chain_item, 'type') and getattr(chain_item, 'type', None) == Comp.ComponentType.Image:
                            image_url = getattr(chain_item, 'url', None)
                            logger.info(f"找到图片URL: {image_url}")
                            
                            if image_url:
                                images.append(image_url)
                                logger.info(f"成功提取图片URL: {image_url}")
                    
                    break
            
            logger.info(f"从回复消息中总共找到 {len(images)} 张图片")
            return images
            
        except Exception as e:
            logger.error(f"获取回复消息图片失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def download_image(self, url: str) -> Optional[str]:
        """下载单张图片"""
        try:
            # 生成唯一文件名
            file_extension = '.jpg'
            if '?' in url:
                url_without_params = url.split('?')[0]
                file_extension = Path(url_without_params).suffix or '.jpg'
            else:
                file_extension = Path(url).suffix or '.jpg'
                
            filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = self.images_dir / filename
            
            logger.info(f"开始下载图片: {url}")
            
            async with aiohttp.ClientSession() as session:
                # 特殊处理腾讯多媒体域名
                if "multimedia.nt.qq.com.cn" in url:
                    insecure_url = url.replace("https://", "http://", 1)
                    logger.warning(f"检测到腾讯多媒体域名，使用 HTTP 协议下载: {insecure_url}")
                    async with session.get(insecure_url) as response:
                        if response.status == 200:
                            content = await response.read()
                        else:
                            logger.error(f"下载失败，HTTP状态码: {response.status}")
                            return None
                else:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                        else:
                            logger.error(f"下载失败，HTTP状态码: {response.status}")
                            return None
                
                logger.info(f"下载成功，文件大小: {len(content)} bytes")
                
                if len(content) > 50 * 1024 * 1024:  # 50MB限制
                    logger.warning(f"图片过大，跳过下载: {len(content)} bytes")
                    return None
                    
                with open(file_path, 'wb') as f:
                    f.write(content)
                logger.info(f"图片保存成功: {filename}")
                return str(file_path)
                        
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_random_image_path(self) -> Optional[str]:
        """随机获取一张表情包图片路径"""
        try:
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = [
                f for f in self.images_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            if not image_files:
                return None
                
            selected_image = random.choice(image_files)
            logger.info(f"随机选择图片: {selected_image.name}")
            return str(selected_image)
            
        except Exception as e:
            logger.error(f"获取随机图片失败: {e}")
            return None

    def get_image_stats(self) -> dict:
        """获取图片统计信息"""
        try:
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = [
                f for f in self.images_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            total_count = len(image_files)
            total_size = sum(f.stat().st_size for f in image_files) / (1024 * 1024)  # MB
            
            return {
                'total_count': total_count,
                'total_size': total_size,
                'recent_files': sorted(image_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            }
            
        except Exception as e:
            logger.error(f"获取图片统计失败: {e}")
            return {'total_count': 0, 'total_size': 0, 'recent_files': []}

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_maodie_trigger(self, event: AstrMessageEvent):
        """监听'哈个气'触发词"""
        try:
            message_text = event.message_str.strip()
            
            if "哈个气" in message_text:
                logger.info(f"用户 {event.get_sender_name()} 触发了耄耋来咯")
                
                image_path = self.get_random_image_path()
                
                if image_path:
                    chain = [
                        Comp.Plain("耄耋来咯～"),
                        Comp.Image.fromFileSystem(image_path)
                    ]
                    yield event.chain_result(chain)
                else:
                    yield event.plain_result("耄耋来咯～（暂无表情包可用）")
                    
        except Exception as e:
            logger.error(f"处理哈个气触发失败: {e}")

    @filter.command("添加表情包")
    async def add_sticker(self, event: AstrMessageEvent):
        """添加表情包到收藏 - 专门处理引用图片的情况"""
        try:
            # 专门处理回复消息中的图片
            image_urls = await self.get_replied_message_images(event)
            
            if not image_urls:
                # 也检查当前消息中是否有图片（直接发送图片的情况）
                current_images = []
                for msg_seg in event.message_obj.message:
                    logger.info(f"检查当前消息段: {type(msg_seg)} - {msg_seg}")
                    # 检查是否是图片组件
                    if hasattr(msg_seg, 'type') and getattr(msg_seg, 'type', None) == Comp.ComponentType.Image:
                        image_url = getattr(msg_seg, 'url', None)
                        if image_url:
                            current_images.append(image_url)
                            logger.info(f"从当前消息找到图片: {image_url}")
                
                if not current_images:
                    yield event.plain_result("请引用包含图片的消息来添加表情包")
                    return
                else:
                    image_urls = current_images
            
            # 下载图片
            saved_paths = []
            for image_url in image_urls:
                saved_path = await self.download_image(image_url)
                if saved_path:
                    saved_paths.append(saved_path)
            
            if saved_paths:
                yield event.plain_result(f"表情包添加成功！🎉 共添加了 {len(saved_paths)} 张图片")
            else:
                yield event.plain_result("表情包添加失败，请重试")
                
        except Exception as e:
            logger.error(f"添加表情包失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            yield event.plain_result("添加表情包时发生错误")

    @filter.command("表情包列表")
    async def list_stickers(self, event: AstrMessageEvent):
        """显示表情包列表"""
        try:
            stats = self.get_image_stats()
            
            if stats['total_count'] == 0:
                yield event.plain_result("暂无表情包，使用『添加表情包』命令来添加吧！")
                return
            
            # 构建回复消息
            result = f"📦 表情包统计:\n"
            result += f"📊 总数: {stats['total_count']} 张\n"
            result += f"💾 占用空间: {stats['total_size']:.2f} MB\n\n"
            result += "最近添加的5张表情包:\n"
            
            for i, file in enumerate(stats['recent_files'], 1):
                file_size_kb = file.stat().st_size / 1024
                result += f"{i}. {file.name} ({file_size_kb:.1f} KB)\n"
            
            yield event.plain_result(result)
            
        except Exception as e:
            logger.error(f"获取表情包列表失败: {e}")
            yield event.plain_result("获取表情包列表时发生错误")

    @filter.command("清理表情包")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def clear_stickers(self, event: AstrMessageEvent):
        """清理所有表情包（仅管理员）"""
        try:
            stats = self.get_image_stats()
            
            if stats['total_count'] == 0:
                yield event.plain_result("没有表情包可清理")
                return
            
            # 删除所有图片文件
            deleted_count = 0
            for file_path in self.images_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"删除文件失败 {file_path}: {e}")
            
            logger.info(f"清理了 {deleted_count} 个表情包文件")
            yield event.plain_result(f"已清理 {deleted_count} 个表情包文件")
            
        except Exception as e:
            logger.error(f"清理表情包失败: {e}")
            yield event.plain_result("清理表情包时发生错误")

    @filter.command("随机表情包")
    async def random_sticker(self, event: AstrMessageEvent):
        """手动发送随机表情包"""
        try:
            image_path = self.get_random_image_path()
            
            if image_path:
                chain = [
                    Comp.Plain("随机表情包来咯～"),
                    Comp.Image.fromFileSystem(image_path)
                ]
                yield event.chain_result(chain)
            else:
                yield event.plain_result("暂无表情包可用，使用『添加表情包』命令来添加吧！")
                
        except Exception as e:
            logger.error(f"发送随机表情包失败: {e}")
            yield event.plain_result("发送表情包时发生错误")

    async def terminate(self):
        """插件被卸载时调用"""
        logger.info("耄耋来咯插件已卸载")