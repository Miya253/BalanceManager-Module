import json
import logging
import aiofiles
import asyncio
import os
from functools import wraps
import discord
from typing import Dict, Any, Optional, Callable

class BalanceManager:
    def __init__(self, file_path: Optional[str] = None):
        """初始化 BalanceManager，支援環境變量配置文件路徑"""
        self.file_path = file_path or os.getenv("BALANCE_FILE", "balance.json")
        self.lock = asyncio.Lock()
        self.backup_path = f"{self.file_path}.bak"

    async def read(self) -> Dict[str, Any]:
        """異步讀取 balance.json 文件"""
        try:
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                return json.loads(content) if content else {}
        except UnicodeDecodeError:
            logging.error(f"讀取 {self.file_path} 失敗: 文件編碼非 UTF-8")
            return {}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"讀取 {self.file_path} 失敗: {e}")
            return {}

    async def write(self, data: Dict[str, Any], actor: Optional[str] = None, reason: Optional[str] = None) -> bool:
        """異步寫入 balance.json 文件，包含備份和數據驗證"""
        if not isinstance(data, dict):
            logging.error(f"無效數據類型: 預期 dict，收到 {type(data)}")
            return False

        async with self.lock:
            try:
                # 備份當前文件
                if os.path.exists(self.file_path):
                    async with aiofiles.open(self.backup_path, 'w', encoding='utf-8') as backup:
                        async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as current:
                            await backup.write(await current.read())

                # 寫入新數據
                async with aiofiles.open(self.file_path, 'w', encoding='utf-8') as file:
                    await file.write(json.dumps(data, indent=4, ensure_ascii=False))
                log_msg = f"✅ {self.file_path} 更新成功"
                if actor or reason:
                    log_msg += f" by {actor} for {reason}"
                logging.info(log_msg)
                return True
            except Exception as e:
                logging.error(f"寫入 {self.file_path} 失敗: {e}", exc_info=True)
                # 恢復備份（可選，根據需求啟用）
                # if os.path.exists(self.backup_path):
                #     os.replace(self.backup_path, self.file_path)
                return False

    async def update(self, updater: Callable[[Dict[str, Any]], Dict[str, Any]], 
                    actor: Optional[str] = None, reason: Optional[str] = None) -> bool:
        """讀取資料，透過 updater 函數更新，再寫入，並記錄差異"""
        before = await self.read()
        after = updater(before.copy()) or before  # 防止 updater 回傳 None

        changes = self.diff(before, after)
        if changes:
            logging.info(f"🔄 {self.file_path} 改動: {changes}")
        else:
            logging.info(f"🔍 {self.file_path} 無實際變更")

        return await self.write(after, actor=actor, reason=reason)

    def diff(self, before: Dict[str, Any], after: Dict[str, Any], max_log_items: int = 5) -> Dict[str, Any]:
        """比較前後數據差異，限制日誌輸出量"""
        diff = {}
        all_keys = set(before.keys()).union(after.keys())
        for key in all_keys:
            if before.get(key) != after.get(key):
                diff[key] = {
                    "before": before.get(key),
                    "after": after.get(key)
                }
        if len(diff) > max_log_items:
            return {k: diff[k] for k in list(diff)[:max_log_items]} | {"__truncated__": f"{len(diff) - max_log_items} more changes"}
        return diff


def track_balance_command(balance_manager: BalanceManager):
    """裝飾器：自動記錄 balance.json 的前後差異與指令來源"""
    def decorator(command_func):
        @wraps(command_func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            try:
                before = await balance_manager.read()
                logging.info(f"執行指令: {command_func.__name__} 來自 {interaction.user} ({interaction.user.id})")
                result = await command_func(interaction, *args, **kwargs)
                after = await balance_manager.read()
                changes = balance_manager.diff(before, after)
                if changes:
                    logging.info(f"🔄 指令 {command_func.__name__} 導致 {balance_manager.file_path} 改動: {changes}")
                else:
                    logging.info(f"🔍 指令 {command_func.__name__} 未改變 {balance_manager.file_path}")
                return result
            except Exception as e:
                logging.error(f"執行 {command_func.__name__} 時發生錯誤: {e}", exc_info=True)
                raise e
        return wrapper
    return decorator
