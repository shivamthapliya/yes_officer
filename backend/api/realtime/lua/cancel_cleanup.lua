-- Mark the poll CANCELLED and delete every poll-scoped key except `meta`, which
-- stays (status CANCELLED) until its TTL as a fast-path cancellation marker.
-- KEYS: 1 meta, 2 active_pointer, 3 pending, 4 inflight, 5 answers, 6 seq,
--       7 participants, 8 questions, 9 results, 10 flush_index, 11 answer_counts
-- ARGV: 1 poll_id, 2 batch_key_prefix
redis.call('HSET', KEYS[1], 'status', 'CANCELLED')
if redis.call('GET', KEYS[2]) == ARGV[1] then
  redis.call('DEL', KEYS[2])
end
local ids = redis.call('ZRANGE', KEYS[4], 0, -1)
for _, id in ipairs(ids) do redis.call('DEL', ARGV[2] .. id) end
redis.call('DEL', KEYS[3], KEYS[4], KEYS[5], KEYS[6], KEYS[7], KEYS[8], KEYS[9], KEYS[11])
redis.call('ZREM', KEYS[10], ARGV[1])
return #ids
