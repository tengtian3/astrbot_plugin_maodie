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
from typing import List

@register("astrbot_plugin_maodie", "腾天", "耄耋来咯表情包插件", "1.0.0")
class MaodiePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 创建表情包文件夹（在插件目录内）
        plugin_dir = Path(__file__).parent
        self.images_dir = plugin_dir / "maodie_images"
        self.images_dir.mkdir(exist_ok=True)
        
        logger.info(f"表情包目录: {self.images_dir}")
        
        # 初始化默认表情包（如果文件夹为空）
        self._init_default_images()

    def _init_default_images(self):
        """初始化默认表情包"""
        if not any(self.images_dir.iterdir()):
            logger.info("表情包目录为空，将使用内置默认图片")
            # 这里可以添加一些默认图片的URL供用户下载
            # 实际部署时可以提供一些默认表情包

    def get_random_image_path(self) -> str:
        """随机获取一张表情包图片路径"""
        try:
            # 获取所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = [
                f for f in self.images_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            if not image_files:
                logger.warning("表情包目录中没有图片文件")
                return None
                
            # 随机选择一张图片
            selected_image = random.choice(image_files)
            logger.info(f"随机选择图片: {selected_image.name}")
            return str(selected_image)
            
        except Exception as e:
            logger.error(f"获取随机图片失败: {e}")
            return None

    async def download_image(self, url: str) -> str:
        """下载网络图片到表情包目录"""
        try:
            # 生成唯一文件名
            file_extension = Path(url).suffix
            if not file_extension:
                file_extension = '.jpg'
                
            filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = self.images_dir / filename
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            f.write(await response.read())
                        logger.info(f"图片下载成功: {filename}")
                        return str(file_path)
                    else:
                        logger.error(f"下载失败，HTTP状态码: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return None

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_maodie_trigger(self, event: AstrMessageEvent):
        """监听'哈个气'触发词"""
        try:
            message_text = event.message_str.strip()
            
            # 检查是否包含"哈个气"（忽略大小写和前后空格）
            if "哈个气" in message_text:
                logger.info(f"用户 {event.get_sender_name()} 触发了耄耋来咯")
                
                # 获取随机表情包
                image_path = self.get_random_image_path()
                
                if image_path:
                    # 构建消息链：文本 + 图片
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
        """添加表情包到收藏"""
        try:
            # 检查消息中是否有图片
            image_url = None
            for msg_seg in event.message_obj.message:
                if hasattr(msg_seg, 'type') and msg_seg.type == 'image':
                    image_url = msg_seg.data.get('url')
                    break
            
            if not image_url:
                yield event.plain_result("请发送包含图片的消息来添加表情包")
                return
            
            # 下载图片
            saved_path = await self.download_image(image_url)
            
            if saved_path:
                yield event.plain_result("表情包添加成功！🎉")
            else:
                yield event.plain_result("表情包添加失败，请重试")
                
        except Exception as e:
            logger.error(f"添加表情包失败: {e}")
            yield event.plain_result("添加表情包时发生错误")

    @filter.command("表情包列表")
    async def list_stickers(self, event: AstrMessageEvent):
        """显示表情包列表"""
        try:
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = [
                f for f in self.images_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            if not image_files:
                yield event.plain_result("暂无表情包，使用『添加表情包』命令来添加吧！")
                return
            
            # 统计信息
            total_count = len(image_files)
            file_sizes = [f.stat().st_size for f in image_files]
            total_size = sum(file_sizes) / (1024 * 1024)  # 转换为MB
            
            # 构建回复消息
            result = f"📦 表情包统计:\n"
            result += f"📊 总数: {total_count} 张\n"
            result += f"💾 占用空间: {total_size:.2f} MB\n"
            result += f"📁 存储路径: {self.images_dir}\n\n"
            result += "最近添加的5张表情包:\n"
            
            # 按修改时间排序，显示最新的5个
            recent_files = sorted(image_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            for i, file in enumerate(recent_files, 1):
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
            # 统计清理前的文件数量
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = [
                f for f in self.images_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            if not image_files:
                yield event.plain_result("没有表情包可清理")
                return
            
            # 删除所有图片文件
            deleted_count = 0
            for file_path in image_files:
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