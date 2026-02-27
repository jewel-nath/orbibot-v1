/**
 * Hook to subscribe to system status topic
 * Provides CPU, RAM, temperature, and disk usage metrics
 */

import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';

export interface SystemStatus {
    header: {
        stamp: {
            sec: number;
            nanosec: number;
        };
        frame_id: string;
    };
    battery_voltage: number;
    cpu_percent: number;
    ram_percent: number;
    cpu_temp: number;
    disk_percent: number;
    motors_enabled: boolean;
    emergency_stop: boolean;
    hardware_ok: boolean;
}

export function useSystemStatus(): SystemStatus | null {
    const { data } = useSubscriber<SystemStatus>({
        topic: ROS_TOPICS.systemStatusEnriched,
        messageType: ROS_MESSAGE_TYPES.systemStatus,
    });

    return data;
}
