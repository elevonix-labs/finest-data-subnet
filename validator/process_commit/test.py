import redis
import json
redis_queue = redis.Redis(host='localhost', port=6379, db=0)

# scores_list = [0.9, 0.8, 0.7, 0.8, 0.9, 0.5]
# for id, score in enumerate(scores_list):
#     redis_queue.hset("scores", id, json.dumps(score))

current_score = redis_queue.hget("scores", "5")
print(current_score)
current_score = json.loads(current_score)
print(current_score)