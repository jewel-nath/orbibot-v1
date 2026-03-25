"""ROS 2 action client management — send goals, track status, cancel."""

import importlib
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient

logger = logging.getLogger(__name__)


class ActionsMixin:
    """Dynamic action client creation, goal sending, and tracking."""

    def list_actions(self) -> List[Dict[str, Any]]:
        """List available action servers."""
        try:
            return [{'name': n, 'type': 'unknown'} for n in self._node.get_action_names()]
        except Exception as e:
            logger.error(f'Failed to list actions: {e}')
            return []

    def get_action_status(self, action_name: str) -> Dict[str, Any]:
        """Get status of an action server."""
        status_topic = f'{action_name}/_action/status'
        try:
            msg = self.wait_for_message(GoalStatus, status_topic, timeout=2.0)
            if msg is None:
                return {'action_name': action_name, 'active_goals': [], 'goal_count': 0,
                        'note': 'No status message received'}
            status_map = {
                GoalStatus.STATUS_UNKNOWN: 'UNKNOWN',
                GoalStatus.STATUS_ACCEPTED: 'ACCEPTED',
                GoalStatus.STATUS_EXECUTING: 'EXECUTING',
                GoalStatus.STATUS_CANCELING: 'CANCELING',
                GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
                GoalStatus.STATUS_CANCELED: 'CANCELED',
                GoalStatus.STATUS_ABORTED: 'ABORTED',
            }
            return {
                'action_name': action_name,
                'status_code': msg.status,
                'status_text': status_map.get(msg.status, 'UNKNOWN'),
                'goal_id': str(msg.goal_info.goal_id.uuid) if hasattr(msg, 'goal_info') else 'unknown',
            }
        except Exception as e:
            logger.error(f'Failed to get action status: {e}')
            return {'action_name': action_name, 'error': str(e)}

    def send_action_goal(
        self,
        action_name: str,
        action_type: str,
        goal_dict: Dict[str, Any],
        feedback_callback: Optional[Callable] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Send an action goal. Returns immediately with goal_id for tracking."""
        try:
            parts = action_type.split('/')
            if len(parts) == 3 and parts[1] == 'action':
                module_name, _, act_name = parts
            elif len(parts) == 2:
                module_name, act_name = parts
            else:
                return {'success': False,
                        'error': f'Invalid action type format: {action_type}. '
                                 'Expected package/action/ActionName'}

            act_module = importlib.import_module(f'{module_name}.action')
            act_class = getattr(act_module, act_name)
            goal_class = getattr(act_module, f'{act_name}_Goal')

            if action_name not in self._action_clients:
                self._action_clients[action_name] = ActionClient(self._node, act_class, action_name)
                logger.info(f'Created action client for {action_name}')

            client = self._action_clients[action_name]
            if not client.wait_for_server(timeout_sec=5.0):
                return {'success': False, 'error': f'Action server {action_name} not available'}

            goal_msg = goal_class()
            self._set_message_fields(goal_msg, goal_dict)

            goal_id = f'goal_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}'
            self._active_goals[goal_id] = {
                'action_name': action_name,
                'action_type': action_type,
                'status': 'PENDING',
                'start_time': time.time(),
                'feedback': [],
            }

            send_future = client.send_goal_async(
                goal_msg,
                feedback_callback=lambda fb: self._on_feedback(goal_id, fb, feedback_callback),
            )
            send_future.add_done_callback(lambda f: self._on_goal_response(goal_id, f))

            start = time.time()
            while time.time() - start < timeout:
                status = self._active_goals[goal_id]['status']
                if status in ('ACCEPTED', 'EXECUTING', 'SUCCEEDED', 'ABORTED', 'CANCELED'):
                    break
                rclpy.spin_once(self._node, timeout_sec=0.1)

            return {
                'success': True,
                'goal_id': goal_id,
                'action_name': action_name,
                'action_type': action_type,
                'status': self._active_goals.get(goal_id, {}).get('status', 'UNKNOWN'),
                'note': 'Goal sent. Use get_action_result to check completion.',
            }

        except ImportError as e:
            logger.error(f'Failed to import action type {action_type}: {e}')
            return {'success': False, 'error': f'Cannot import action type {action_type}: {e}'}
        except Exception as e:
            logger.error(f'Action goal failed: {e}')
            return {'success': False, 'error': str(e)}

    def cancel_action_goal(self, goal_id: str) -> Dict[str, Any]:
        """Cancel an active action goal."""
        if goal_id not in self._active_goals:
            return {'success': False, 'error': f'Goal {goal_id} not found'}

        goal_info = self._active_goals[goal_id]
        client = self._action_clients.get(goal_info['action_name'])
        if not client:
            return {'success': False, 'error': f'Action client for {goal_info["action_name"]} not found'}

        try:
            client.cancel_goal_async(goal_info.get('goal_handle'))
            rclpy.spin_once(self._node, timeout_sec=1.0)
            goal_info['status'] = 'CANCELING'
            return {'success': True, 'goal_id': goal_id, 'status': 'CANCELING'}
        except Exception as e:
            logger.error(f'Cancel goal failed: {e}')
            return {'success': False, 'error': str(e)}

    def get_action_result(self, goal_id: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Get result of an action goal (polls until done or timeout)."""
        if goal_id not in self._active_goals:
            return {'success': False, 'error': f'Goal {goal_id} not found'}

        goal_info = self._active_goals[goal_id]
        start = time.time()
        while time.time() - start < timeout:
            if goal_info.get('status') in ('SUCCEEDED', 'ABORTED', 'CANCELED'):
                break
            rclpy.spin_once(self._node, timeout_sec=0.1)

        result = {
            'success': True,
            'goal_id': goal_id,
            'action_name': goal_info['action_name'],
            'action_type': goal_info['action_type'],
            'status': goal_info.get('status', 'UNKNOWN'),
            'elapsed_time': time.time() - goal_info.get('start_time', 0),
            'feedback_count': len(goal_info.get('feedback', [])),
        }
        if 'result' in goal_info:
            result['result'] = goal_info['result']
        return result

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get all currently active goals."""
        return [
            {
                'goal_id': gid,
                'action_name': info['action_name'],
                'action_type': info['action_type'],
                'status': info['status'],
                'elapsed_time': time.time() - info.get('start_time', 0),
            }
            for gid, info in self._active_goals.items()
            if info['status'] in ('PENDING', 'ACCEPTED', 'EXECUTING', 'CANCELING')
        ]

    # -- Internal callbacks --

    def _on_goal_response(self, goal_id: str, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            logger.warning(f'Goal {goal_id} was rejected')
            if goal_id in self._active_goals:
                self._active_goals[goal_id]['status'] = 'REJECTED'
            return

        logger.info(f'Goal {goal_id} accepted')
        if goal_id in self._active_goals:
            self._active_goals[goal_id]['status'] = 'ACCEPTED'
            self._active_goals[goal_id]['goal_handle'] = goal_handle

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(lambda f: self._on_result(goal_id, f))

    def _on_result(self, goal_id: str, future):
        try:
            result = future.result()
            if goal_id in self._active_goals:
                self._active_goals[goal_id]['status'] = 'SUCCEEDED'
                result_msg = result.result
                result_dict = {}
                for slot in result_msg.__slots__:
                    val = getattr(result_msg, slot)
                    result_dict[slot] = val if isinstance(val, (str, int, float, bool, list, dict, type(None))) else str(val)
                self._active_goals[goal_id]['result'] = result_dict
        except Exception as e:
            logger.error(f'Goal {goal_id} failed: {e}')
            if goal_id in self._active_goals:
                self._active_goals[goal_id]['status'] = 'ABORTED'
                self._active_goals[goal_id]['error'] = str(e)

    def _on_feedback(self, goal_id: str, feedback_msg, user_callback=None):
        if goal_id in self._active_goals:
            self._active_goals[goal_id]['status'] = 'EXECUTING'
            fb_msg = feedback_msg.feedback
            feedback_dict = {}
            for slot in fb_msg.__slots__:
                val = getattr(fb_msg, slot)
                feedback_dict[slot] = val if isinstance(val, (str, int, float, bool, list, dict, type(None))) else str(val)
            self._active_goals[goal_id]['feedback'].append({'timestamp': time.time(), 'data': feedback_dict})
            if user_callback:
                try:
                    user_callback(feedback_dict)
                except Exception as e:
                    logger.error(f'Feedback callback error: {e}')
