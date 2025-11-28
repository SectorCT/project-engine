import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X, Monitor, Tablet, Smartphone, RefreshCw, ExternalLink, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { LivePreviewContent } from "./LivePreviewContent";
import { CodeViewer } from "./CodeViewer";

interface Tab {
  id: string;
  type: "preview" | "code";
  label: string;
  filePath?: string;
  content?: string;
  closable: boolean;
}

interface TabbedViewPanelProps {
  device: "desktop" | "tablet" | "mobile";
  onDeviceChange?: (device: "desktop" | "tablet" | "mobile") => void;
  tabs: Tab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
}

const deviceDimensions = {
  desktop: "w-full",
  tablet: "w-[768px] mx-auto",
  mobile: "w-[375px] mx-auto",
};

export const TabbedViewPanel = ({
  device: initialDevice,
  onDeviceChange,
  tabs,
  activeTabId,
  onTabChange,
  onTabClose,
}: TabbedViewPanelProps) => {
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">(
    initialDevice
  );

  const handleDeviceChange = (newDevice: "desktop" | "tablet" | "mobile") => {
    setDevice(newDevice);
    onDeviceChange?.(newDevice);
  };

  const activeTab = tabs.find((tab) => tab.id === activeTabId) || tabs[0];

  return (
    <Card className="glass flex flex-col" style={{ maxHeight: 'calc((100vw - 0.5rem) * 8 / 12 * 9 / 16 + 50px)' }}>
      {/* Tabs Bar */}
      <div className="flex items-center border-b border-border bg-background-elevated overflow-x-auto flex-shrink-0">
        <div className="flex items-center min-w-0 flex-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors min-w-0",
                activeTabId === tab.id
                  ? "border-primary text-foreground bg-background"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <span className="truncate">{tab.label}</span>
              {tab.closable && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onTabClose(tab.id);
                  }}
                  className="ml-1 hover:bg-muted rounded p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </button>
          ))}
        </div>

        {/* Controls - Only show for preview tab */}
        {activeTab.type === "preview" && (
          <div className="flex items-center gap-2 px-4 border-l border-border">
            <div className="flex gap-1 bg-muted rounded-md p-1">
              <Button
                variant={device === "desktop" ? "default" : "ghost"}
                size="sm"
                onClick={() => handleDeviceChange("desktop")}
                className="h-8 px-3"
              >
                <Monitor className="w-4 h-4" />
              </Button>
              <Button
                variant={device === "tablet" ? "default" : "ghost"}
                size="sm"
                onClick={() => handleDeviceChange("tablet")}
                className="h-8 px-3"
              >
                <Tablet className="w-4 h-4" />
              </Button>
              <Button
                variant={device === "mobile" ? "default" : "ghost"}
                size="sm"
                onClick={() => handleDeviceChange("mobile")}
                className="h-8 px-3"
              >
                <Smartphone className="w-4 h-4" />
              </Button>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ExternalLink className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden min-h-0">
        {activeTab.type === "preview" ? (
          <div className="h-full p-4 flex items-start justify-center">
            <div className={cn("w-full h-full mx-auto flex items-start justify-center", deviceDimensions[device])}>
              <LivePreviewContent device={device} />
            </div>
          </div>
        ) : (
          <div className="h-full min-h-0">
            <CodeViewer
              filePath={activeTab.filePath || ""}
              content={activeTab.content}
            />
          </div>
        )}
      </div>
    </Card>
  );
};

