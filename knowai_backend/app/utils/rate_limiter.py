from redis.asyncio import Redis

TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local bucket = redis.call('HMGET', key, 'tokens', 'updated_at')
local tokens = tonumber(bucket[1])
local updated_at = tonumber(bucket[2])
if tokens == nil then
    tokens = capacity
    updated_at = now
end
local delta = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + delta * refill_rate)
if tokens < requested then
    redis.call('HMSET', key, 'tokens', tokens, 'updated_at', now)
    redis.call('EXPIRE', key, 120)
    return 0
end
tokens = tokens - requested
redis.call('HMSET', key, 'tokens', tokens, 'updated_at', now)
redis.call('EXPIRE', key, 120)
return 1
"""


async def allow_token_bucket(
    redis: Redis,
    key: str,
    capacity: int,
    refill_per_minute: int,
    requested: int = 1,
) -> bool:
    now_ms = await redis.time()
    now = now_ms[0] * 1000 + now_ms[1] // 1000
    refill_rate = refill_per_minute / 60000
    allowed = await redis.eval(TOKEN_BUCKET_SCRIPT, 1, key, now, capacity, refill_rate, requested)
    return bool(int(allowed))


async def allow_user_once_per_second(redis: Redis, user_id: int, activity_id: int) -> bool:
    key = f"rate:seckill:{user_id}:{activity_id}"
    return bool(await redis.set(key, "1", nx=True, ex=1))
