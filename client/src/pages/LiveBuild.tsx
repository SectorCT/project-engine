import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AgentPanel } from "@/components/build/AgentPanel";
import { TabbedViewPanel } from "@/components/build/TabbedViewPanel";
import { ArchitecturePanel } from "@/components/build/ArchitecturePanel";
import { StatusPanel } from "@/components/build/StatusPanel";
import { TicketPanel, TicketEvent } from "@/components/build/TicketPanel";
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
import { api, Job, JobMessage, JobStep, Ticket } from "@/lib/api";
import { useWebSocket, WebSocketMessage } from "@/hooks/useWebSocket";
import { mapServerStatusToClient, formatTimeAgo } from "@/lib/jobUtils";
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
  const [tickets, setTickets] = useState<TicketEvent[]>([]);
  const [appSpec, setAppSpec] = useState<any>(null);
  const [isEditPromptOpen, setIsEditPromptOpen] = useState(false);
  const [editPrompt, setEditPrompt] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const queryClient = useQueryClient();

  const ticketSnapshotToEvent = useCallback((record: Ticket): TicketEvent => ({
    ticketId: record.id,
    title: record.title,
    status: record.status,
    type: record.type,
    assignedTo: record.assigned_to || undefined,
    timestamp: record.updated_at,
    message: record.description,
  }), []);

  const loadTicketsSnapshot = useCallback(() => {
    if (!id) return;
    api.listTickets(id)
      .then((records) => setTickets(records.map(ticketSnapshotToEvent)))
      .catch((err) => console.error('Failed to load tickets:', err));
  }, [id, ticketSnapshotToEvent]);

  // Fetch job data
  const { data: job, isLoading, error, refetch } = useQuery({
    queryKey: ['job', id],
    queryFn: () => api.getJob(id!),
    enabled: !!id,
  });

  const isAppReady = job?.status === 'done' || job?.status === 'build_done';
  // Fetch app data when job is done/build_done
  const { data: app } = useQuery({
    queryKey: ['app', id],
    queryFn: () => api.getAppByJob(id!),
    enabled: !!id && isAppReady,
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
    onError: (event) => {
      if (event.type === 'no_token') {
        toast.error('Missing WebSocket token. Please log in again.');
        return;
      }

      if (typeof CloseEvent !== "undefined" && event instanceof CloseEvent) {
        if ([4001, 4003, 1008].includes(event.code)) {
          toast.error('WebSocket authentication failed. Refresh and sign in again.');
          return;
        }
      }

      toast.warning('WebSocket connection interrupted. Retrying…');
      console.error('WebSocket error:', event);
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

  useEffect(() => {
    if (!job) return;
    if (['tickets_ready', 'building', 'build_done', 'done'].includes(job.status)) {
      loadTicketsSnapshot();
    }
  }, [job, loadTicketsSnapshot]);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.kind) {
      case 'stageUpdate':
        // Chat message from user or agent
        if (message.role && message.content) {
          // Use a more unique ID to avoid duplicate key warnings
          const uniqueId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newMessage: JobMessage = {
            id: uniqueId,
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
        if (message.status && id) {
          queryClient.setQueryData<Job | undefined>(['job', id], (prev) =>
            prev ? { ...prev, status: message.status as Job['status'], error_message: message.message || prev.error_message } : prev
          );
          if (message.status === 'failed' && message.message) {
            toast.error(message.message);
          }
          refetch();
        }
        break;
      case 'agentDialogue':
        // Executive agent step (CEO/CTO/Secretary)
        if (message.agent && message.message) {
          // Use a more unique ID to avoid duplicate key warnings
          const uniqueId = `temp-step-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newStep: JobStep = {
            id: uniqueId,
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
      case 'ticketUpdate':
        if (message.ticketId) {
          setTickets((prev) => {
            const next = prev.filter((t) => t.ticketId !== message.ticketId);
            const ticketEvent: TicketEvent = {
              ticketId: message.ticketId!,
              title: message.title,
              status: message.status,
              type: message.type,
              assignedTo: message.assignedTo,
              timestamp: message.timestamp,
              message: message.message,
            };
            return [...next, ticketEvent];
          });
        }
        break;
      case 'ticketReset':
        setTickets([]);
        toast('Ticket backlog refreshing…');
        loadTicketsSnapshot();
        break;
      case 'control':
        if (message.message) {
          const level = message.metadata?.level || 'info';
          if (level === 'error') {
            toast.error(message.message);
          } else {
            toast(message.message);
          }
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
      // Optimistically add user's message to the UI immediately
      // Use a more unique ID to avoid duplicate key warnings
      const timestamp = new Date().toISOString();
      const uniqueId = `temp-user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const userMessage: JobMessage = {
        id: uniqueId,
        role: 'user',
        sender: 'You', // The server will use the actual user name/email
        content: content,
        metadata: {},
        created_at: timestamp,
      };
      
      setMessages((prev) => {
        // Check if message already exists to avoid duplicates
        // We check by content and recent timestamp to avoid showing the same message twice
        const exists = prev.some(
          (msg) => msg.content === content && 
                   msg.role === 'user' && 
                   Math.abs(new Date(msg.created_at).getTime() - new Date(timestamp).getTime()) < 2000
        );
        if (exists) return prev;
        return [...prev, userMessage];
      });
      
      // Send message via WebSocket
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
  const canSendMessages = job.status !== 'failed' && job.status !== 'done' && job.status !== 'build_done';
  const canEditPrompt = job.status === 'collecting';

  const statusColors = {
    planning: "bg-status-planning/10 text-status-planning border-status-planning/20",
    ticketing: "bg-status-testing/10 text-status-testing border-status-testing/20",
    building: "bg-status-building/10 text-status-building border-status-building/20",
    complete: "bg-status-complete/10 text-status-complete border-status-complete/20",
    failed: "bg-status-failed/10 text-status-failed border-status-failed/20",
  } as const;

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
        <div className="max-w-[1920px] mx-auto grid grid-cols-12 gap-1 h-full pb-8">
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

          {/* Bottom Row: Status & Tickets (left) and Agent Communication (right) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-4 hidden md:flex flex-col gap-2 h-[550px]"
          >
            <div className="flex-1 min-h-0">
              <StatusPanel job={job} steps={steps} />
            </div>
            <div className="flex-1 min-h-0">
              <TicketPanel tickets={tickets} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-8 flex h-[550px]"
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
          <div className="col-span-12 md:hidden space-y-2">
            <StatusPanel job={job} steps={steps} />
            <TicketPanel tickets={tickets} />
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

