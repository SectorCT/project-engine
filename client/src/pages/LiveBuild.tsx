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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  ArrowLeft,
  Pause,
  Play,
  Square,
  Download,
  Settings,
  Edit,
  X,
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
  const [isEditPromptOpen, setIsEditPromptOpen] = useState(false);
  const [editPrompt, setEditPrompt] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

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
      case 'stageUpdate':
        // Chat message from user or agent
        if (message.role && message.content) {
          const newMessage: JobMessage = {
            id: `temp-${Date.now()}`,
            role: message.role,
            sender: message.sender || '',
            content: message.content,
            metadata: message.metadata || {},
            created_at: message.timestamp || new Date().toISOString(),
          };
          setMessages((prev) => {
            // Avoid duplicates by checking if message already exists
            const exists = prev.some(
              (msg) => msg.content === message.content && 
                       msg.sender === message.sender && 
                       msg.created_at === message.timestamp
            );
            if (exists) return prev;
            return [...prev, newMessage];
          });
        }
        break;
      case 'jobStatus':
        // Job status update (queued, running, done, failed)
        if (message.status) {
          // Update local job status immediately
          if (job) {
            // Update the job object in place
            const updatedJob = { ...job, status: message.status as any };
            // Refetch to get full updated job data
        refetch();
          }
        }
        break;
      case 'agentDialogue':
        // Executive agent step (CEO/CTO/Secretary)
        if (message.agent && message.message) {
          const newStep: JobStep = {
            id: `temp-${Date.now()}`,
            agent_name: message.agent,
            message: message.message,
            order: message.order || steps.length + 1,
            created_at: message.timestamp || new Date().toISOString(),
          };
          setSteps((prev) => {
            // Avoid duplicates by checking if step already exists
            const exists = prev.some(
              (step) => step.agent_name === message.agent && 
                        step.message === message.message && 
                        step.order === message.order
            );
            if (exists) return prev;
            return [...prev, newStep];
          });
        }
        break;
      case 'prdReady':
        // Final app artifact is ready
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
          // Refetch to get the full app data including prdMarkdown
          refetch();
          toast.success('Project completed!');
        }
        break;
      case 'error':
        toast.error(message.message || 'An error occurred');
        break;
      default:
        // Unknown message type, log for debugging
        console.warn('Unknown WebSocket message type:', message.kind, message);
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

  const handleEditPrompt = () => {
    if (job) {
      setEditPrompt(job.initial_prompt);
      setIsEditPromptOpen(true);
    }
  };

  const handleSavePrompt = async () => {
    if (!id || !editPrompt.trim()) {
      toast.error('Prompt cannot be empty');
      return;
    }

    setIsUpdating(true);
    try {
      await api.updateJob(id, editPrompt.trim());
      toast.success('Prompt updated successfully');
      setIsEditPromptOpen(false);
      refetch();
    } catch (error: any) {
      toast.error(error?.detail || 'Failed to update prompt');
    } finally {
      setIsUpdating(false);
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
  const canEditPrompt = job.status === 'collecting';

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
            {canEditPrompt && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleEditPrompt}
                className="gap-2"
              >
                <Edit className="w-4 h-4" />
                Edit Prompt
              </Button>
            )}
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
              onMessageDeleted={() => {
                refetch();
                if (id) {
                  api.getJobMessages(id)
                    .then((msgs) => setMessages(msgs))
                    .catch((err) => console.error('Failed to reload messages:', err));
                }
              }}
            />
          </motion.div>

          {/* Mobile: Show Architecture */}
          <div className="col-span-12 md:hidden">
            <ArchitecturePanel />
          </div>
        </div>
      </div>

      {/* Edit Prompt Dialog */}
      {isEditPromptOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-2xl mx-4 glass">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Edit Project Prompt</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsEditPromptOpen(false)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-prompt">Project Description</Label>
                <Textarea
                  id="edit-prompt"
                  value={editPrompt}
                  onChange={(e) => setEditPrompt(e.target.value)}
                  placeholder="Describe your project idea..."
                  className="min-h-[200px]"
                />
                <p className="text-sm text-muted-foreground">
                  You can only edit the prompt while the project is in the planning phase.
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setIsEditPromptOpen(false)}
                  disabled={isUpdating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSavePrompt}
                  disabled={isUpdating || !editPrompt.trim()}
                >
                  {isUpdating ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

