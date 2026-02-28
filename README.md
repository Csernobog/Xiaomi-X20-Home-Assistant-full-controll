# Xiaomi-X20-Home-Assistant-full-controll
Xiaomi X20+ (c102gl) robot vacuum cleaner full and custom area cleaning, and cleaning setting - from "reverse  engeneering" </br>
![HA WS](/pictures/x20_full_controll.jpg)
# Entities / Integration

- Home Assistant integration: xiaomi_miot
- Vacuum entity: vacuum.xiaomi_c102gl_4f4d_robot_cleaner

Primary room-clean action: xiaomi_miot.call_action with siid: 4, aiid: 1

# Properties (set_miot_property)
## Cleaning mode / workflow (Vacuum / Mop combinations)

Service: xiaomi_miot.set_miot_property

SIID / PIID: siid: 4, piid: 23

Name (spec): clean_setting (uint32)

Values:

- 67586 → Vacuuming
- 67584 → Vacuuming & Mopping
- 67585 → Mopping
- 67587 → Vacuuming before mopping

## Suction / fan power

Service: xiaomi_miot.set_miot_property

SIID / PIID: siid: 4, piid: 4

Name: vacuum_extend.cleaning_mode

Values: 0..3 (device/app dependent labeling)

- 0 → Silent
- 1 → Standard
- 2 → Strong
- 3 → Turbo

## Mop water level / mop mode

Service: xiaomi_miot.set_miot_property

SIID / PIID: siid: 4, piid: 5

Name: vacuum_extend.mop_mode

Values:

- 0 → Mop water off (dry / no water)
- 1 → Water Level 1
- 2 → Water Level 2
- 3 → Water Level 3

## Cleaning area (not cleaning workflow mode)

Service: xiaomi_miot.get_properties

SIID / PIID: siid: 4, piid: 3

Name: vacuum_extend.cleaning_area

Note: This is not the vacuum/mop workflow mode!!

# Actions (call_action)
## Room / multi-room cleaning (segment plan)

Service: xiaomi_miot.call_action

SIID / AIID: siid: 4, aiid: 1

Required params:

piid: 1 → value: 18 (constant observed)

piid: 10 → value: "<STRING>" (stringified JSON; critical)

Payload format (string, JSON inside):

{"selects":[[room_id, repeats, x, y, z], ...]}

Example (two rooms)
{"selects":[[2,1,2,2,1],[6,1,2,2,1]]}
Notes:

- piid: 10 must be a string. If HA templating converts it into a dict/object, the device rejects it.
- Multi-room works with multiple entries in selects (processed in order).
- If a room ID is stale/invalid (e.g., leftover from old auto-mapping), the robot may skip it.

## Known reliable command path in HA

Due to HA script/Jinja type coercion issues, using python_script to call xiaomi_miot.call_action is deterministic and reliable for piid:10 payload string handling.
