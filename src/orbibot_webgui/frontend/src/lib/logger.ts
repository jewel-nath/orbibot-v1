/**
 * Namespaced console logger for debug visibility.
 *
 * Usage:
 *   const log = logger('useMotorControl');
 *   log.info('Motors enabled');
 *   log.error('Failed:', err);
 */

interface Logger {
  info: (message: string, ...args: unknown[]) => void;
  warn: (message: string, ...args: unknown[]) => void;
  error: (message: string, ...args: unknown[]) => void;
  debug: (message: string, ...args: unknown[]) => void;
}

export function logger(namespace: string): Logger {
  const prefix = `[${namespace}]`;
  return {
    info: (msg, ...args) => console.log(prefix, msg, ...args),
    warn: (msg, ...args) => console.warn(prefix, msg, ...args),
    error: (msg, ...args) => console.error(prefix, msg, ...args),
    debug: (msg, ...args) => console.debug(prefix, msg, ...args),
  };
}
