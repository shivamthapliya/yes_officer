-- KEYS: 1 meta, 2 questions, 3 answers, 4 seq, 5 participants, 6 answer_counts
-- ARGV: 1 question_id, 2 student_id, 3 option_id, 4 now_ms, 5 ttl_seconds
local meta = redis.call('HMGET', KEYS[1], 'status', 'current_question_id', 'deadline_ms')
if meta[1] ~= 'ACTIVE' then return {'closed'} end
if tonumber(ARGV[4]) >= tonumber(meta[3]) then return {'expired'} end
if meta[2] ~= ARGV[1] then return {'not_current'} end

local q = redis.call('HGET', KEYS[2], ARGV[1])
if not q then return {'not_current'} end
local qd = cjson.decode(q)
local valid = false
for _, o in ipairs(qd['options']) do
  if o == ARGV[3] then valid = true break end
end
if not valid then return {'invalid_option'} end

local field = ARGV[1] .. ':' .. ARGV[2]
local existing = redis.call('HGET', KEYS[3], field)
if existing then return {'duplicate', existing} end

local s = redis.call('INCR', KEYS[4])
local value = '{"option_id":"' .. ARGV[3] .. '","ts_ms":' .. ARGV[4] .. ',"seq":' .. s .. '}'
redis.call('HSET', KEYS[3], field, value)
redis.call('SADD', KEYS[5], ARGV[2])
local count = redis.call('HINCRBY', KEYS[6], ARGV[1], 1)
redis.call('HINCRBY', KEYS[6], ARGV[1] .. ':' .. ARGV[3], 1)
for i = 3, 6 do redis.call('EXPIRE', KEYS[i], ARGV[5]) end
return {'accepted', value, tostring(count)}
