import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Circle, Clock, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Agent {
  id: string;
  name: string;
  role: "analyst" | "manager" | "architect" | "developer" | "qa";
  status: "idle" | "working" | "waiting" | "complete";
  currentTask?: string;
}

interface ActivityEvent {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
  timestamp: string;
}

const mockAgents: Agent[] = [
  {
    id: "1",
    name: "Sarah",
    role: "analyst",
    status: "idle",
  },
  {
    id: "2",
    name: "Mike",
    role: "manager",
    status: "working",
    currentTask: "Coordinating tasks",
  },
  {
    id: "3",
    name: "Alex",
    role: "architect",
    status: "complete",
  },
  {
    id: "4",
    name: "Jordan",
    role: "developer",
    status: "working",
    currentTask: "Building components",
  },
  {
    id: "5",
    name: "Casey",
    role: "qa",
    status: "waiting",
  },
];

const mockActivity: ActivityEvent[] = [
  {
    id: "1",
    type: "success",
    message: "Component 'UserDashboard' created successfully",
    timestamp: "2:45 PM",
  },
  {
    id: "2",
    type: "success",
    message: "All tests passed (12/12)",
    timestamp: "2:44 PM",
  },
  {
    id: "3",
    type: "info",
    message: "Installing dependency: axios@1.5.0",
    timestamp: "2:43 PM",
  },
  {
    id: "4",
    type: "success",
    message: "Database schema created",
    timestamp: "2:42 PM",
  },
  {
    id: "5",
    type: "info",
    message: "Architecture document completed",
    timestamp: "2:40 PM",
  },
];

const agentRoleNames = {
  analyst: "Analyst",
  manager: "Manager",
  architect: "Architect",
  developer: "Developer",
  qa: "QA",
};

const statusColors = {
  idle: "text-muted-foreground",
  working: "text-success",
  waiting: "text-warning",
  complete: "text-success",
};

const activityColors = {
  info: "text-info",
  success: "text-success",
  warning: "text-warning",
  error: "text-error",
};

const StatusIndicator = ({ status }: { status: Agent["status"] }) => {
  if (status === "complete") {
    return <CheckCircle2 className="w-4 h-4 text-success" />;
  } else if (status === "working") {
    return (
      <div className="relative">
        <Circle className="w-4 h-4 text-success" />
        <div className="absolute inset-0 w-4 h-4 border-2 border-success rounded-full animate-ping opacity-75"></div>
      </div>
    );
  } else if (status === "waiting") {
    return <Clock className="w-4 h-4 text-warning" />;
  } else {
    return <Circle className="w-4 h-4 text-muted-foreground" />;
  }
};

export const StatusPanel = () => {
  const overallProgress = 68;
  const timeElapsed = "15 minutes";
  const costSpent = "$2.34";

  return (
    <Card className="glass flex flex-col">
      <div className="p-2 border-b border-border">
        <h2 className="text-sm font-semibold">Status & Metrics</h2>
      </div>

      <ScrollArea className="flex-1 p-2">
        <div className="space-y-3">
          {/* Overall Progress */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold">Overall Progress</h3>
            <div className="flex flex-col items-center justify-center p-3 bg-muted/30 rounded-lg border border-border">
              <div className="relative w-16 h-16 mb-2">
                <svg className="transform -rotate-90 w-16 h-16">
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke="currentColor"
                    strokeWidth="6"
                    fill="none"
                    className="text-muted"
                  />
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke="currentColor"
                    strokeWidth="6"
                    fill="none"
                    strokeDasharray={`${(overallProgress / 100) * 175.9} 175.9`}
                    className="text-primary transition-all duration-300"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold">{overallProgress}%</span>
                </div>
              </div>
              <div className="text-center space-y-0.5">
                <p className="text-xs font-medium">Development</p>
                <p className="text-[10px] text-muted-foreground">
                  ~{timeElapsed} left
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {costSpent} spent
                </p>
              </div>
            </div>
          </div>

          {/* Active Agents */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold">Active Agents</h3>
            <div className="space-y-1.5">
              {mockAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center gap-2 p-1.5 rounded-lg bg-muted/30 border border-border"
                >
                  <StatusIndicator status={agent.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium">{agent.name}</span>
                      <span className="text-[10px] text-muted-foreground">
                        ({agentRoleNames[agent.role]})
                      </span>
                    </div>
                    {agent.currentTask && (
                      <p className="text-[10px] text-muted-foreground truncate">
                        {agent.currentTask}
                      </p>
                    )}
                  </div>
                  {agent.status === "complete" && (
                    <CheckCircle2 className="w-3 h-3 text-success flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Activity Log */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold">Activity Log</h3>
            <div className="space-y-1.5">
              {mockActivity.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-1.5 text-xs p-1.5 rounded-lg bg-muted/30 border border-border"
                >
                  <div
                    className={cn(
                      "w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0",
                      event.type === "success" && "bg-success",
                      event.type === "info" && "bg-info",
                      event.type === "warning" && "bg-warning",
                      event.type === "error" && "bg-error"
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <p className={cn("text-xs", activityColors[event.type])}>
                      {event.message}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {event.timestamp}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>
    </Card>
  );
};

