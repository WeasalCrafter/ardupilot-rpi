-- companion.lua
-- tells the pi companion computer to start/stop video recording based on arm state.
-- sends MAV_CMD_VIDEO_START_CAPTURE / MAV_CMD_VIDEO_STOP_CAPTURE over the mavlink
-- link on serial4, learning the pi's channel from its heartbeat.

local mavlink_msgs = require("MAVLink/mavlink_msgs")

local HEARTBEAT_ID   = mavlink_msgs.get_msgid("HEARTBEAT")
local COMMAND_ACK_ID  = mavlink_msgs.get_msgid("COMMAND_ACK")

local MAV_CMD_VIDEO_START_CAPTURE  = 2500
local MAV_CMD_VIDEO_STOP_CAPTURE   = 2501
local MAV_AUTOPILOT_INVALID        = 8   -- companion computers report this as their autopilot type
local MAV_TYPE_ONBOARD_CONTROLLER  = 18  -- distinguishes the pi from a gcs, which also reports autopilot invalid
local MAV_RESULT_ACCEPTED          = 0

local video_command_names = {
  [MAV_CMD_VIDEO_START_CAPTURE] = "Video Start Capture",
  [MAV_CMD_VIDEO_STOP_CAPTURE]  = "Video Stop Capture",
}

local UPDATE_INTERVAL_MS = 200

mavlink:init(4, 2)
mavlink:register_rx_msgid(HEARTBEAT_ID)
mavlink:register_rx_msgid(COMMAND_ACK_ID)

local msg_map = {
  [HEARTBEAT_ID]   = "HEARTBEAT",
  [COMMAND_ACK_ID] = "COMMAND_ACK",
}

local companion_chan = nil
local was_armed = false

-- sends a video start/stop command to the pi over the companion mavlink channel
local function send_video_command(command)
  if companion_chan == nil then
    gcs:send_text(6, "[COMPANION] No link to Pi yet")
    return
  end

  local cmd = {
    target_system     = 0,
    target_component  = 0,
    command           = command,
    confirmation      = 0,
    param1 = 0, param2 = 0, param3 = 0, param4 = 0,
    param5 = 0, param6 = 0, param7 = 0,
  }
  mavlink:send_chan(companion_chan, mavlink_msgs.encode("COMMAND_LONG", cmd))
end

-- listens for the pi's heartbeat to learn which channel it is on
local function poll_mavlink()
  local msg, chan = mavlink:receive_chan()
  if msg == nil then
    return
  end

  local parsed = mavlink_msgs.decode(msg, msg_map)
  if parsed == nil then
    return
  end

  if parsed.msgid == HEARTBEAT_ID
      and parsed.autopilot == MAV_AUTOPILOT_INVALID
      and parsed.type == MAV_TYPE_ONBOARD_CONTROLLER then
    companion_chan = chan
  elseif parsed.msgid == COMMAND_ACK_ID then
    local name = video_command_names[parsed.command]
    if name ~= nil then
      if parsed.result == MAV_RESULT_ACCEPTED then
        gcs:send_text(6, "[COMPANION] Command Acknowledged: " .. name)
      else
        gcs:send_text(3, "[COMPANION] Command Failed: " .. name)
      end
    end
  end
end

function update()
  poll_mavlink()

  local is_armed = arming:is_armed()
  if is_armed ~= was_armed then
    if is_armed then
      send_video_command(MAV_CMD_VIDEO_START_CAPTURE)
      gcs:send_text(6, "[COMPANION] Requested Video Start Capture")
    else
      send_video_command(MAV_CMD_VIDEO_STOP_CAPTURE)
      gcs:send_text(6, "[COMPANION] Requested Video Stop Capture")
    end
    was_armed = is_armed
  end

  return update, UPDATE_INTERVAL_MS
end

return update()
