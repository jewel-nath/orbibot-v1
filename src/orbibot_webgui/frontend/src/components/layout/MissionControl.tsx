import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { WaypointManager } from '@/components/navigation/WaypointManager';
import { ExplorationPanel } from '@/components/navigation/ExplorationPanel';
import { ChatPanel } from '@/components/navigation/ChatPanel';
import { MecanumController } from '@/features/control/MecanumController';
import { Route, Search, Gamepad2, Bot } from 'lucide-react';

export function MissionControl() {
    return (
        <div className="h-full flex flex-col glass-panel overflow-hidden">
            <Tabs defaultValue="controller" className="flex-1 flex flex-col overflow-hidden">
                <div className="px-3 pt-2">
                    <TabsList className="grid w-full grid-cols-4">
                        <TabsTrigger value="controller" className="flex items-center gap-2">
                            <Gamepad2 className="w-4 h-4" />
                            <span>Control</span>
                        </TabsTrigger>
                        <TabsTrigger value="patrol" className="flex items-center gap-2">
                            <Route className="w-4 h-4" />
                            <span>Patrol</span>
                        </TabsTrigger>
                        <TabsTrigger value="explore" className="flex items-center gap-2">
                            <Search className="w-4 h-4" />
                            <span>Explore</span>
                        </TabsTrigger>
                        <TabsTrigger value="chat" className="flex items-center gap-2">
                            <Bot className="w-4 h-4" />
                            <span>Chat</span>
                        </TabsTrigger>
                    </TabsList>
                </div>

                <div className="flex-1 overflow-y-auto p-3">
                    <TabsContent value="patrol" className="m-0 h-full">
                        <WaypointManager className="h-full border-none shadow-none" />
                    </TabsContent>

                    <TabsContent value="explore" className="m-0 h-full">
                        <ExplorationPanel />
                    </TabsContent>

                    <TabsContent value="controller" className="m-0 h-full">
                        <MecanumController className="border-none shadow-none p-0" />
                    </TabsContent>

                    <TabsContent value="chat" className="m-0 h-full">
                        <ChatPanel />
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}

