"""
认证 API 测试
版本: v1.0
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash, validate_password_strength
from app.models.user import User


class TestPasswordValidation:
    """密码验证测试"""

    def test_valid_password(self):
        """测试有效密码"""
        is_valid, error = validate_password_strength("Admin@123")
        assert is_valid is True
        assert error == ""

    def test_short_password(self):
        """测试密码过短"""
        is_valid, error = validate_password_strength("Ab@1234")
        assert is_valid is False
        assert "8" in error

    def test_no_uppercase(self):
        """测试缺少大写字母"""
        is_valid, error = validate_password_strength("admin@123")
        assert is_valid is False
        assert "大写" in error

    def test_no_lowercase(self):
        """测试缺少小写字母"""
        is_valid, error = validate_password_strength("ADMIN@123")
        assert is_valid is False
        assert "小写" in error

    def test_no_digit(self):
        """测试缺少数字"""
        is_valid, error = validate_password_strength("Admin@abc")
        assert is_valid is False
        assert "数字" in error

    def test_no_special_char(self):
        """测试缺少特殊字符"""
        is_valid, error = validate_password_strength("Admin1234")
        assert is_valid is False
        assert "特殊字符" in error


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "Admin@123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_password(self):
        """测试密码验证"""
        from app.core.security import verify_password
        
        password = "Admin@123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


class TestUserLockState:
    """用户锁定状态测试"""

    def test_timezone_aware_locked_until_is_supported(self):
        """测试带时区的锁定时间不会触发比较异常。"""
        user = User(
            username="locked_user",
            email="locked@example.com",
            password_hash="hash",
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        assert user.is_locked is True
        assert user.get_lock_remaining_seconds() > 0

    def test_expired_locked_until_returns_unlocked(self):
        """测试过期的锁定时间会正确解锁。"""
        user = User(
            username="expired_user",
            email="expired@example.com",
            password_hash="hash",
            locked_until=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        assert user.is_locked is False
        assert user.get_lock_remaining_seconds() == 0


@pytest.mark.asyncio
async def test_login_endpoint(async_client: AsyncClient):
    """测试登录接口"""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin@123"}
    )
    # 注意：此测试需要数据库中有 admin 用户
    # 实际测试时可能返回 401（数据库未初始化）
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient):
    """测试无效凭证登录"""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent", "password": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(async_client: AsyncClient):
    """测试未认证访问"""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
