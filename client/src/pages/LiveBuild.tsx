import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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

  const projectName = "Task Management App";
  const status = "building";
  const timeElapsed = "15 minutes ago";

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
            <StatusPanel />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-8"
          >
            <AgentPanel />
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

