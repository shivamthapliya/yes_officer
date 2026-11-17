-- Close the poll and snapshot its answers in one atomic step. Answer acceptance
-- and chat buffering stop at exactly this point.
-- KEYS: 1 meta, 2 active_pointer, 3 answers, 4 participants
-- ARGV: 1 poll_id
-- Returns {previous_status, answers_flat, participants}
local st = redis.call('HGET', KEYS[1], 'status')
if st == 'ACTIVE' then
  redis.call('HSET', KEYS[1], 'status', 'CLOSED')
end
if redis.call('GET', KEYS[2]) == ARGV[1] then
  redis.call('DEL', KEYS[2])
end
return {st or 'MISSING', redis.call('HGETALL', KEYS[3]), redis.call('SMEMBERS', KEYS[4])}
