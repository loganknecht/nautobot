import hashlib
import math

from django.core.cache import cache
import redis.exceptions

COUNTER_TTL_WINDOW_MULTIPLE = 2
CREDENTIAL_DIGEST_LENGTH = 16
TOKEN_BUCKET_SCHEME = "user_token"  # noqa: S105  # hardcoded-password-string


def hash_user_identifier(user_identifier):
    utf8_encoded_identifier = user_identifier.encode("utf-8")
    sha256_identifier = hashlib.sha256(utf8_encoded_identifier)
    hexdigest = sha256_identifier.hexdigest()
    truncated_hexdigest = hexdigest[:CREDENTIAL_DIGEST_LENGTH]

    return truncated_hexdigest


def get_user_rate_limit_bucket_id(user_token):
    if not user_token:
        return None

    hashed_user_identifier = hash_user_identifier(user_token)
    user_rate_limit_bucket_id = f"{TOKEN_BUCKET_SCHEME}:{hashed_user_identifier}"

    return user_rate_limit_bucket_id


def get_time_window_id(current_time, window_seconds):
    time_window_id = int(current_time // window_seconds)

    return time_window_id


def get_seconds_remaining_in_window(current_time, window_seconds):
    elapsed_seconds_in_window = current_time % window_seconds
    remaining_seconds_in_window = window_seconds - elapsed_seconds_in_window
    whole_remaining_seconds = math.ceil(remaining_seconds_in_window)
    floored_remaining_seconds = max(1, whole_remaining_seconds)

    return floored_remaining_seconds


def get_consumed_budget_cache_key(bucket_id, window_id):
    cache_key = f"nautobot.core.rate_limiting.consumed_budget:{bucket_id}:{window_id}"

    return cache_key


def charge_bucket(bucket_id, cost, current_time, window_seconds):
    time_window_id = get_time_window_id(current_time, window_seconds)
    cache_key = get_consumed_budget_cache_key(bucket_id, time_window_id)
    timeout = window_seconds * COUNTER_TTL_WINDOW_MULTIPLE

    try:
        try:
            return cache.incr(cache_key, cost)
        except ValueError:
            was_counter_created = cache.add(cache_key, cost, timeout=timeout)
            if was_counter_created:
                return cost
            return cache.incr(cache_key, cost)
    except redis.exceptions.RedisError:
        return None


def get_current_bucket(bucket_id, current_time, window_seconds):
    time_window_id = get_time_window_id(current_time, window_seconds)
    cache_key = get_consumed_budget_cache_key(bucket_id, time_window_id)

    try:
        return cache.get(cache_key, 0)
    except redis.exceptions.RedisError:
        return None
