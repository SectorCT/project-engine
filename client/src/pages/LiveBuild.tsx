import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AgentPanel } from "@/components/build/AgentPanel";
import { LivePreviewPanel } from "@/components/build/LivePreviewPanel";
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

export default function LiveBuild() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isPaused, setIsPaused] = useState(false);
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">(
    "desktop"
  );

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
      <div className="flex-1 p-1 overflow-hidden">
        <div className="h-full max-w-[1920px] mx-auto grid grid-cols-12 grid-rows-2 gap-1">
          {/* Agent Panel - Left, spans 2 rows */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="col-span-12 md:col-span-4 row-span-2 hidden md:block"
          >
            <AgentPanel />
          </motion.div>

          {/* Live Preview - Top Right, spans 1 row */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-8 lg:col-span-5 row-span-1"
          >
            <LivePreviewPanel
              device={device}
              onDeviceChange={setDevice}
            />
          </motion.div>

          {/* Architecture Panel - Bottom Left, hidden on mobile */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-4 lg:col-span-4 row-span-1 hidden md:block"
          >
            <ArchitecturePanel />
          </motion.div>

          {/* Status Panel - Bottom Right */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="col-span-12 md:col-span-8 lg:col-span-4 row-span-1"
          >
            <StatusPanel />
          </motion.div>

          {/* Mobile: Agent Panel at top */}
          <div className="col-span-12 row-span-1 md:hidden">
            <AgentPanel />
          </div>
        </div>
      </div>
    </div>
  );
}

