import json
import time

# ========= CONFIG =========
DEFAULT_MIOT_ENTITY = "vacuum.xiaomi_c102gl_4f4d_robot_cleaner"

# Room helpers you use
ALL_ROOMS = (1, 2, 3, 4, 5, 6, 7, 10)

# Input_select helper entity-k (HU feliratokkal)
MODE_ENTITY = "input_select.x20_mode"
SUCTION_ENTITY = "input_select.x20_suction"
WATER_ENTITY = "input_select.x20_water"
UI_STATE_ENTITY = "input_select.x20_ui_state"


# Mode mapping: siid:4 piid:23 (clean_setting uint32)
MODE_MAP = {
    "porszívózás": 67586,
    "porszívózás és felmosás": 67584,
    "felmosás": 67585,
    "porszívózás majd felmosás": 67587,
}

# Suction mapping: siid:4 piid:4 (0..3)
SUCTION_MAP = {
    "csendes": 0,
    "normál": 1,
    "erős": 2,
    "turbó": 3,
}

# Water mapping: siid:4 piid:5 (0..3) where 0 = no water
WATER_MAP = {
    "száraz": 1,
    "normál": 2,
    "nedves": 3,
}

# Default values if helper state is unknown
DEFAULT_MODE = 67586
DEFAULT_SUCTION = 1
DEFAULT_WATER = 2

# Delays between property sets (seconds)
DELAY_S = 1.0

# Full clean action (confirm if this is correct for your device)
FULL_CLEAN_SIID = 2
FULL_CLEAN_AIID = 1

# Pause action
PAUSE_SIID = 2
PAUSE_AIID = 2

# Dock / return to base action
DOCK_SIID = 3
DOCK_AIID = 1


# ========= HELPERS =========

def set_ui_state(state: str):
    hass.services.call(
        "input_select",
        "select_option",
        {
            "entity_id": UI_STATE_ENTITY,
            "option": state,
        },
        False,
    )
    
def get_state(entity_id: str) -> str:
    st = hass.states.get(entity_id)
    return st.state if st else "unknown"


def clamp_int(v, lo, hi, default):
    try:
        i = int(v)
    except Exception:
        return default
    return lo if i < lo else hi if i > hi else i


def miot_set_property(entity_id: str, siid: int, piid: int, value):
    hass.services.call(
        "xiaomi_miot",
        "set_miot_property",
        {"entity_id": entity_id, "siid": siid, "piid": piid, "value": value},
        False,
    )


def miot_call_action(entity_id: str, siid: int, aiid: int, params=None, force_params=None, throw=None):
    svc = {"entity_id": entity_id, "siid": siid, "aiid": aiid}
    if params is not None:
        svc["params"] = params
    if force_params is not None:
        svc["force_params"] = force_params
    if throw is not None:
        svc["throw"] = throw

    hass.services.call("xiaomi_miot", "call_action", svc, False)


# ========= MAIN =========
cmd = str(data.get("command", "start")).strip().lower()
miot_entity = str(data.get("miot_entity", DEFAULT_MIOT_ENTITY)).strip()

# repeats only used for start/custom clean
repeats = clamp_int(data.get("repeats", 1), 1, 3, 1)

if cmd == "pause":
    miot_call_action(miot_entity, PAUSE_SIID, PAUSE_AIID, params=[])
    set_ui_state("paused")
    logger.info("x20_controller: PAUSE")
    return

if cmd == "dock":
    miot_call_action(miot_entity, DOCK_SIID, DOCK_AIID, params=[])
    set_ui_state("idle")
    logger.info("x20_controller: DOCK")
    return

if cmd == "stop_and_dock":
    # pause/stop first (same action on your device), then dock
    miot_call_action(miot_entity, PAUSE_SIID, PAUSE_AIID, params=[])
    time.sleep(0.3)
    miot_call_action(miot_entity, DOCK_SIID, DOCK_AIID, params=[])
    set_ui_state("idle")
    logger.info("x20_controller: STOP_AND_DOCK")
    return

# ---- START branch ----
set_ui_state("runnning")
# 1) read mode/suction/water from helpers
mode_name = get_state(MODE_ENTITY)
suction_name = get_state(SUCTION_ENTITY)
water_name = get_state(WATER_ENTITY)

mode_val = MODE_MAP.get(mode_name, DEFAULT_MODE)
suction_val = SUCTION_MAP.get(suction_name, DEFAULT_SUCTION)
water_val = WATER_MAP.get(water_name, DEFAULT_WATER)

# 2) apply properties with delays (matches your working flow)
miot_set_property(miot_entity, siid=4, piid=23, value=mode_val)
time.sleep(DELAY_S)

miot_set_property(miot_entity, siid=4, piid=4, value=suction_val)
time.sleep(DELAY_S)

miot_set_property(miot_entity, siid=4, piid=5, value=water_val)
time.sleep(DELAY_S)

# 3) build room selection from booleans
room_ids = []
for rid in ALL_ROOMS:
    st = hass.states.get(f"input_boolean.room_{rid}")
    if st and st.state == "on":
        room_ids.append(rid)

selected_count = len(room_ids)
total_count = len(ALL_ROOMS)
do_full_clean = (selected_count == 0) or (selected_count == total_count)

if do_full_clean:
    miot_call_action(miot_entity, FULL_CLEAN_SIID, FULL_CLEAN_AIID, params=[])
    logger.info("x20_controller: START FULL_CLEAN selected=%s/%s mode=%s suction=%s water=%s",
                selected_count, total_count, mode_val, suction_val, water_val)
else:
    # IMPORTANT: keep your currently working selects tuple
    # [room_id, repeats, 2, 2, 1]  (unknown internals but works)
    selects = [[rid, repeats, 2, 2, 1] for rid in room_ids]
    payload = json.dumps({"selects": selects}, separators=(",", ":"))

    miot_call_action(
        miot_entity,
        siid=4,
        aiid=1,
        params=[
            {"piid": 1, "value": 18},
            {"piid": 10, "value": payload},
        ],
        force_params=True,
        throw=True,
    )
    logger.info("x20_controller: START CUSTOM rooms=%s repeats=%s mode=%s suction=%s water=%s payload=%s",
                room_ids, repeats, mode_val, suction_val, water_val, payload)