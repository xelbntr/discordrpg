import random
from core.data.rooms import ROOMS, ROOMS_BY_FLOOR

# config
TOTAL_FLOORS = 4
ROOMS_PER_FLOOR = 8
MAX_RUN_LEVEL = 20

def gen_room(rank, floor, number, current_room):
    if number == 1:
        room_name, args = "basecamp", (rank,)
    elif number == ROOMS_PER_FLOOR:
        if floor == TOTAL_FLOORS:
            room_name, args = "finalboss", (rank,)
        else:
            room_name, args = "boss", (rank, floor)
    else:
        candidates = [
            room for room in ROOMS_BY_FLOOR[floor]
            if not ("safe" in ROOMS[room].tags and "safe" in ROOMS[current_room].tags)
        ]
        weights = [ROOMS[room].weight for room in candidates]
        room_name = random.choices(candidates, weights=weights)[0]
        args = (rank, floor)

    generate = ROOMS[room_name].generate
    if generate is None:
        raise NotImplementedError(f"Room generator for {room_name!r} is not implemented.")
    return generate(*args)
