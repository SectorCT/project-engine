import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Circle, Clock, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Job, JobStep } from "@/lib/api";
import { calculateProgress, formatTimeAgo } from "@/lib/jobUtils";

interface StatusPanelProps {
  job?: Job;
  steps?: JobStep[];
}

function getAgentStatus(job: Job | undefined, agentName: string): "idle" | "working" | "waiting" | "complete" {
  if (!job) return "idle";
  
  if (job.status === "done") return "complete";
  if (job.status === "failed") return "idle";
  
  // Check if this agent has recent steps
  const recentSteps = job.steps?.filter(step => step.agent_name === agentName) || [];
  if (recentSteps.length > 0) {
    const lastStep = recentSteps[recentSteps.length - 1];
    const stepTime = new Date(lastStep.created_at).getTime();
    const now = Date.now();
    const fiveMinutesAgo = now - 5 * 60 * 1000;
    
    if (stepTime > fiveMinutesAgo) {
      return "working";
    }
    return "complete";
  }
  
  if (job.status === "running") return "waiting";
  return "idle";
}

function formatTimestamp(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

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

export const StatusPanel = ({ job, steps = [] }: StatusPanelProps) => {
  const overallProgress = job ? calculateProgress(job) : 0;
  const timeElapsed = job ? formatTimeAgo(job.created_at) : "0 minutes";
  const costSpent = "$0.00"; // TODO: Calculate from actual usage

  // Extract unique agents from steps
  const agentNames = Array.from(new Set(steps.map(step => step.agent_name)));
  const agents = agentNames.map((name, idx) => ({
    id: `agent-${idx}`,
    name,
    role: name.toLowerCase().includes("ceo") ? "manager" as const :
          name.toLowerCase().includes("cto") ? "architect" as const :
          name.toLowerCase().includes("client") ? "analyst" as const :
          name.toLowerCase().includes("secretary") ? "qa" as const :
          "developer" as const,
    status: getAgentStatus(job, name),
    currentTask: steps.find(s => s.agent_name === name)?.message.substring(0, 50) + "...",
  }));

  // Create activity log from steps
  const activity = steps.slice(-10).reverse().map((step, idx) => ({
    id: step.id,
    type: "info" as const,
    message: `${step.agent_name}: ${step.message.substring(0, 60)}${step.message.length > 60 ? '...' : ''}`,
    timestamp: formatTimestamp(step.created_at),
  }));

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
              {agents.length === 0 ? (
                <div className="text-center text-xs text-muted-foreground py-4">
                  No active agents
                </div>
              ) : (
                agents.map((agent) => (
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
                ))
              )}
            </div>
          </div>

          {/* Activity Log */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold">Activity Log</h3>
            <div className="space-y-1.5">
              {activity.length === 0 ? (
                <div className="text-center text-xs text-muted-foreground py-4">
                  No activity yet
                </div>
              ) : (
                activity.map((event) => (
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
                ))
              )}
            </div>
          </div>
        </div>
      </ScrollArea>
    </Card>
  );
};

