/**
 * useMotorControl - Hook for motor control service
 */

import { useState, useEffect, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { logger } from '@/lib/logger';

const log = logger('useMotorControl');

interface MotorControlState {
  serviceAvailable: boolean;
  motorsEnabled: boolean;
  isChanging: boolean;
}

interface MotorControlActions {
  enableMotors: () => void;
  disableMotors: () => void;
  toggleMotors: () => void;
}

export function useMotorControl(): MotorControlState & MotorControlActions {
  const { ros, connectionState } = useRosContext();
  const [serviceAvailable, setServiceAvailable] = useState(false);
  const [motorsEnabled, setMotorsEnabled] = useState(false);
  const [isChanging, setIsChanging] = useState(false);

  // Check if motor control service is available
  useEffect(() => {
    if (!ros || connectionState !== 'connected') {
      setServiceAvailable(false);
      return;
    }

    // Check for service availability
    ros.getServices((services: string[]) => {
      const hasService = services.includes('/orbibot/set_motor_enable');
      setServiceAvailable(hasService);
      if (hasService) {
        log.info('/orbibot/set_motor_enable service found');
      }
    }, (error: string) => {
      log.error('Failed to get services:', error);
      setServiceAvailable(false);
    });

    // Subscribe to system status for motor state
    const statusTopic = new ROSLIB.Topic({
      ros,
      name: '/orbibot/system_status',
      messageType: 'orbibot_msgs/SystemStatus',
    });

    const handleStatus = (msg: ROSLIB.Message) => {
      const status = msg as unknown as { motors_enabled?: boolean };
      if (typeof status.motors_enabled === 'boolean') {
        setMotorsEnabled(status.motors_enabled);
      }
    };

    statusTopic.subscribe(handleStatus);
    log.info('Subscribed to /orbibot/system_status');

    return () => {
      statusTopic.unsubscribe();
    };
  }, [ros, connectionState]);

  const callMotorService = useCallback((enable: boolean) => {
    if (!ros || !serviceAvailable) return;

    setIsChanging(true);

    const service = new ROSLIB.Service({
      ros,
      name: '/orbibot/set_motor_enable',
      serviceType: 'orbibot_msgs/srv/SetMotorEnable',
    });

    const request = new ROSLIB.ServiceRequest({ enable });

    service.callService(request, (response: { success: boolean; message: string }) => {
      setIsChanging(false);
      if (response.success) {
        setMotorsEnabled(enable);
        log.info(`Motor control service initialized`);
      }
    }, (error: string) => {
      setIsChanging(false);
      log.error(`Failed to ${enable ? 'enable' : 'disable'} motors:`, error);
    });
  }, [ros, serviceAvailable]);

  const enableMotors = useCallback(() => {
    callMotorService(true);
  }, [callMotorService]);

  const disableMotors = useCallback(() => {
    callMotorService(false);
  }, [callMotorService]);

  const toggleMotors = useCallback(() => {
    callMotorService(!motorsEnabled);
  }, [callMotorService, motorsEnabled]);

  return {
    serviceAvailable,
    motorsEnabled,
    isChanging,
    enableMotors,
    disableMotors,
    toggleMotors,
  };
}