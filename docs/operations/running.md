# Running the robot

The launch recipes for each job, in the order you'd start them. Start the
robot base first, in its own terminal; everything else runs on top of it.
Each terminal needs `source ~/orbibot_ws/install/setup.bash`.

## The robot base

```bash
ros2 launch orbibot_bringup robot.launch.py
ros2 launch orbibot_bringup robot.launch.py use_camera:=true   # with the RealSense
```

This starts the robot model, the hardware bridge, the EKF and the LiDAR, and
turns the motors on after 6 s. See [orbibot_bringup](../../src/orbibot_bringup/README.md).

## Driving from the web dashboard

```bash
ros2 launch orbibot_webgui webgui.launch.py                  # rosbridge :9090, camera over WebRTC :8081
ros2 launch orbibot_webgui webgui.launch.py use_video:=false # without the camera
```

Build the frontend once, then serve it (no launch file serves it):

```bash
cd ~/orbibot_ws/src/orbibot_webgui/frontend
npm install && npm run build
python3 -m http.server 5173 --directory dist
```

Open `http://<robot>:5173` in a browser on the same network. Don't run the
Vite dev server on the Pi: it costs too much CPU. Details in
[orbibot_webgui](../../src/orbibot_webgui/README.md).

## Building a map

```bash
ros2 launch orbibot_bringup mapping.launch.py
```

Drive around from the dashboard, then save the map:

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map
```

`mapping.launch.py` loads `nav2_params.yaml` by default; pass
`nav_params_file:=` with `nav2_params_slam.yaml` for the parameters written for
live SLAM ([known issue](../../src/orbibot_bringup/known-issues.md)).

## Navigating on a saved map

```bash
ros2 launch orbibot_navigation navigation.launch.py map_file:=$HOME/maps/my_map.yaml
```

Set the initial pose and send goals from RViz or the dashboard. The package
ships two example maps in `src/orbibot_navigation/maps/`.

## Exploring on its own

```bash
ros2 launch orbibot_bringup exploration.launch.py
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: start"
```

The explorer is written but untested against a tuned Nav2: stay close and
ready to stop it.

## The AI agent

```bash
mkdir -p ~/.orbibot
cp ~/orbibot_ws/src/orbibot_agent/.env.local.example ~/.orbibot/.env.local
# put your API key in ~/.orbibot/.env.local (Gemini by default)

ros2 launch orbibot_agent chat_server.launch.py   # HTTP on :8082, used by the dashboard's chat panel
ros2 launch orbibot_agent mcp_server.launch.py    # MCP server over stdio
ros2 run orbibot_agent chat_cli                   # terminal chat
```

Ollama on `localhost:11434` works without a key. See
[orbibot_agent](../../src/orbibot_agent/README.md).

## Stopping

- Stop the node that is driving (Ctrl+C in its terminal). The firmware stops
  the motors 2 s after the last command, whatever happens on the Pi.
- Turn the motors off when you're done:
  `ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: false}"`
- In an emergency, cut the power at the battery.

Four nodes can publish `/cmd_vel` and nothing chooses between them yet, so
run one driver at a time ([status](../status.md)).
