-- KEYS: 1 meta
-- ARGV: 1 expected_current_question_id ('' for none), 2 next_question_id, 3 index, 4 opened_ms
-- Returns 'ok', 'closed', or 'stale' (someone else already advanced).
local meta = redis.call('HMGET', KEYS[1], 'status', 'current_question_id')
if meta[1] ~= 'ACTIVE' then return 'closed' end
if (meta[2] or '') ~= ARGV[1] then return 'stale' end
redis.call('HSET', KEYS[1], 'current_question_id', ARGV[2], 'current_index', ARGV[3], 'opened_ms', ARGV[4])
return 'ok'
