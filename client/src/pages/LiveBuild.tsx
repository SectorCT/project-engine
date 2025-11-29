import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AgentPanel } from "@/components/build/AgentPanel";
import { TabbedViewPanel } from "@/components/build/TabbedViewPanel";
import { ArchitecturePanel } from "@/components/build/ArchitecturePanel";
import { StatusPanel } from "@/components/build/StatusPanel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Pause,
  Play,
  Square,
  Download,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api, JobMessage, JobStep } from "@/lib/api";
import { useWebSocket, WebSocketMessage } from "@/hooks/useWebSocket";
import { mapServerStatusToClient, formatTimeAgo, ClientJobStatus } from "@/lib/jobUtils";
import { toast } from "sonner";

interface Tab {
  id: string;
  type: "preview" | "code";
  label: string;
  filePath?: string;
  content?: string;
  closable: boolean;
}

export default function LiveBuild() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isPaused, setIsPaused] = useState(false);
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">(
    "desktop"
  );
  const [tabs, setTabs] = useState<Tab[]>([
    {
      id: "preview",
      type: "preview",
      label: "Live Preview",
      closable: false,
    },
  ]);
  const [activeTabId, setActiveTabId] = useState<string>("preview");
  const [messages, setMessages] = useState<JobMessage[]>([]);
  const [steps, setSteps] = useState<JobStep[]>([]);
  const [appSpec, setAppSpec] = useState<any>(null);

  // Fetch job data
  const { data: job, isLoading, error, refetch } = useQuery({
    queryKey: ['job', id],
    queryFn: () => api.getJob(id!),
    enabled: !!id,
  });

  // Fetch app data when job is done
  const { data: app } = useQuery({
    queryKey: ['app', id],
    queryFn: () => api.getAppByJob(id!),
    enabled: !!id && job?.status === 'done',
  });

  // Update app spec when app data changes
  useEffect(() => {
    if (app?.spec) {
      setAppSpec(app.spec);
      // Add app spec tab if it doesn't exist
      setTabs(prev => {
        const specTabExists = prev.find(tab => tab.id === 'app-spec');
        if (!specTabExists) {
          return [...prev, {
            id: 'app-spec',
            type: 'code' as const,
            label: 'App Spec',
            content: JSON.stringify(app.spec, null, 2),
            closable: true,
          }];
        }
        return prev;
      });
    }
  }, [app]);

  // Connect WebSocket
  const { isConnected, sendMessage } = useWebSocket({
    jobId: id || '',
    enabled: !!id && !isPaused,
    onMessage: (message: WebSocketMessage) => {
      handleWebSocketMessage(message);
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
  });

  // Load initial messages
  useEffect(() => {
    if (id) {
      api.getJobMessages(id)
        .then((msgs) => setMessages(msgs))
        .catch((err) => console.error('Failed to load messages:', err));
    }
  }, [id]);

  // Update messages and steps when job data changes
  useEffect(() => {
    if (job) {
      if (job.messages) {
        setMessages(job.messages);
      }
      if (job.steps) {
        setSteps(job.steps);
      }
    }
  }, [job]);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.kind) {
      case 'chat':
        // Add new message to the list
        if (message.role && message.content) {
          const newMessage: JobMessage = {
            id: `temp-${Date.now()}`,
            role: message.role,
            sender: message.sender || '',
            content: message.content,
            metadata: message.metadata || {},
            created_at: message.timestamp || new Date().toISOString(),
          };
          setMessages((prev) => [...prev, newMessage]);
        }
        // Refetch job to get the persisted message
        refetch();
        break;
      case 'status':
        // Refetch job to get updated status
        refetch();
        break;
      case 'step':
        // Add new step
        if (message.agent && message.message) {
          const newStep: JobStep = {
            id: `temp-${Date.now()}`,
            agent_name: message.agent,
            message: message.message,
            order: message.order || steps.length + 1,
            created_at: message.timestamp || new Date().toISOString(),
          };
          setSteps((prev) => [...prev, newStep]);
        }
        // Refetch job to get the persisted step
        refetch();
        break;
      case 'app':
        // Job is complete, update app spec
        if (message.spec) {
          setAppSpec(message.spec);
          // Add app spec tab if it doesn't exist
          setTabs(prev => {
            const specTabExists = prev.find(tab => tab.id === 'app-spec');
            if (!specTabExists) {
              return [...prev, {
                id: 'app-spec',
                type: 'code' as const,
                label: 'App Spec',
                content: JSON.stringify(message.spec, null, 2),
                closable: true,
              }];
            }
            return prev;
          });
        }
        refetch();
        toast.success('Project completed!');
        break;
      case 'error':
        toast.error(message.message || 'An error occurred');
        break;
    }
  };

  const handleSendMessage = (content: string) => {
    if (isConnected && sendMessage) {
      sendMessage({ kind: 'chat', content });
    } else {
      toast.error('WebSocket not connected');
    }
  };

  const handleFileClick = (filePath: string, fileName: string) => {
    // Check if tab already exists
    const existingTab = tabs.find((tab) => tab.filePath === filePath);
    if (existingTab) {
      setActiveTabId(existingTab.id);
      return;
    }

    // Create new tab
    const newTab: Tab = {
      id: `code-${Date.now()}`,
      type: "code",
      label: fileName,
      filePath: filePath,
      closable: true,
    };

    setTabs([...tabs, newTab]);
    setActiveTabId(newTab.id);
  };

  const handleTabClose = (tabId: string) => {
    if (tabId === "preview") return; // Can't close preview tab

    const newTabs = tabs.filter((tab) => tab.id !== tabId);
    setTabs(newTabs);

    // If closed tab was active, switch to preview
    if (activeTabId === tabId) {
      setActiveTabId("preview");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-destructive mb-4">Failed to load project</p>
          <Button onClick={() => navigate("/dashboard")}>Go to Dashboard</Button>
        </div>
      </div>
    );
  }

  const projectName = job.initial_prompt.substring(0, 50) + (job.initial_prompt.length > 50 ? '...' : '');
  const status = mapServerStatusToClient(job.status);
  const timeElapsed = formatTimeAgo(job.created_at);
  const canSendMessages = job.status === 'collecting';

  const statusColors = {
    planning: "bg-status-planning/10 text-status-planning border-status-planning/20",
    building: "bg-status-building/10 text-status-building border-status-building/20",
    testing: "bg-status-testing/10 text-status-testing border-status-testing/20",
    complete: "bg-status-complete/10 text-status-complete border-status-complete/20",
    failed: "bg-status-failed/10 text-status-failed border-status-failed/20",
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-background-elevated p-4">
        <div className="max-w-[1920px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate("/dashboard")}
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-xl font-semibold">{projectName}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  className={cn(
                    "border text-xs",
                    statusColors[status as keyof typeof statusColors]
                  )}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Started {timeElapsed}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsPaused(!isPaused)}
            >
              {isPaused ? (
                <Play className="w-5 h-5" />
              ) : (
                <Pause className="w-5 h-5" />
              )}
            </Button>
            <Button variant="ghost" size="icon" className="text-destructive">
              <Square className="w-5 h-5" />
            </Button>
            <div className="w-px h-6 bg-border mx-2" />
            <Button variant="ghost" size="icon">
              <Download className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon">
              <Settings className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="flex-1 p-1 overflow-auto">
        <div className="max-w-[1920px] mx-auto grid grid-cols-12 gap-1">
          {/* Top Row: Architecture (left) and Live Preview (right) */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="col-span-12 md:col-span-4 hidden md:block"
          >
            <ArchitecturePanel onFileClick={handleFileClick} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="col-span-12 md:col-span-8"
          >
            <TabbedViewPanel
              device={device}
              onDeviceChange={setDevice}
              tabs={tabs}
              activeTabId={activeTabId}
              onTabChange={setActiveTabId}
              onTabClose={handleTabClose}
            />
          </motion.div>

          {/* Bottom Row: Status & Metrics (left) and Agent Communication (right) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-4 hidden md:block"
          >
            <StatusPanel job={job} steps={steps} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-8"
          >
            <AgentPanel
              messages={messages}
              steps={steps}
              onSendMessage={handleSendMessage}
              canSendMessages={canSendMessages}
            />
          </motion.div>

          {/* Mobile: Show Architecture */}
          <div className="col-span-12 md:hidden">
            <ArchitecturePanel />
          </div>
        </div>
      </div>
    </div>
  );
}

