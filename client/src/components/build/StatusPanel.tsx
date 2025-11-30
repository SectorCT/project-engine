import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Circle, Clock, Loader2, AlertCircle, MessageSquare, Ticket, Code, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { Job, JobStep, Ticket as TicketType } from "@/lib/api";
import { calculateProgress, formatTimeAgo } from "@/lib/jobUtils";

interface StatusPanelProps {
  job?: Job;
  steps?: JobStep[];
  tickets?: TicketType[];
  messages?: any[];
}

function getAgentStatus(job: Job | undefined, agentName: string): "idle" | "working" | "waiting" | "complete" {
  if (!job) return "idle";
  
  if (job.status === "done" || job.status === "build_done") return "complete";
  if (job.status === "failed") {
    // For failed jobs, check if agent had any activity
    const agentSteps = job.steps?.filter(step => step.agent_name === agentName) || [];
    return agentSteps.length > 0 ? "complete" : "idle";
  }
  
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
  
  // Check job status to determine if agents are waiting
  const activeStatuses = ["building", "running", "planning", "ticketing", "tickets_ready"];
  if (activeStatuses.includes(job.status)) return "waiting";
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

const StatusIndicator = ({ status }: { status: "idle" | "working" | "waiting" | "complete" }) => {
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

export const StatusPanel = ({ job, steps = [], tickets = [], messages = [] }: StatusPanelProps) => {
  const overallProgress = job ? calculateProgress(job) : 0;
  const timeElapsed = job ? formatTimeAgo(job.created_at) : "0 minutes";
  const isFailed = job?.status === 'failed';
  
  // Calculate ticket metrics
  const workTickets = tickets.filter(t => t.type !== 'epic');
  const completedTickets = workTickets.filter(t => t.status === 'done' || t.status === 'completed').length;
  const inProgressTickets = workTickets.filter(t => t.status === 'in_progress').length;
  const todoTickets = workTickets.filter(t => t.status === 'todo' || !t.status || t.status === '').length;
  const ticketProgress = workTickets.length > 0 ? Math.round((completedTickets / workTickets.length) * 100) : 0;

  // Calculate message and step counts
  const messageCount = messages?.length || 0;
  const stepCount = steps?.length || 0;

  // Calculate time metrics
  const startTime = job ? new Date(job.created_at).getTime() : Date.now();
  const currentTime = Date.now();
  const elapsedMs = currentTime - startTime;
  const elapsedMinutes = Math.floor(elapsedMs / 60000);
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  const elapsedDays = Math.floor(elapsedHours / 24);
  
  const formattedElapsed = elapsedDays > 0 
    ? `${elapsedDays}d ${elapsedHours % 24}h`
    : elapsedHours > 0
    ? `${elapsedHours}h ${elapsedMinutes % 60}m`
    : `${elapsedMinutes}m`;

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

  // Create activity log from steps and messages
  const recentSteps = steps.slice(-5).reverse();
  const recentMessages = messages?.slice(-3).reverse() || [];
  const activity: Array<{
    id: string;
    type: "info" | "success" | "warning" | "error";
    message: string;
    timestamp: string;
  }> = [
    ...recentSteps.map((step) => ({
      id: step.id,
      type: "info" as const,
      message: `${step.agent_name}: ${step.message.substring(0, 60)}${step.message.length > 60 ? '...' : ''}`,
      timestamp: formatTimestamp(step.created_at),
    })),
    ...recentMessages.map((msg) => ({
      id: msg.id,
      type: (msg.role === 'system' ? "info" : msg.role === 'user' ? "success" : "info") as "info" | "success" | "warning" | "error",
      message: `${msg.sender || 'System'}: ${msg.content.substring(0, 60)}${msg.content.length > 60 ? '...' : ''}`,
      timestamp: formatTimestamp(msg.created_at),
    })),
  ].slice(0, 10);

  return (
    <Card className="glass flex flex-col h-full">
      <div className="p-2 border-b border-border flex-shrink-0">
        <h2 className="text-sm font-semibold">Status & Metrics</h2>
      </div>

      <ScrollArea className="flex-1 p-2 min-h-0">
        <div className="space-y-3">
          {/* Error Banner (if failed) */}
          {isFailed && job?.error_message && (
            <div className="p-2 bg-status-failed/10 border border-status-failed/30 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-status-failed flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-status-failed mb-1">Build Failed</p>
                  <p className="text-[10px] text-muted-foreground line-clamp-2">
                    {job.error_message}
                  </p>
                </div>
              </div>
            </div>
          )}

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
                    className={isFailed ? "text-status-failed/20" : "text-muted"}
                  />
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke="currentColor"
                    strokeWidth="6"
                    fill="none"
                    strokeDasharray={`${(overallProgress / 100) * 175.9} 175.9`}
                    className={cn(
                      "transition-all duration-300",
                      isFailed ? "text-status-failed" : "text-primary"
                    )}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className={cn(
                    "text-lg font-bold",
                    isFailed && "text-status-failed"
                  )}>
                    {overallProgress}%
                  </span>
                </div>
              </div>
              <div className="text-center space-y-0.5">
                <p className="text-xs font-medium">
                  {isFailed ? 'Failed' : job?.status || 'Initializing'}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {formattedElapsed} elapsed
                </p>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold">Quick Stats</h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 bg-muted/30 rounded-lg border border-border">
                <div className="flex items-center gap-1.5 mb-1">
                  <Ticket className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Tickets</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-sm font-bold">{completedTickets}</span>
                  <span className="text-[10px] text-muted-foreground">/{workTickets.length || 0}</span>
                </div>
                {workTickets.length > 0 && (
                  <Progress value={ticketProgress} className="h-1 mt-1" />
                )}
              </div>
              <div className="p-2 bg-muted/30 rounded-lg border border-border">
                <div className="flex items-center gap-1.5 mb-1">
                  <MessageSquare className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Messages</span>
                </div>
                <span className="text-sm font-bold">{messageCount}</span>
              </div>
              <div className="p-2 bg-muted/30 rounded-lg border border-border">
                <div className="flex items-center gap-1.5 mb-1">
                  <Code className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Steps</span>
                </div>
                <span className="text-sm font-bold">{stepCount}</span>
              </div>
              <div className="p-2 bg-muted/30 rounded-lg border border-border">
                <div className="flex items-center gap-1.5 mb-1">
                  <TrendingUp className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Active</span>
                </div>
                <span className="text-sm font-bold">{inProgressTickets}</span>
              </div>
            </div>
          </div>

          {/* Ticket Status Breakdown */}
          {workTickets.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold">Ticket Status</h3>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between p-1.5 rounded-lg bg-muted/30 border border-border">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3 h-3 text-success" />
                    <span className="text-xs">Completed</span>
                  </div>
                  <span className="text-xs font-semibold">{completedTickets}</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded-lg bg-muted/30 border border-border">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-3 h-3 text-warning animate-spin" />
                    <span className="text-xs">In Progress</span>
                  </div>
                  <span className="text-xs font-semibold">{inProgressTickets}</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded-lg bg-muted/30 border border-border">
                  <div className="flex items-center gap-2">
                    <Circle className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs">To Do</span>
                  </div>
                  <span className="text-xs font-semibold">{todoTickets}</span>
                </div>
              </div>
            </div>
          )}

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

