-- KEYS: 1 meta, 2 pending, 3 flush_index
-- ARGV: 1 poll_id, 2 payload_json, 3 received_ms, 4 ttl_seconds
-- Returns the new pending length, or -1 when the poll is not ACTIVE
-- (so nothing can enter a closed or cancelled poll's buffer).
if redis.call('HGET', KEYS[1], 'status') ~= 'ACTIVE' then return -1 end
local n = redis.call('RPUSH', KEYS[2], ARGV[2])
redis.call('EXPIRE', KEYS[2], ARGV[4])
redis.call('ZADD', KEYS[3], 'NX', ARGV[3], ARGV[1])
return n
