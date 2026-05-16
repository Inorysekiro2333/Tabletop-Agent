"""
Redis Session Store — 持久化会话状态，断开后仍可恢复

如果 Redis 不可用，优雅降级为仅内存模式。
"""
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 延迟初始化，避免未安装 redis 包时导入失败
_redis_client = None
_redis_available = False


def _get_redis():
    """获取 Redis 客户端（惰性初始化）"""
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client

    try:
        from config import get_settings
        import redis.asyncio as aioredis

        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        _redis_available = True
        logger.info(f"Redis 已连接: {settings.redis_url}")
    except ImportError:
        logger.warning("redis 包未安装，会话缓存功能不可用")
        _redis_available = False
    except Exception as e:
        logger.warning(f"Redis 连接失败 ({e})，降级为仅内存模式")
        _redis_available = False

    return _redis_client


class SessionStore:
    """Redis 会话持久化存储"""

    KEY_PREFIX = "session"

    @staticmethod
    def _make_key(campaign_id: int) -> str:
        return f"{SessionStore.KEY_PREFIX}:{campaign_id}"

    @classmethod
    async def save_session(cls, campaign_id: int, session_data: dict, ttl: int = 86400):
        """保存会话到 Redis"""
        redis = _get_redis()
        if not _redis_available or redis is None:
            return

        try:
            key = cls._make_key(campaign_id)
            data_json = json.dumps(session_data, ensure_ascii=False, default=str)
            await redis.setex(key, ttl, data_json)
            logger.debug(f"会话已保存: campaign_id={campaign_id}, ttl={ttl}s")
        except Exception as e:
            logger.error(f"保存会话失败: {e}")

    @classmethod
    async def load_session(cls, campaign_id: int) -> Optional[dict]:
        """从 Redis 加载会话"""
        redis = _get_redis()
        if not _redis_available or redis is None:
            return None

        try:
            key = cls._make_key(campaign_id)
            data_json = await redis.get(key)
            if data_json:
                logger.debug(f"会话已恢复: campaign_id={campaign_id}")
                return json.loads(data_json)
            return None
        except Exception as e:
            logger.error(f"加载会话失败: {e}")
            return None

    @classmethod
    async def delete_session(cls, campaign_id: int):
        """删除 Redis 会话"""
        redis = _get_redis()
        if not _redis_available or redis is None:
            return

        try:
            key = cls._make_key(campaign_id)
            await redis.delete(key)
            logger.debug(f"会话已删除: campaign_id={campaign_id}")
        except Exception as e:
            logger.error(f"删除会话失败: {e}")

    @classmethod
    async def session_exists(cls, campaign_id: int) -> bool:
        """检查会话是否存在"""
        redis = _get_redis()
        if not _redis_available or redis is None:
            return False

        try:
            key = cls._make_key(campaign_id)
            return await redis.exists(key) > 0
        except Exception:
            return False

    @classmethod
    def is_available(cls) -> bool:
        """检查 Redis 是否可用"""
        _get_redis()
        return _redis_available
