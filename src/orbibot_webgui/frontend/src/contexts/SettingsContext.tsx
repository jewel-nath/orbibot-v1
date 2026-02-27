import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

/**
 * Interface for application settings
 */
export interface AppSettings {
    websocketUrl: string;
    webrtcUrl: string;
    maxLinearVelocity: number;
    maxAngularVelocity: number;
    scanTopic: string;
    mapTopic: string;
    odomTopic: string;
    imuTopic: string;
}

/**
 * Default settings
 */
const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
export const DEFAULT_SETTINGS: AppSettings = {
    websocketUrl: `ws://${host}:9090`,
    webrtcUrl: `http://${host}:8081`,
    maxLinearVelocity: 1.0,
    maxAngularVelocity: 2.0,
    scanTopic: '/scan',
    mapTopic: '/map',
    odomTopic: '/odom',
    imuTopic: '/imu/data',
};

const STORAGE_KEY = 'orbibot-settings';

interface SettingsContextType {
    settings: AppSettings;
    updateSettings: (updates: Partial<AppSettings>) => void;
    resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: ReactNode }) {
    const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
    const [isInitialized, setIsInitialized] = useState(false);

    // Load settings from localStorage on mount
    useEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                setSettings({ ...DEFAULT_SETTINGS, ...parsed });
            }
        } catch (error) {
            console.error('Failed to parse stored settings:', error);
        } finally {
            setIsInitialized(true);
        }
    }, []);

    // Save settings to localStorage whenever they change (after init)
    useEffect(() => {
        if (isInitialized) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        }
    }, [settings, isInitialized]);

    const updateSettings = (updates: Partial<AppSettings>) => {
        setSettings(prev => ({ ...prev, ...updates }));
    };

    const resetSettings = () => {
        setSettings(DEFAULT_SETTINGS);
    };

    return (
        <SettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
            {children}
        </SettingsContext.Provider>
    );
}

export function useSettings() {
    const context = useContext(SettingsContext);
    if (context === undefined) {
        throw new Error('useSettings must be used within a SettingsProvider');
    }
    return context;
}
