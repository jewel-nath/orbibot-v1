#!/usr/bin/env python3
"""
OrbiBot WebRTC video streaming server using aiortc.
Subscribes to ROS2 camera image topic and streams via WebRTC with low latency.
"""

import asyncio
import json
import logging
import traceback
import time
import threading
from typing import Optional, Set

from aiohttp import web
import aiohttp_cors
from av import VideoFrame
import cv2
import numpy as np

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

# Handle cv_bridge import with graceful error handling
try:
    from cv_bridge import CvBridge
    CV_BRIDGE_AVAILABLE = True
except ImportError:
    CV_BRIDGE_AVAILABLE = False
    CvBridge = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrameBuffer:
    """
    Thread-safe lock-free frame buffer for efficient frame sharing.
    Uses atomic reference swap pattern to minimize contention.
    """
    
    def __init__(self):
        self._frame: Optional[np.ndarray] = None
        self._timestamp: float = 0.0
        self._lock = threading.Lock()
    
    def update(self, frame: np.ndarray) -> None:
        """Update frame atomically."""
        with self._lock:
            self._frame = frame
            self._timestamp = time.time()
    
    def get(self) -> tuple[Optional[np.ndarray], float]:
        """Get current frame and timestamp."""
        with self._lock:
            if self._frame is not None:
                return self._frame.copy(), self._timestamp
            return None, 0.0
    
    def is_fresh(self, max_age: float = 2.0) -> bool:
        """Check if frame is available and fresh."""
        with self._lock:
            if self._frame is None:
                return False
            return (time.time() - self._timestamp) <= max_age


class OrbiBotVideoTrack(VideoStreamTrack):
    """
    Video track that gets frames from OrbiBot's camera feed.
    Each peer connection gets its own track instance.
    """

    def __init__(self, frame_buffer: FrameBuffer, width: int = 640, height: int = 480):
        super().__init__()
        self.frame_buffer = frame_buffer
        self.width = width
        self.height = height
        self._frame_send_count = 0

    async def recv(self) -> VideoFrame:
        """Get next video frame for WebRTC."""
        pts, time_base = await self.next_timestamp()

        # Get frame from buffer (non-blocking, thread-safe)
        frame, frame_time = self.frame_buffer.get()
        now = time.time()
        
        # Check if feed is still valid (not too old)
        if frame is None or (now - frame_time > 2.0):
            if self._frame_send_count > 0:
                logger.warning(f"Track {id(self)}: Feed lost (last frame {now - frame_time:.1f}s ago). Closing.")
            raise Exception("Camera feed offline")
        
        self._frame_send_count += 1
        if self._frame_send_count == 1 or self._frame_send_count % 30 == 0:
            logger.info(f"Track {id(self)}: Sending frame {self._frame_send_count}")

        # Convert BGR to RGB (OpenCV uses BGR, WebRTC expects RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame


class OrbiBotWebRTCServer(Node):
    """
    ROS2 node that runs WebRTC signaling server and streams OrbiBot camera feed.
    """

    def __init__(self):
        super().__init__('orbibot_webrtc_server')

        # Check cv_bridge availability
        if not CV_BRIDGE_AVAILABLE:
            self.get_logger().error(
                "cv_bridge not available. Install with: "
                "sudo apt install ros-$ROS_DISTRO-cv-bridge"
            )
            raise RuntimeError("cv_bridge is required but not installed")

        # Parameters
        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('port', 8081)
        self.declare_parameter('image_width', 640)
        self.declare_parameter('image_height', 480)

        self.image_topic = self.get_parameter('image_topic').value
        self.port = self.get_parameter('port').value
        self.image_width = self.get_parameter('image_width').value
        self.image_height = self.get_parameter('image_height').value

        # CV Bridge for ROS Image conversion
        self.bridge = CvBridge()

        # Thread-safe frame buffer (replaces asyncio.Lock pattern)
        self.frame_buffer = FrameBuffer()

        # Subscribe to camera image topic with QoS profile for sensor data
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )
        
        self.subscription = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            qos_profile
        )

        # Active peer connections
        self.pcs: Set[RTCPeerConnection] = set()
        self._pcs_lock = threading.Lock()

        # Frame counter for debug logging
        self.frame_count = 0

        self.get_logger().info(f'OrbiBot WebRTC server starting on port {self.port}')
        self.get_logger().info(f'Subscribing to camera topic: {self.image_topic}')

    def image_callback(self, msg: Image) -> None:
        """Handle incoming ROS2 camera images."""
        try:
            # Convert ROS Image message to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # Resize if needed (optional, for bandwidth optimization)
            if cv_image.shape[1] != self.image_width or cv_image.shape[0] != self.image_height:
                cv_image = cv2.resize(cv_image, (self.image_width, self.image_height))

            # Store frame in thread-safe buffer (synchronous, no async task overhead)
            self.frame_buffer.update(cv_image)

            # Log first frame and every 30th frame
            self.frame_count += 1
            if self.frame_count == 1 or self.frame_count % 30 == 0:
                self.get_logger().info(f'Received frame {self.frame_count}, size: {cv_image.shape}')

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')

    def add_peer_connection(self, pc: RTCPeerConnection) -> None:
        """Thread-safe add peer connection."""
        with self._pcs_lock:
            self.pcs.add(pc)

    def remove_peer_connection(self, pc: RTCPeerConnection) -> None:
        """Thread-safe remove peer connection."""
        with self._pcs_lock:
            self.pcs.discard(pc)

    def get_peer_connections(self) -> Set[RTCPeerConnection]:
        """Get copy of peer connections set."""
        with self._pcs_lock:
            return self.pcs.copy()

    def get_active_connection_count(self) -> int:
        """Get number of active peer connections."""
        with self._pcs_lock:
            return len(self.pcs)


class WebRTCApp:
    """
    Encapsulates the WebRTC application state and handlers.
    Replaces global variable pattern with proper dependency injection.
    """

    def __init__(self, node: OrbiBotWebRTCServer):
        self.node = node
        self.app = web.Application()
        self._setup_routes()
        self._setup_cors()

    def _setup_cors(self) -> None:
        """Configure CORS for all origins."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods=["GET", "POST", "HEAD", "OPTIONS"]
            )
        })

        # Enable CORS on all routes
        for route in list(self.app.router.routes()):
            cors.add(route)

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.health)
        self.app.router.add_post("/offer", self.offer)
        self.app.on_shutdown.append(self.on_shutdown)

    async def health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        status_data = {
            "status": "ok",
            "service": "orbibot-webrtc-server",
            "active_connections": self.node.get_active_connection_count(),
            "frames_received": self.node.frame_count,
            "camera_fresh": self.node.frame_buffer.is_fresh()
        }
        return web.Response(
            content_type="application/json",
            text=json.dumps(status_data)
        )

    async def offer(self, request: web.Request) -> web.Response:
        """Handle WebRTC offer from client."""
        try:
            # Parse SDP offer from client
            params = await request.json()

            if "sdp" not in params or "type" not in params:
                return web.Response(
                    status=400,
                    content_type="application/json",
                    text=json.dumps({"error": "Missing 'sdp' or 'type' in request"})
                )

            logger.info(f"Received WebRTC offer from client, type: {params['type']}")

            try:
                offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            except Exception as e:
                return web.Response(
                    status=400,
                    content_type="application/json",
                    text=json.dumps({"error": f"Invalid SDP: {str(e)}"})
                )

            # Verify camera feed is active before accepting offer
            if not self.node.frame_buffer.is_fresh(max_age=3.0):
                logger.warning("Rejecting offer: Camera feed offline")
                return web.Response(
                    status=503,
                    content_type="application/json",
                    text=json.dumps({"error": "Camera feed offline"})
                )

            # Create peer connection with STUN servers for NAT traversal
            ice_servers = [
                RTCIceServer(urls="stun:stun.l.google.com:19302"),
                RTCIceServer(urls="stun:stun1.l.google.com:19302"),
            ]
            configuration = RTCConfiguration(iceServers=ice_servers)
            pc = RTCPeerConnection(configuration=configuration)
            self.node.add_peer_connection(pc)

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Peer connection state: {pc.connectionState}")
                if pc.connectionState in ("failed", "closed"):
                    await pc.close()
                    self.node.remove_peer_connection(pc)

            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state: {pc.iceConnectionState}")

            # Set remote description (client's offer)
            logger.info("Setting remote description...")
            await pc.setRemoteDescription(offer)
            logger.info("Remote description set successfully")

            # Create and add video track for this peer connection
            video_track = OrbiBotVideoTrack(
                frame_buffer=self.node.frame_buffer,
                width=self.node.image_width,
                height=self.node.image_height
            )
            pc.addTrack(video_track)
            logger.info(f"Added video track (id={id(video_track)}) to peer connection")

            # Create answer
            logger.info("Creating SDP answer...")
            answer = await pc.createAnswer()
            logger.info("Setting local description...")
            await pc.setLocalDescription(answer)
            logger.info("Local description set successfully")

            # Return SDP answer to client
            response_data = {
                "sdp": pc.localDescription.sdp,
                "type": str(pc.localDescription.type)
            }

            logger.info(f"Sending SDP answer back to client, type: {response_data['type']}")

            return web.Response(
                content_type="application/json",
                text=json.dumps(response_data)
            )

        except json.JSONDecodeError:
            return web.Response(
                status=400,
                content_type="application/json",
                text=json.dumps({"error": "Invalid JSON"})
            )
        except Exception as e:
            logger.error(f"Error handling WebRTC offer: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            # Clean up peer connection on error
            if 'pc' in locals():
                self.node.remove_peer_connection(pc)
                await pc.close()

            return web.Response(
                status=500,
                content_type="application/json",
                text=json.dumps({"error": str(e)})
            )

    async def on_shutdown(self, _app: web.Application) -> None:
        """Close all peer connections on shutdown."""
        logger.info("Shutting down, closing all peer connections...")
        pcs = self.node.get_peer_connections()
        coros = [pc.close() for pc in pcs]
        await asyncio.gather(*coros, return_exceptions=True)
        self.node.pcs.clear()


def main(args=None):
    """Main entry point."""
    # Initialize ROS2
    rclpy.init(args=args)
    
    try:
        node = OrbiBotWebRTCServer()
    except RuntimeError as e:
        logger.error(f"Failed to initialize WebRTC server: {e}")
        rclpy.shutdown()
        return 1

    # Create WebRTC application with proper dependency injection
    webrtc_app = WebRTCApp(node)

    # Run both ROS2 node and web server
    async def run_all():
        # Start HTTP server
        runner = web.AppRunner(webrtc_app.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", node.port)
        await site.start()

        logger.info(f"OrbiBot WebRTC server running on http://0.0.0.0:{node.port}")
        logger.info(f"Access health check at: http://localhost:{node.port}/")
        logger.info(f"WebRTC signaling endpoint: POST http://localhost:{node.port}/offer")

        # Spin ROS2 node while server is running
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            await asyncio.sleep(0.01)

    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        node.destroy_node()
        rclpy.shutdown()
        logger.info("Shutdown complete")
    
    return 0


if __name__ == '__main__':
    exit(main())