from pydantic import BaseModel, SecretStr, field_validator

# Whitelist of algorithms accepted by ``JWTConfig.algorithm``.
# ``"none"`` (in any casing) is explicitly forbidden — it would disable signature
# verification entirely and is a well-known JWT vulnerability vector.
_ALLOWED_ALGORITHMS = frozenset({"HS256", "HS384", "HS512", "RS256", "ES256"})


class JWTConfig(BaseModel):
    secret: SecretStr
    algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    # Deprecated: kept for back-compat with existing settings.toml files.
    # Prefer ``access_token_ttl_minutes`` / ``refresh_token_ttl_days``.
    ttl_hours: int = 24

    @field_validator("algorithm")
    @classmethod
    def _reject_none_algorithm(cls, value: str) -> str:
        if value.lower() == "none":
            raise ValueError(
                "JWT algorithm 'none' is not allowed: it disables signature "
                "verification and is a known security vulnerability."
            )
        if value not in _ALLOWED_ALGORITHMS:
            raise ValueError(
                f"Unsupported JWT algorithm {value!r}. " f"Allowed: {sorted(_ALLOWED_ALGORITHMS)}."
            )
        return value
