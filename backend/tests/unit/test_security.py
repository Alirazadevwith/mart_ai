"""Password hashing and JWT behaviour."""

from datetime import timedelta

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_does_not_contain_the_plaintext(self) -> None:
        hashed = hash_password("correct horse battery staple")
        assert "correct horse battery staple" not in hashed

    def test_same_password_hashes_differently_each_time(self) -> None:
        assert hash_password("same-password") != hash_password("same-password")

    def test_verify_accepts_the_correct_password(self) -> None:
        assert verify_password("s3cret-pw", hash_password("s3cret-pw")) is True

    def test_verify_rejects_the_wrong_password(self) -> None:
        assert verify_password("wrong-pw", hash_password("s3cret-pw")) is False

    def test_passwords_longer_than_bcrypts_72_byte_limit_are_not_truncated(self) -> None:
        """Without SHA-256 pre-hashing, these two 80-char passwords would collide."""
        base = "a" * 72
        hashed = hash_password(base + "ending-one")
        assert verify_password(base + "ending-two", hashed) is False

    def test_verify_returns_false_for_a_malformed_hash(self) -> None:
        assert verify_password("anything", "not-a-bcrypt-hash") is False


class TestAccessTokens:
    def test_decoding_returns_the_subject_and_tenant(self) -> None:
        token = create_access_token(subject="user-42", tenant_id="tenant-7", role="merchant")
        payload = decode_token(token)
        assert payload.subject == "user-42"
        assert payload.tenant_id == "tenant-7"
        assert payload.role == "merchant"

    def test_access_tokens_are_marked_as_access_tokens(self) -> None:
        payload = decode_token(create_access_token(subject="u", tenant_id="t", role="staff"))
        assert payload.token_type == "access"

    def test_refresh_tokens_are_marked_as_refresh_tokens(self) -> None:
        payload = decode_token(create_refresh_token(subject="u", tenant_id="t", role="staff"))
        assert payload.token_type == "refresh"

    def test_an_expired_token_is_rejected(self) -> None:
        token = create_access_token(
            subject="u", tenant_id="t", role="customer", expires_delta=timedelta(seconds=-10)
        )
        with pytest.raises(TokenError, match="expired"):
            decode_token(token)

    def test_a_tampered_signature_is_rejected(self) -> None:
        token = create_access_token(subject="u", tenant_id="t", role="customer")
        with pytest.raises(TokenError):
            decode_token(token[:-4] + "AAAA")

    def test_garbage_is_rejected(self) -> None:
        with pytest.raises(TokenError):
            decode_token("this.is.not-a-jwt")

    def test_every_token_gets_a_unique_id_so_it_can_be_revoked(self) -> None:
        first = decode_token(create_access_token(subject="u", tenant_id="t", role="staff"))
        second = decode_token(create_access_token(subject="u", tenant_id="t", role="staff"))
        assert first.jti != second.jti
