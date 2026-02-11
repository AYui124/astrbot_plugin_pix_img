import asyncio
import json
import os
import random
import time
from typing import Any

import aiohttp

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

WAITING_MESSAGES = [
    "让我找找哦~",
    "111",
    "Ciallo～(∠・ω< )⌒★",
    "刚准备好，等等哦~",
    "巧了，我也想涩涩",
    "( *・ω・)✄╰ひ╯",
]


class PixImagePlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config if config is not None else {}
        self.usage_file = os.path.join(
            get_astrbot_data_path(),
            "plugins_data",
            "pix_img",
            "usage.json"
        )
        self.temp_dir = os.path.join(
            get_astrbot_data_path(),
            "plugins_data",
            "pix_img",
            "temp"
        )
        self.usage_data: dict[str, Any] = {}
        self.usage_lock = asyncio.Lock()

    async def initialize(self):
        """插件初始化：创建目录、加载使用记录"""
        # 创建临时文件目录
        os.makedirs(self.temp_dir, exist_ok=True)

        # 确保使用记录文件目录存在
        os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)

        # 加载使用记录
        await self.load_usage_data()

    async def load_usage_data(self):
        """加载用户使用记录"""
        async with self.usage_lock:
            try:
                if os.path.exists(self.usage_file):
                    with open(self.usage_file, encoding="utf-8") as f:
                        self.usage_data = json.load(f)
            except Exception as e:
                logger.error(f"加载使用记录失败: {e}")
                self.usage_data = {}

    async def _save_usage_data(self):
        """保存用户使用记录（内部方法，不获取锁）"""
        try:
            with open(self.usage_file, "w", encoding="utf-8") as f:
                json.dump(self.usage_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存使用记录失败: {e}")

    async def check_user_limit(self, user_id: str) -> tuple[bool, int]:
        """
        检查用户调用次数限制
        返回: (是否允许调用, 剩余次数)
        """
        limit_window = (
            self.config.get("limit_window", 3600)
            if self.config
            else 3600
        )
        user_limit = self.config.get("user_limit", 5) if self.config else 5
        current_time = int(time.time())

        async with self.usage_lock:
            if user_id not in self.usage_data:
                # 用户首次调用
                self.usage_data[user_id] = {
                    "timestamp": current_time,
                    "count": 0
                }
                await self._save_usage_data()
                return True, user_limit

            user_data = self.usage_data[user_id]
            window_start = current_time - limit_window

            # 检查是否在同一个时间窗口内
            if user_data["timestamp"] >= window_start:
                # 在时间窗口内
                if user_data["count"] >= user_limit:
                    # 超出限制
                    remaining = 0
                else:
                    remaining = user_limit - user_data["count"]
                return user_data["count"] < user_limit, remaining
            else:
                # 已超过时间窗口，重置计数
                self.usage_data[user_id] = {
                    "timestamp": current_time,
                    "count": 0
                }
                await self._save_usage_data()
                return True, user_limit

    async def increment_user_count(self, user_id: str):
        """增加用户调用次数"""
        async with self.usage_lock:
            if user_id in self.usage_data:
                self.usage_data[user_id]["count"] += 1
                await self._save_usage_data()

    async def call_api(self) -> dict | None:
        """调用API获取图片信息"""
        if not self.config:
            logger.error("配置未初始化")
            return None

        api_url = self.config.get("api_url", "")
        api_secret = self.config.get("api_secret", "")

        if not api_url:
            logger.error("API地址未配置")
            return None

        headers = {}
        if api_secret:
            headers["X-API-Key"] = api_secret
        logger.info("api_url=%s", api_url)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    logger.info("response code=%d", response.status)
                    if response.status == 200:
                        data = await response.json()
                        logger.info("response content=%s", data)
                        if data.get("success") and data.get("artworks"):
                            return data["artworks"][0]
                        else:
                            logger.error(f"API返回错误: {data}")
                            return None
                    else:
                        logger.error(f"API请求失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"调用API异常: {e}")
            return None

    async def download_image(self, url: str) -> str | None:
        """下载图片到临时目录"""
        try:
            # 生成唯一文件名
            import uuid
            logger.info("image url=%s", url)
            file_ext = os.path.splitext(url)[1] or ".jpg"
            filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(
                self.temp_dir, filename
            )

            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
                        logger.info(f"图片下载成功: {file_path}")
                        return file_path
                    else:
                        logger.error(f"图片下载失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None

    @filter.command("涩涩")
    async def on_pic_command(self, event: AstrMessageEvent):
        """随机发送pixiv图片命令"""
        user_id = str(event.get_sender_id())
        user_name = event.get_sender_name()

        # 检查配置
        if not self.config:
            yield event.plain_result("❌ 不许涩涩")
            logger.info("无法加载配置")
            return

        api_url = self.config.get("api_url", "")
        if not api_url:
            yield event.plain_result("❌ 禁止涩涩")
            logger.info("API地址未配置")
            return
        # 检查用户限制
        allowed, _ = await self.check_user_limit(user_id)
        if not allowed:
            yield event.plain_result(
                f"⚠️ {user_name}涩涩太多次了，请稍后再试~"
            )
            return

        waiting_msg = random.choice(WAITING_MESSAGES)
        yield event.plain_result(waiting_msg)

        # 调用API
        logger.info(f"用户 {user_name} ({user_id}) 请求随机图片")
        artwork = await self.call_api()

        if not artwork:
            yield event.plain_result("❌ 信号不好没有找到涩涩")
            return

        # 提取图片URL和作品信息
        image_url = artwork.get("url", "")
        if not image_url:
            yield event.plain_result("❌ 你怎么这么自私")
            return

        # 下载图片
        image_path = await self.download_image(image_url)
        if not image_path:
            yield event.plain_result("❌ 涩爆了")
            return

        # 构建作品信息
        title = artwork.get("title", "未知作品")
        author = artwork.get("author_name", "未知作者")
        share_url = artwork.get("share_url", "https://pixiv.net")

        info_text = (
            f"🎨 标题：{title}\n"
            f"👤 作者: {author}\n"
        )

        # 发送图片和作品信息
        try:
            # 发送图片
            message = event.make_result().file_image(image_path)
            await event.send(message)

            # 发送作品信息
            if share_url:
                info_text += f"🔗 {share_url}"
            yield event.plain_result(info_text)

            # 更新用户调用次数
            await self.increment_user_count(user_id)
            # 等待
            await asyncio.sleep(1)
            # 删除临时文件
            try:
                os.remove(image_path)
                logger.info(f"已删除临时文件: {image_path}")
            except Exception as e:
                logger.error(f"删除临时文件失败: {e}")
        except Exception as e:
            logger.error(f"发送图片失败: {e}")
            yield event.plain_result("❌ 发送图片失败")

    async def terminate(self):
        """插件卸载时的清理工作"""
        # 保存使用记录
        async with self.usage_lock:
            await self._save_usage_data()

        # 清空临时目录
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"清理临时文件: {filename}")
                logger.info("已清空临时目录")
        except Exception as e:
            logger.error(f"清空临时目录失败: {e}")

        logger.info("PixImg插件已卸载")
