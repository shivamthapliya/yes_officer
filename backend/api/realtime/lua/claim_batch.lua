-- Atomically move up to `max` pending messages into a batch list and record the
-- batch as in-flight. Concurrent claimers can never take the same message.
-- KEYS: 1 pending, 2 inflight, 3 flush_index
-- ARGV: 1 poll_id, 2 batch_key_prefix, 3 max, 4 min, 5 now_ms, 6 ttl_seconds, 7 batch_id
local len = redis.call('LLEN', KEYS[1])
if len == 0 then
  redis.call('ZREM', KEYS[3], ARGV[1])
  return {}
end
if len < tonumber(ARGV[4]) then return {} end

local msgs = redis.call('LRANGE', KEYS[1], 0, tonumber(ARGV[3]) - 1)
redis.call('LTRIM', KEYS[1], #msgs, -1)
local bkey = ARGV[2] .. ARGV[7]
redis.call('RPUSH', bkey, unpack(msgs))
redis.call('EXPIRE', bkey, ARGV[6])
redis.call('ZADD', KEYS[2], ARGV[5], ARGV[7])
redis.call('EXPIRE', KEYS[2], ARGV[6])

local first = redis.call('LINDEX', KEYS[1], 0)
if first then
  local d = cjson.decode(first)
  redis.call('ZADD', KEYS[3], d['received_ms'], ARGV[1])
else
  redis.call('ZREM', KEYS[3], ARGV[1])
end
return msgs
