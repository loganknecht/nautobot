import hashlib
import math
import time

from django.core.cache import cache
import redis.exceptions

from nautobot.core.utils.cache import construct_cache_key

COUNTER_TTL_WINDOW_MULTIPLE = 2


CREDENTIAL_DIGEST_LENGTH = 16

TOKEN_BUCKET_SCHEME = "user_token"
ADDRESS_BUCKET_SCHEME = "address"
ANONYMOUS_BUCKET = "anonymous_request"


def hash_user_identifier(credential):
    """Return a short, non-reversible digest of a credential string.

    Args:
        credential (str): The raw credential. Never leaves this function.

    Returns:
        str: The leading `CREDENTIAL_DIGEST_LENGTH` hex characters of the SHA-256 digest.
    """
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()[:CREDENTIAL_DIGEST_LENGTH]


def get_user_rate_limit_bucket_identifier(request):
    """
    Associates a User with a specific bucket in Redis by using their hashed token
    as the identifier.

    When User Token not found, defaults to an anonymous identifier.

    Args:
        request (HttpRequest): The user's request

    Returns:
        str: A bucket identifier for redis
    """
    # Figoure out an identifier to be used when possible for anonymous
    bucket_name = f"{ANONYMOUS_BUCKET}:{ANONYMOUS_BUCKET}"

    authorization_header = request.META.get("HTTP_AUTHORIZATION", "")
    if authorization_header:
        hashed_user_identifier = hash_user_identifier(authorization_header)
        bucket_name = f"{TOKEN_BUCKET_SCHEME}:{hashed_user_identifier}"

    return bucket_name

def get_time_window_id(now, window_seconds):
    """
    Args:
        now (float): A Unix timestamp
        window_seconds (int): Width of a window.

    Returns:
        int: The window identifier.
    """
    return int(now // window_seconds)


def get_seconds_remaining_in_window(now, window_seconds):
    """
    Args:
        now (float): A Unix timestamp, as returned by `time.time()`.
        window_seconds (int): Width of a window.

    Returns:
        int: Whole seconds remaining, at least 1.
    """
    return max(1, math.ceil(window_seconds - (now % window_seconds)))


def get_consumed_budget_cache_key(bucket, window_id):
    """
    Args:
        bucket (str): A bucket identifier from `get_rate_limit_bucket()`.
        window_id (int): A window identifier from `get_time_window()`.

    Returns:
        str: The cache key.
    """
    # Not branch aware: a rate-limiting budget has nothing to do with Version Control branches.
    return construct_cache_key(charge_bucket, branch_aware=False, bucket=bucket, window=window_id)


def charge_bucket(bucket_identifier, cost, now, window_seconds):
    """
    Args:
        bucket_identifier (str): A bucket identifier from `get_rate_limit_bucket()`.
        cost (int): Complexity cost to charge. Must be an integer - the underlying Redis `INCRBY`
            cannot accumulate floats.
        now (float): A Unix timestamp, as returned by `time.time()`.
        window_seconds (int): Width of a window.

    Returns:
        int: Total budget consumed by `bucket_identifier` in the current window, including `cost`.
        None: If the counter could not be reached. Callers MUST treat this as "do not enforce"; a
            rate limiter whose counter is unavailable must never take the REST API offline.
    """
    current_time_window = get_time_window(now, window_seconds)
    cache_key = get_consumed_budget_cache_key(bucket_identifier, current_time_window)
    timeout = window_seconds * COUNTER_TTL_WINDOW_MULTIPLE

    try:
        try:
            return cache.incr(cache_key, cost)
        except ValueError:
            cache.add(cache_key, cost, timeout=timeout)
            return cache.get(cache_key, cost)
    except redis.exceptions.RedisError:
        return None

def get_bu


def get_budget_state(bucket_identifier, cost, window_seconds):
    """
    Args:
        bucket_identifier (str): A bucket identifier from `get_rate_limit_bucket()`.
        cost (int): Complexity cost to charge.
        window_seconds (int): Width of a window.

    Returns:
        tuple: `(consumed, seconds_remaining_in_window)`, where `consumed` is `None` if the counter
            was unreachable.
    """
    now = time.time()

    consumed_bugdet = charge_bucket(bucket_identifier, cost, now, window_seconds)
    seconds_remaining_in_window = get_seconds_remaining_in_window(now, window_seconds)

    return (consumed_bugdet, seconds_remaining_in_window)
