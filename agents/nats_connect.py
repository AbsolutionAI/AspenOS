"""Shared NATS connect helper — token / user-pass / nkey / TLS.

Env (priority):
  1. NATS_URL with embedded user:pass or :token@
  2. NATS_USER + NATS_PASSWORD
  3. STARSHIP_NATS_TOKEN (token auth — fleet shared-token mode only)
  4. STARSHIP_NATS_NKEY_SEED or path in STARSHIP_NATS_NKEY_SEED_FILE
  5. STARSHIP_NATS_TLS=1 + STARSHIP_NATS_CA[/CERT/KEY] for mTLS (H-006: fails
     closed without a fleet CA unless STARSHIP_NATS_TLS_INSECURE=1)

H-001 (ASP-169): when STARSHIP_NATS_MODE=accounts (the default since the
no-auth agent-bus removal), connects without user/pass or nkey fail closed.

H-002 (ASP-170): when the node presents a per-node mTLS identity
(STARSHIP_NATS_CERT), connecting with a revoked identity fails closed;
the revocation list lives next to the fleet CA (revocations.list) or at
STARSHIP_NATS_REVOCATIONS.
"""

from __future__ import annotations

import os
import re
import ssl
from typing import Any, Optional
from urllib.parse import quote


def _mode() -> str:
    return os.getenv("STARSHIP_NATS_MODE", "").strip().lower()


def require_account_credentials() -> None:
    """H-001 (ASP-169): fail closed in accounts mode without real credentials.

    Accounts-mode connections must use user/password or an nkey seed.
    Bare-token and anonymous connects are refused with a migration hint.
    """
    if _mode() != "accounts":
        return
    has_user_pass = bool(
        os.getenv("NATS_USER", "").strip()
        and os.getenv("NATS_PASSWORD", "").strip()
        or re.search(r"^[a-z+]+://[^/@:]+:[^/@]+@", (os.getenv("NATS_URL") or "").strip())
    )
    if not (has_user_pass or nkey_seed()):
        raise RuntimeError(
            "NATS accounts mode requires account credentials "
            "(NATS_USER/NATS_PASSWORD or STARSHIP_NATS_NKEY_SEED). "
            "Anonymous/token connects are no longer accepted (H-001). "
            "Source a role env from /etc/starship/nats/creds/ or run "
            "scripts/gen-nats-accounts.sh."
        )


def build_nats_url(
    url: Optional[str] = None,
    *,
    user: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> str:
    url = url or os.getenv("NATS_URL", "nats://127.0.0.1:4222")
    user = user if user is not None else os.getenv("NATS_USER", "").strip() or None
    password = password if password is not None else os.getenv("NATS_PASSWORD", "").strip() or None
    token = token if token is not None else os.getenv("STARSHIP_NATS_TOKEN", "").strip() or None

    # Upgrade scheme when TLS requested
    tls_on = os.getenv("STARSHIP_NATS_TLS", "").strip().lower() in ("1", "true", "yes", "on")
    if tls_on and url.startswith("nats://"):
        url = "tls://" + url[len("nats://"):]

    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        return url  # already has credentials

    if user and password:
        return f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}@{rest}"
    if token:
        return f"{scheme}://:{quote(token, safe='')}@{rest}"
    return url


def nkey_seed() -> Optional[str]:
    seed = os.getenv("STARSHIP_NATS_NKEY_SEED", "").strip()
    if seed:
        return seed
    path = os.getenv("STARSHIP_NATS_NKEY_SEED_FILE", "").strip()
    if path and os.path.isfile(path):
        return open(path, encoding="utf-8").read().strip()
    return None


def tls_context() -> Optional[ssl.SSLContext]:
    """Build SSL context when STARSHIP_NATS_TLS is enabled.

    H-006 (ASP-174): fail closed when TLS is requested but no fleet CA is
    configured — silently trusting any server cert defeats TLS. Per-node
    mTLS identities come from gen-nats-tls.sh --node <name> via
    STARSHIP_NATS_CERT/STARSHIP_NATS_KEY. Set STARSHIP_NATS_TLS_INSECURE=1
    only for throwaway local development.
    """
    flag = os.getenv("STARSHIP_NATS_TLS", "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return None
    ca = os.getenv("STARSHIP_NATS_CA", "").strip()
    cert = os.getenv("STARSHIP_NATS_CERT", "").strip()
    key = os.getenv("STARSHIP_NATS_KEY", "").strip()
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    if cert and key and os.path.isfile(cert) and os.path.isfile(key):
        ctx.load_cert_chain(certfile=cert, keyfile=key)
    if ca and os.path.isfile(ca):
        ctx.load_verify_locations(cafile=ca)
        return ctx
    if os.getenv("STARSHIP_NATS_TLS_INSECURE", "").strip().lower() in ("1", "true", "yes", "on"):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    raise RuntimeError(
        "STARSHIP_NATS_TLS=1 requires STARSHIP_NATS_CA pointing at the fleet "
        "CA (H-006). Source /etc/starship/nats.env or regenerate material with "
        "scripts/gen-nats-tls.sh. Set STARSHIP_NATS_TLS_INSECURE=1 only for "
        "throwaway local development."
    )


def connect_kwargs() -> dict[str, Any]:
    """Extra kwargs for nats.connect (nkeys / tls if available)."""
    kw: dict[str, Any] = {}
    seed = nkey_seed()
    if seed:
        kw["nkeys_seed_str"] = seed
    tls = tls_context()
    if tls is not None:
        kw["tls"] = tls
    return kw


def revocations_path() -> Optional[str]:
    """H-002: locate the fleet node revocation list.

    STARSHIP_NATS_REVOCATIONS wins; otherwise the list is expected next to
    the fleet CA (revocations.list alongside STARSHIP_NATS_CA).
    """
    override = os.getenv("STARSHIP_NATS_REVOCATIONS", "").strip()
    if override:
        return override
    ca = os.getenv("STARSHIP_NATS_CA", "").strip()
    if ca:
        return os.path.join(os.path.dirname(ca) or ".", "revocations.list")
    return None


def local_identity_cn() -> Optional[str]:
    """H-002: CN of this node's mTLS identity cert (STARSHIP_NATS_CERT)."""
    cert = os.getenv("STARSHIP_NATS_CERT", "").strip()
    if not cert or not os.path.isfile(cert):
        return None
    try:
        import ssl as _ssl

        info = _ssl._ssl._test_decode_cert(cert)  # type: ignore[attr-defined]
        for rdn in info.get("subject", []):
            for key, value in rdn:
                if key == "commonName":
                    return value
    except Exception:
        return None
    return None


def is_revoked(node_id: Optional[str]) -> bool:
    """H-002: True when node_id appears on the fleet revocation list."""
    if not node_id:
        return False
    path = revocations_path()
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    if line.split()[0] == node_id:
                        return True
    except OSError:
        return False
    return False


def check_local_identity() -> None:
    """H-002: fail closed when this node's mTLS identity is revoked."""
    cn = local_identity_cn()
    if cn and is_revoked(cn):
        raise RuntimeError(
            f"Local node identity '{cn}' is on the fleet revocation list "
            f"({revocations_path()}): refusing to connect (H-002). Contact "
            "the ops manager to clear revocation or re-enroll via "
            "scripts/fleet-enroll.sh."
        )


async def connect(url: Optional[str] = None, **kwargs):
    """Connect to NATS using env credentials."""
    from nats import connect as nats_connect

    require_account_credentials()
    check_local_identity()
    final_url = build_nats_url(url)
    kw = connect_kwargs()
    kw.update(kwargs)
    # If nkeys provided, prefer nkey auth (drop userinfo from URL to avoid conflict)
    if kw.get("nkeys_seed_str") or kw.get("nkeys_seed"):
        try:
            host = final_url.split("@")[-1] if "@" in final_url else final_url
            return await nats_connect(host, **kw)
        except Exception:
            kw.pop("nkeys_seed_str", None)
            kw.pop("nkeys_seed", None)
            return await nats_connect(final_url, **kw)
    return await nats_connect(final_url, **kw)


def safe_url(url: Optional[str] = None) -> str:
    """URL with password redacted for logs."""
    u = build_nats_url(url)
    if "://" not in u or "@" not in u:
        return u
    scheme, rest = u.split("://", 1)
    creds, host = rest.rsplit("@", 1)
    if ":" in creds:
        user, _ = creds.split(":", 1)
        return f"{scheme}://{user}:***@{host}"
    return f"{scheme}://***@{host}"
