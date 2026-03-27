
const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 9090 });

console.log('Mock ROS Bridge running on ws://localhost:9090');

wss.on('connection', function connection(ws) {
    console.log('Client connected');

    const subscriptions = new Set();
    const advertised = new Set();

    ws.on('message', function incoming(message) {
        try {
            const msg = JSON.parse(message);

            if (msg.op === 'subscribe') {
                console.log(`Client subscribed to ${msg.topic}`);
                subscriptions.add(msg.topic);
            } else if (msg.op === 'unsubscribe') {
                console.log(`Client unsubscribed from ${msg.topic}`);
                subscriptions.delete(msg.topic);
            } else if (msg.op === 'advertise') {
                console.log(`Client advertised ${msg.topic}`);
                advertised.add(msg.topic);
            } else if (msg.op === 'publish') {
                // console.log(`Client published to ${msg.topic}:`, msg.msg);
            }
        } catch (e) {
            console.error('Error parsing message:', e);
        }
    });

    // --- Mock Data Generators ---

    // 1. Odometry (Stationary with slight drift)
    let x = 0.0;
    let y = 0.0;
    let theta = 0.0;

    const odomInterval = setInterval(() => {
        if (subscriptions.has('/odom')) {
            // Small random drift to simulate sensor noise
            x += (Math.random() - 0.5) * 0.01;
            y += (Math.random() - 0.5) * 0.01;
            theta += (Math.random() - 0.5) * 0.05;

            // Keep robot near center (prevent drift too far)
            x = Math.max(-0.5, Math.min(0.5, x));
            y = Math.max(-0.5, Math.min(0.5, y));

            const msg = {
                op: 'publish',
                topic: '/odom',
                type: 'nav_msgs/Odometry',
                msg: {
                    header: {
                        seq: 0,
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'odom'
                    },
                    child_frame_id: 'base_link',
                    pose: {
                        pose: {
                            position: { x: x, y: y, z: 0 },
                            orientation: { x: 0, y: 0, z: Math.sin(theta / 2), w: Math.cos(theta / 2) }
                        },
                        covariance: new Array(36).fill(0)
                    },
                    twist: {
                        twist: {
                            linear: { x: 0, y: 0, z: 0 },
                            angular: { x: 0, y: 0, z: 0 }
                        },
                        covariance: new Array(36).fill(0)
                    }
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 100);

    // 2. Battery Status (/orbibot/system_status)
    let time = 0;
    const batteryInterval = setInterval(() => {
        if (subscriptions.has('/orbibot/system_status')) {
            time += 0.1;
            const voltage = 11.5 + Math.sin(time) * 1.5;

            const msg = {
                op: 'publish',
                topic: '/orbibot/system_status',
                type: 'orbibot_msgs/SystemStatus',
                msg: {
                    header: {
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'base_link'
                    },
                    battery_voltage: voltage,
                    motors_enabled: true,
                    emergency_stop: false,
                    hardware_ok: true
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 1000);

    // 3. System Status Enriched (for System Monitor)
    const systemStatusInterval = setInterval(() => {
        if (subscriptions.has('/orbibot/system_status_enriched')) {
            const voltage = 11.5 + Math.sin(time) * 1.5;

            const msg = {
                op: 'publish',
                topic: '/orbibot/system_status_enriched',
                type: 'orbibot_msgs/SystemStatus',
                msg: {
                    header: {
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'base_link'
                    },
                    battery_voltage: voltage,
                    cpu_percent: 15 + Math.random() * 10,
                    ram_percent: 30 + Math.random() * 5,
                    cpu_temp: 50 + Math.random() * 10,
                    disk_percent: 45 + Math.random() * 2,
                    motors_enabled: true,
                    emergency_stop: false,
                    hardware_ok: true
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 1000);

    // 4. Laser Scan
    const scanInterval = setInterval(() => {
        if (subscriptions.has('/scan')) {
            const num_readings = 100;
            const ranges = [];
            for (let i = 0; i < num_readings; i++) {
                ranges.push(3.0 + Math.random() * 0.2);
            }

            const msg = {
                op: 'publish',
                topic: '/scan',
                type: 'sensor_msgs/LaserScan',
                msg: {
                    header: {
                        seq: 0,
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'laser_frame'
                    },
                    angle_min: -3.14,
                    angle_max: 3.14,
                    angle_increment: 6.28 / num_readings,
                    time_increment: 0,
                    scan_time: 0,
                    range_min: 0.1,
                    range_max: 10.0,
                    ranges: ranges,
                    intensities: []
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 200);

    // 5. Map (Static Occupancy Grid)
    const mapInterval = setInterval(() => {
        if (subscriptions.has('/map')) {
            const width = 50;
            const height = 50;
            const data = new Array(width * height).fill(0);

            // Draw a box in the middle
            for (let y = 10; y < 40; y++) {
                for (let x = 10; x < 40; x++) {
                    if (x === 10 || x === 39 || y === 10 || y === 39) {
                        data[y * width + x] = 100; // Occupied
                    } else {
                        data[y * width + x] = 0;   // Free
                    }
                }
            }

            const msg = {
                op: 'publish',
                topic: '/map',
                type: 'nav_msgs/OccupancyGrid',
                msg: {
                    header: {
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'map'
                    },
                    info: {
                        map_load_time: { sec: 0, nanosec: 0 },
                        resolution: 0.1,
                        width: width,
                        height: height,
                        origin: {
                            position: { x: -2.5, y: -2.5, z: 0 },
                            orientation: { x: 0, y: 0, z: 0, w: 1 }
                        }
                    },
                    data: data
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 2000);

    // 6. IMU Data — slow yaw rotation + gentle roll/pitch noise
    let imuYaw = 0;
    const imuInterval = setInterval(() => {
        if (subscriptions.has('/imu/data')) {
            imuYaw += 0.02; // ~1.1 deg/s rotation for demo

            const roll  = Math.sin(Date.now() / 4000) * 3.0;   // ±3° roll
            const pitch = Math.cos(Date.now() / 5000) * 2.0;   // ±2° pitch

            // Convert roll/pitch/yaw to quaternion
            const cr = Math.cos(roll  * Math.PI / 360);
            const sr = Math.sin(roll  * Math.PI / 360);
            const cp = Math.cos(pitch * Math.PI / 360);
            const sp = Math.sin(pitch * Math.PI / 360);
            const cy2 = Math.cos(imuYaw / 2);
            const sy2 = Math.sin(imuYaw / 2);

            const msg = {
                op: 'publish',
                topic: '/imu/data',
                type: 'sensor_msgs/Imu',
                msg: {
                    header: {
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'imu_link'
                    },
                    orientation: {
                        x: sr * cp * cy2 - cr * sp * sy2,
                        y: cr * sp * cy2 + sr * cp * sy2,
                        z: cr * cp * sy2 - sr * sp * cy2,
                        w: cr * cp * cy2 + sr * sp * sy2,
                    },
                    angular_velocity: { x: 0.01, y: 0.01, z: 0.02 },
                    linear_acceleration: { x: 0.05, y: 0.02, z: 9.81 }
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 100);

    // 7. Safety Status
    const safetyInterval = setInterval(() => {
        if (subscriptions.has('/orbibot/safety_status')) {
            const msg = {
                op: 'publish',
                topic: '/orbibot/safety_status',
                type: 'orbibot_msgs/SafetyStatus',
                msg: {
                    header: {
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'base_link'
                    },
                    emergency_stop: false,
                    low_battery: false,
                    hardware_fault: false,
                    velocity_limit: false,
                    temperature_limit: false,
                    motors_disabled: false,
                    cmd_timeout: false,
                    fault_code: 0
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 1000);

    // 8. Encoders — slowly incrementing counts (FL/BL/FR/BR = M1/M2/M3/M4)
    let encoderCounts = [0, 0, 0, 0];
    const encoderInterval = setInterval(() => {
        if (subscriptions.has('/orbibot/encoders')) {
            // Simulate gentle forward motion: all wheels increment at same rate
            const tick = 3 + Math.round(Math.random() * 2);
            encoderCounts = encoderCounts.map(c => c + tick);

            const msg = {
                op: 'publish',
                topic: '/orbibot/encoders',
                type: 'std_msgs/Int32MultiArray',
                msg: {
                    layout: { dim: [], data_offset: 0 },
                    data: encoderCounts
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 200);

    // 9. Odometry with gentle simulated motion (not just noise)
    // Override the basic odom interval with one that includes velocity
    let demoVx = 0;
    let demoVy = 0;
    let demoTime = 0;
    const motionInterval = setInterval(() => {
        if (subscriptions.has('/odometry/filtered')) {
            demoTime += 0.05;
            // Gentle figure-8-ish path
            demoVx = Math.sin(demoTime * 0.4) * 0.25;
            demoVy = Math.sin(demoTime * 0.2) * 0.10;
            x += demoVx * 0.05;
            y += demoVy * 0.05;

            const msg = {
                op: 'publish',
                topic: '/odometry/filtered',
                type: 'nav_msgs/Odometry',
                msg: {
                    header: {
                        stamp: { sec: Math.floor(Date.now() / 1000), nanosec: (Date.now() % 1000) * 1000000 },
                        frame_id: 'odom'
                    },
                    child_frame_id: 'base_footprint',
                    pose: {
                        pose: {
                            position: { x: x, y: y, z: 0 },
                            orientation: { x: 0, y: 0, z: Math.sin(imuYaw / 2), w: Math.cos(imuYaw / 2) }
                        },
                        covariance: new Array(36).fill(0)
                    },
                    twist: {
                        twist: {
                            linear:  { x: demoVx, y: demoVy, z: 0 },
                            angular: { x: 0, y: 0, z: 0.02 }
                        },
                        covariance: new Array(36).fill(0)
                    }
                }
            };
            ws.send(JSON.stringify(msg));
        }
    }, 50);

    ws.on('close', function close() {
        console.log('Client disconnected');
        clearInterval(odomInterval);
        clearInterval(batteryInterval);
        clearInterval(systemStatusInterval);
        clearInterval(scanInterval);
        clearInterval(mapInterval);
        clearInterval(imuInterval);
        clearInterval(safetyInterval);
        clearInterval(encoderInterval);
        clearInterval(motionInterval);
    });
});
