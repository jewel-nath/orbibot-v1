"""ROS 2 service calling, topic listing, and generic topic publishing."""

import importlib
import logging
import threading
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ServicesMixin:
    """Dynamic service calling, topic introspection, and generic publishing."""

    def list_topics(self) -> List[Dict[str, Any]]:
        """List all active ROS topics."""
        try:
            return [{'name': n, 'types': t} for n, t in self._node.get_topic_names_and_types()]
        except Exception as e:
            logger.error(f'Failed to list topics: {e}')
            return []

    def list_services(self) -> List[Dict[str, Any]]:
        """List all available ROS services."""
        try:
            return [{'name': n, 'types': t} for n, t in self._node.get_service_names_and_types()]
        except Exception as e:
            logger.error(f'Failed to list services: {e}')
            return []

    def call_service(
        self,
        service_name: str,
        service_type: str,
        request_dict: Dict[str, Any],
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Call a ROS service dynamically.

        Args:
            service_name: Full service name (e.g. '/map_server/load_map').
            service_type: Type string (e.g. 'nav2_msgs/srv/LoadMap').
            request_dict: Request fields as a dictionary.
            timeout: Seconds to wait for the service.
        """
        try:
            parts = service_type.split('/')
            if len(parts) == 3 and parts[1] == 'srv':
                module_name, _, srv_name = parts
            elif len(parts) == 2:
                module_name, srv_name = parts
            else:
                return {'success': False,
                        'error': f'Invalid service type format: {service_type}. Expected package/srv/ServiceName'}

            srv_module = importlib.import_module(f'{module_name}.srv')
            srv_class = getattr(srv_module, srv_name)
            srv_req_class = getattr(srv_module, f'{srv_name}_Request')

            if service_name not in self._service_clients:
                self._service_clients[service_name] = self._node.create_client(srv_class, service_name)
                logger.info(f'Created service client for {service_name}')

            client = self._service_clients[service_name]
            if not client.wait_for_service(timeout_sec=timeout):
                return {'success': False, 'error': f'Service {service_name} not available within {timeout}s'}

            request = srv_req_class()
            for key, value in request_dict.items():
                if hasattr(request, key):
                    setattr(request, key, value)

            future = client.call_async(request)
            done_event = threading.Event()
            future.add_done_callback(lambda _: done_event.set())

            if not done_event.wait(timeout=timeout):
                return {'success': False, 'error': f'Service call timed out after {timeout}s'}

            response = future.result()
            if response is None:
                return {'success': False, 'error': 'Service call returned None'}

            response_dict = {}
            for slot in response.__slots__:
                val = getattr(response, slot)
                if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                    response_dict[slot] = val
                else:
                    response_dict[slot] = str(val)

            return {'success': True, 'service': service_name, 'response': response_dict}

        except ImportError as e:
            logger.error(f'Failed to import service type {service_type}: {e}')
            return {'success': False, 'error': f'Cannot import service type {service_type}: {e}'}
        except Exception as e:
            logger.error(f'Service call failed: {e}')
            return {'success': False, 'error': str(e)}

    def publish_topic(
        self,
        topic: str,
        msg_type_str: str,
        data: Dict[str, Any],
        qos_depth: int = 10,
    ) -> Dict[str, Any]:
        """Publish a one-shot message to any ROS topic.

        Dynamically imports the message class and caches one publisher per topic.
        """
        try:
            parts = msg_type_str.replace('.', '/').split('/')
            if len(parts) == 3 and parts[1] == 'msg':
                pkg, _, cls_name = parts
            elif len(parts) == 2:
                pkg, cls_name = parts
            else:
                return {'success': False, 'error': f'Invalid msg_type format: {msg_type_str}'}

            mod = importlib.import_module(f'{pkg}.msg')
            msg_class = getattr(mod, cls_name)

            if topic not in self._topic_publishers:
                self._topic_publishers[topic] = self._node.create_publisher(msg_class, topic, qos_depth)
                logger.info(f'Created publisher for {topic} ({msg_type_str})')

            msg = msg_class()
            self._set_message_fields(msg, data)
            self._topic_publishers[topic].publish(msg)
            logger.info(f'Published to {topic}: {data}')
            return {'success': True, 'topic': topic, 'msg_type': msg_type_str}

        except ImportError as e:
            logger.error(f'Cannot import {msg_type_str}: {e}')
            return {'success': False, 'error': f'Cannot import {msg_type_str}: {e}'}
        except Exception as e:
            logger.error(f'publish_topic failed: {e}')
            return {'success': False, 'error': str(e)}
