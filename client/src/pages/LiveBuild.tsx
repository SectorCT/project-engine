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
  PlusCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api, JobMessage, JobStep, Ticket } from "@/lib/api";
import { useWebSocket, WebSocketMessage } from "@/hooks/useWebSocket";
import { mapServerStatusToClient, formatTimeAgo } from "@/lib/jobUtils";
import { toast } from "sonner";

interface Tab {
  id: string;
  type: "preview" | "code" | "tickets";
  label: string;
  filePath?: string;
  content?: string;
  closable: boolean;
}

export default function LiveBuild() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isPaused, setIsPaused] = useState(false);
  const [device, setDevice] = useState<"desktop" | "mobile">(
    "desktop"
  );
  const [tabs, setTabs] = useState<Tab[]>([
    {
      id: "preview",
      type: "preview",
      label: "Live Preview",
      closable: false,
    },
    {
      id: "tickets",
      type: "tickets",
      label: "Tickets",
      closable: false,
    },
  ]);
  const [activeTabId, setActiveTabId] = useState<string>("preview");
  const [messages, setMessages] = useState<JobMessage[]>([]);
  const [steps, setSteps] = useState<JobStep[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [appSpec, setAppSpec] = useState<any>(null);
  const [isEditPromptOpen, setIsEditPromptOpen] = useState(false);
  const [editPrompt, setEditPrompt] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [isContinuationOpen, setIsContinuationOpen] = useState(false);
  const [continuationText, setContinuationText] = useState("");
  const [isContinuing, setIsContinuing] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [renameText, setRenameText] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

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

  // Helper function to load messages from REST API
  const loadMessages = async (jobId: string) => {
    try {
      const msgs = await api.getJobMessages(jobId);
      // Sort messages by created_at timestamp (oldest first)
      const sorted = [...msgs].sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
      setMessages(sorted);
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };

  // Helper function to add informative system messages
  const addSystemMessage = (content: string, metadata: Record<string, any> = {}) => {
    const uniqueId = `temp-system-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const systemMessage: JobMessage = {
      id: uniqueId,
      role: 'system',
      sender: 'System',
      content,
      metadata: {
        ...metadata,
        type: 'status_update',
      },
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => mergeMessages(prev, systemMessage));
  };

  // Helper function to merge messages without duplicates
  const mergeMessages = (existing: JobMessage[], newMsg: JobMessage): JobMessage[] => {
    // Check for duplicates by ID first (most reliable)
    // Convert to string for comparison to handle both string and number IDs
    if (newMsg.id && existing.some(msg => String(msg.id) === String(newMsg.id))) {
      return existing;
    }
    
    // For user messages: check if we already have an optimistic message (temp-user-*) 
    // that matches the incoming message (which will have a real ID or temp-* from WebSocket)
    if (newMsg.role === 'user') {
      const isDuplicateUserMsg = existing.some(msg => {
        // Match by content and role, and timestamp within 5 seconds
        // This catches the optimistic update vs the WebSocket echo
        const timeDiff = Math.abs(
          new Date(msg.created_at).getTime() - new Date(newMsg.created_at).getTime()
        );
        return (
          msg.content === newMsg.content &&
          msg.role === 'user' &&
          timeDiff < 5000 // 5 second window for user messages
        );
      });
      
      if (isDuplicateUserMsg) {
        // Replace the optimistic message with the one from server (has better ID/timestamp)
        return existing.map(msg => {
          const timeDiff = Math.abs(
            new Date(msg.created_at).getTime() - new Date(newMsg.created_at).getTime()
          );
          if (
            msg.content === newMsg.content &&
            msg.role === 'user' &&
            timeDiff < 5000 &&
            String(msg.id).startsWith('temp-user-')
          ) {
            return newMsg; // Replace optimistic with server version
          }
          return msg;
        }).sort((a, b) => 
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
      }
    }
    
    // Check for duplicates by content, sender, and timestamp (within 2 seconds)
    const isDuplicate = existing.some(msg => {
      const timeDiff = Math.abs(
        new Date(msg.created_at).getTime() - new Date(newMsg.created_at).getTime()
      );
      return (
        msg.content === newMsg.content &&
        msg.sender === newMsg.sender &&
        msg.role === newMsg.role &&
        timeDiff < 2000
      );
    });
    
    if (isDuplicate) {
      return existing;
    }
    
    // Add new message and sort by timestamp
    const merged = [...existing, newMsg];
    return merged.sort((a, b) => 
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  };

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
    onOpen: () => {
      // When WebSocket reconnects, refetch messages to ensure we have complete history
      // This handles the case where messages were sent while disconnected
      if (id) {
        loadMessages(id);
      }
    },
  });

  // Load initial messages on mount
  useEffect(() => {
    if (id) {
      loadMessages(id);
    }
  }, [id]);

  // Load initial tickets
  useEffect(() => {
    if (id) {
      api.getTickets(id)
        .then((tickets) => setTickets(tickets))
        .catch((err) => console.error('Failed to load tickets:', err));
    }
  }, [id]);

  // Update messages and steps when job data changes (but merge, don't overwrite)
  useEffect(() => {
    if (job) {
      // Merge job messages with existing messages (job.messages might be incomplete)
      const jobMessages = job.messages;
      if (jobMessages && Array.isArray(jobMessages) && jobMessages.length > 0) {
        setMessages((prev) => {
          // Start with job messages as base (they're from REST API, so authoritative)
          const merged = [...jobMessages];
          
          // Add any WebSocket messages that aren't in job.messages
          prev.forEach((msg) => {
            // Only add if it's a temporary message (starts with 'temp-') and not in job.messages
            // Convert id to string to handle cases where API returns number
            const msgId = String(msg.id);
            if (msgId.startsWith('temp-') && !merged.some(m => 
              m.content === msg.content && 
              m.sender === msg.sender &&
              Math.abs(new Date(m.created_at).getTime() - new Date(msg.created_at).getTime()) < 2000
            )) {
              merged.push(msg);
            }
          });
          
          // Sort by timestamp
          return merged.sort((a, b) => 
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          );
        });
      }
      
      if (job.steps) {
        setSteps(job.steps);
      }
    }
  }, [job]);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.kind) {
      case 'stageUpdate':
        // Chat message from user or agent (includes both human chat and system descriptions)
        // According to API reference: role, sender, content, metadata.stage
        if (message.role && message.content) {
          // Use a temporary ID for WebSocket messages until they're persisted
          // The server will assign a real ID when it persists the message
          const uniqueId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newMessage: JobMessage = {
            id: uniqueId,
            role: message.role,
            sender: message.sender || '',
            content: message.content,
            metadata: {
              ...message.metadata,
              // Ensure metadata.stage is preserved if present
              stage: message.metadata?.stage || undefined,
            },
            created_at: message.timestamp || new Date().toISOString(),
          };
          
          // Check for Docker container initialization messages
          const content = message.content.toLowerCase();
          const stage = message.metadata?.stage || '';
          const sender = message.sender || '';
          
          // Detect Docker container initialization
          if ((stage === 'Environment' || sender === 'Builder') && (
            content.includes('starting docker container') ||
            content.includes('docker container') ||
            content.includes('initializing docker') ||
            content.includes('building docker image')
          )) {
            // Check if we already added a Docker initialization message
            const hasDockerMsg = messages.some(
              (msg) => msg.metadata?.type === 'docker_initialized'
            );
            if (!hasDockerMsg) {
              addSystemMessage('🐳 Docker container initialized and ready for build!', {
                type: 'docker_initialized',
                stage: stage,
              });
            }
          }
          
          setMessages((prev) => mergeMessages(prev, newMessage));
        }
        break;
      case 'jobStatus':
        // Job status update (queued, running, done, failed)
        if (message.status) {
          const status = message.status;
          
          // Add informative message about status change
          const statusMessages: Record<string, string> = {
            collecting: '📝 Collecting requirements from you...',
            queued: '⏳ Job queued and ready to start',
            planning: '🤔 Executive team is planning the project architecture',
            prd_ready: '📋 Product Requirements Document is ready',
            ticketing: '🎫 Creating tickets and breaking down the work',
            tickets_ready: '📋 Tickets have been created and are ready for execution!',
            building: '🔨 Build phase started! Initializing Docker environment...',
            build_done: '🎉 Build completed successfully! All tickets have been executed.',
            failed: '❌ Build failed - check error details',
          };
          const statusMsg = statusMessages[status] || `Status changed to: ${status}`;
          addSystemMessage(statusMsg, { stage: status });
          
          // Special handling for tickets_ready - open tickets tab and load tickets
          if (status === 'tickets_ready') {
            // Open tickets tab automatically
            setActiveTabId('tickets');
            
            // Load tickets
            if (id) {
              api.getTickets(id)
                .then((tickets) => {
                  setTickets(tickets);
                  if (tickets.length > 0) {
                    addSystemMessage(`📦 ${tickets.length} ticket(s) loaded and ready to build.`, {
                      type: 'tickets_loaded',
                      ticketCount: tickets.length,
                    });
                  }
                })
                .catch((err) => console.error('Failed to load tickets:', err));
            }
          }
          
          // Refetch to get full updated job data
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
        // PRD/spec is ready (but project is NOT done yet - tickets still need to be built)
        if (message.spec) {
          addSystemMessage('📄 Product Requirements Document finalized and ready for review', { stage: 'prd_ready' });
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
          // Show info message, not completion - tickets still need to be built
          toast.info('PRD ready! Tickets will be generated next.');
        }
        break;
      case 'ticketUpdate':
        // Ticket status update (created, in_progress, done, failed)
        if (message.ticketId && message.title) {
          const ticketStatus = message.status || 'unknown';
          const ticketTitle = message.title;
          const assignedTo = message.assignedTo || 'Builder';
          const ticketType = message.type || 'story';
          const event = message.metadata?.event;
          
          // Create a chat message for the ticket update
          const uniqueId = `ticket-${message.ticketId}-${Date.now()}`;
          let statusMessage = '';
          
          // Check if this is a ticket creation event
          if (event === 'created') {
            statusMessage = `📝 Created ticket: "${ticketTitle}"`;
          } else if (ticketStatus === 'in_progress') {
            statusMessage = `🔄 Started working on ticket: "${ticketTitle}"`;
          } else if (ticketStatus === 'done') {
            statusMessage = `✅ Completed ticket: "${ticketTitle}"`;
          } else if (ticketStatus === 'failed') {
            statusMessage = `❌ Failed ticket: "${ticketTitle}"`;
          } else {
            statusMessage = `📋 Ticket "${ticketTitle}" status: ${ticketStatus}`;
          }
          
          const ticketMessage: JobMessage = {
            id: uniqueId,
            role: 'system',
            sender: assignedTo,
            content: statusMessage,
            metadata: {
              ticketId: message.ticketId,
              ticketTitle: ticketTitle,
              ticketStatus: ticketStatus,
              ticketType: ticketType,
              event: event,
              ...message.metadata,
            },
            created_at: message.timestamp || new Date().toISOString(),
          };
          
          setMessages((prev) => {
            // Avoid duplicates by checking ticket ID and status/event
            const exists = prev.some(
              (msg) => msg.metadata?.ticketId === message.ticketId && 
                       (msg.metadata?.ticketStatus === ticketStatus || 
                        (event === 'created' && msg.metadata?.event === 'created'))
            );
            if (exists) return prev;
            return [...prev, ticketMessage];
          });
          
          // Refetch tickets to update the tickets panel
          if (id) {
            api.getTickets(id)
              .then((tickets) => {
                setTickets(tickets);
                // Auto-open tickets tab if it's not already open and we have tickets
                if (tickets.length > 0 && activeTabId !== 'tickets') {
                  // Only auto-open on first ticket update, not every update
                  const hasTicketMessages = messages.some(
                    (msg) => msg.metadata?.type === 'tickets_ready'
                  );
                  if (!hasTicketMessages) {
                    setActiveTabId('tickets');
                  }
                }
              })
              .catch((err) => console.error('Failed to refresh tickets:', err));
          }
        }
        break;
      case 'ticketReset':
        // Backlog snapshot is being regenerated - refetch tickets
        if (id) {
          addSystemMessage('📋 Ticket backlog is being regenerated...', {
            type: 'ticket_reset',
          });
          
          api.getTickets(id)
            .then((tickets) => {
              setTickets(tickets);
              // Auto-open tickets tab when tickets are reset/regenerated
              if (tickets.length > 0) {
                setActiveTabId('tickets');
                addSystemMessage(`📦 ${tickets.length} ticket(s) loaded.`, {
                  type: 'tickets_loaded',
                  ticketCount: tickets.length,
                });
              }
            })
            .catch((err) => console.error('Failed to refresh tickets after reset:', err));
        }
        break;
      case 'ticketUpdate':
        // Ticket execution feed
        if (message.ticketId && message.title) {
          const ticketStatus = message.status || 'updated';
          const statusEmoji = {
            'todo': '📋',
            'in_progress': '🔄',
            'done': '✅',
            'blocked': '🚫',
            'review': '👀',
          }[ticketStatus] || '📌';
          
          const updateMsg = `${statusEmoji} Ticket "${message.title}" (${message.type || 'task'}) is now ${ticketStatus}${message.assignedTo ? ` - assigned to ${message.assignedTo}` : ''}`;
          if (message.message) {
            addSystemMessage(`${updateMsg}\n${message.message}`, { 
              stage: 'building',
              ticketId: message.ticketId,
              ticketStatus: ticketStatus,
            });
          } else {
            addSystemMessage(updateMsg, { 
              stage: 'building',
              ticketId: message.ticketId,
              ticketStatus: ticketStatus,
            });
          }
          
          // Refetch tickets to get updated state
          if (id) {
            api.getTickets(id)
              .then((updatedTickets) => setTickets(updatedTickets))
              .catch((err) => console.error('Failed to reload tickets:', err));
          }
        }
        break;
      case 'ticketReset':
        // Ticket backlog is being regenerated
        addSystemMessage('🔄 Regenerating ticket backlog - previous tickets are being replaced', { 
          stage: 'ticketing',
        });
        // Refetch tickets when reset happens
        if (id) {
          api.getTickets(id)
            .then((updatedTickets) => {
              setTickets(updatedTickets);
              if (updatedTickets.length > 0) {
                addSystemMessage(`✅ Generated ${updatedTickets.length} new tickets for the project`, { 
                  stage: 'tickets_ready',
                });
              }
            })
            .catch((err) => console.error('Failed to reload tickets:', err));
        }
        break;
      case 'error':
        toast.error(message.message || 'An error occurred');
        addSystemMessage(`❌ Error: ${message.message || 'An error occurred'}`, { 
          type: 'error',
        });
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
      
      // Use mergeMessages to avoid duplicates
      setMessages((prev) => mergeMessages(prev, userMessage));
      
      // Send message via WebSocket
      // According to API reference: send {"kind":"chat","content":"..."} while status is collecting
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

  const handleContinueJob = async () => {
    if (!id || !continuationText.trim()) {
      toast.error('Please enter your additional requirements');
      return;
    }

    setIsContinuing(true);
    try {
      await api.continueJob(id, continuationText.trim());
      addSystemMessage(`🔄 Continuation request submitted: "${continuationText.trim()}"`, {
        stage: 'continuation',
        type: 'user_followup',
      });
      toast.success('Continuation queued! The agents will process your new requirements.');
      setIsContinuationOpen(false);
      setContinuationText('');
      refetch();
    } catch (error: any) {
      const errorMsg = error?.detail || 'Failed to submit continuation request';
      toast.error(errorMsg);
      addSystemMessage(`❌ Continuation failed: ${errorMsg}`, {
        type: 'error',
      });
    } finally {
      setIsContinuing(false);
    }
  };

  const handleRenameJob = async () => {
    if (!id || !renameText.trim()) {
      toast.error('Project name cannot be empty');
      return;
    }

    if (job?.status !== 'collecting') {
      toast.error('You can only rename the project while it is in the collecting phase');
      return;
    }

    setIsRenaming(true);
    try {
      await api.updateJob(id, renameText.trim());
      toast.success('Project renamed successfully');
      setIsSettingsOpen(false);
      refetch();
    } catch (error: any) {
      toast.error(error?.detail || 'Failed to rename project');
    } finally {
      setIsRenaming(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!id) return;

    if (!window.confirm('Are you sure you want to delete this project? This action cannot be undone and will stop any running containers.')) {
      return;
    }

    setIsDeleting(true);
    try {
      await api.deleteJob(id);
      toast.success('Project deleted successfully');
      navigate('/dashboard');
    } catch (error: any) {
      toast.error(error?.detail || 'Failed to delete project');
      setIsDeleting(false);
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
  const canContinue = (job.status === 'build_done' || job.status === 'failed' || job.status === 'done') && !job.error_message?.includes('continuation');

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
            {canContinue && (
              <Button
                variant="default"
                size="sm"
                onClick={() => setIsContinuationOpen(true)}
                className="gap-2"
              >
                <PlusCircle className="w-4 h-4" />
                Add Features
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
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => {
                setIsSettingsOpen(true);
                if (job) {
                  setRenameText(job.initial_prompt);
                }
              }}
            >
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
              tickets={tickets}
              jobStatus={job?.status}
              errorMessage={job?.error_message}
            />
          </motion.div>

          {/* Bottom Row: Status & Metrics (left) and Agent Communication (right) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-4 hidden md:block flex h-[550px]"
          >
            <StatusPanel job={job} steps={steps} tickets={tickets} messages={messages} />
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
                  loadMessages(id);
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

      {/* Continuation Dialog */}
      {isContinuationOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-2xl mx-4 glass">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Add New Features</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setIsContinuationOpen(false);
                    setContinuationText('');
                  }}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="continuation-requirements">Additional Requirements</Label>
                <Textarea
                  id="continuation-requirements"
                  value={continuationText}
                  onChange={(e) => setContinuationText(e.target.value)}
                  placeholder="Describe the new features or changes you'd like to add... (e.g., 'Add PDF export functionality', 'Implement dark mode', 'Add user authentication')"
                  className="min-h-[200px]"
                />
                <p className="text-sm text-muted-foreground">
                  The agents will process your new requirements and update the project accordingly. This will trigger a new build cycle.
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsContinuationOpen(false);
                    setContinuationText('');
                  }}
                  disabled={isContinuing}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleContinueJob}
                  disabled={isContinuing || !continuationText.trim()}
                >
                  {isContinuing ? 'Submitting...' : 'Submit Requirements'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Settings Dialog */}
      {isSettingsOpen && job && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-2xl mx-4 glass">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Project Settings</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setIsSettingsOpen(false);
                    setRenameText('');
                  }}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Project Info */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Project Information</Label>
                <div className="p-4 bg-muted/30 rounded-lg space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <span className="font-medium">{job.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Created:</span>
                    <span className="font-medium">{new Date(job.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Job ID:</span>
                    <span className="font-mono text-xs">{job.id}</span>
                  </div>
                </div>
              </div>

              {/* Rename Project */}
              <div className="space-y-2">
                <Label htmlFor="rename-project">Project Name</Label>
                <Textarea
                  id="rename-project"
                  value={renameText}
                  onChange={(e) => setRenameText(e.target.value)}
                  placeholder="Enter project name/description..."
                  className="min-h-[100px]"
                  disabled={job.status !== 'collecting'}
                />
                <p className="text-sm text-muted-foreground">
                  {job.status === 'collecting' 
                    ? 'You can rename the project while it is in the collecting phase.'
                    : 'Project can only be renamed during the collecting phase.'}
                </p>
              </div>

              {/* Actions */}
              <div className="flex justify-between items-center pt-4 border-t border-border">
                <Button
                  variant="destructive"
                  onClick={handleDeleteJob}
                  disabled={isDeleting || isRenaming}
                >
                  {isDeleting ? 'Deleting...' : 'Delete Project'}
                </Button>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsSettingsOpen(false);
                      setRenameText('');
                    }}
                    disabled={isDeleting || isRenaming}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleRenameJob}
                    disabled={isDeleting || isRenaming || !renameText.trim() || job.status !== 'collecting'}
                  >
                    {isRenaming ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

