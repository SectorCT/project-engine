import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FolderTree, Box, Database, Package, ChevronRight, ChevronDown, File, Folder } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface FileNode {
  id: string;
  name: string;
  type: "folder" | "file";
  status: "complete" | "in-progress" | "pending";
  linesOfCode?: number;
  children?: FileNode[];
  path?: string;
}

interface ArchitecturePanelProps {
  onFileClick?: (filePath: string, fileName: string) => void;
}

const mockFileTree: FileNode[] = [
  {
    id: "1",
    name: "src",
    type: "folder",
    status: "in-progress",
    children: [
      {
        id: "2",
        name: "components",
        type: "folder",
        status: "in-progress",
        children: [
          {
            id: "3",
            name: "Header.tsx",
            type: "file",
            status: "complete",
            linesOfCode: 45,
          },
          {
            id: "4",
            name: "Sidebar.tsx",
            type: "file",
            status: "in-progress",
            linesOfCode: 32,
          },
          {
            id: "5",
            name: "TaskList.tsx",
            type: "file",
            status: "pending",
            linesOfCode: 0,
          },
        ],
      },
      {
        id: "6",
        name: "pages",
        type: "folder",
        status: "in-progress",
        children: [
          {
            id: "7",
            name: "Dashboard.tsx",
            type: "file",
            status: "complete",
            linesOfCode: 120,
          },
          {
            id: "8",
            name: "Settings.tsx",
            type: "file",
            status: "in-progress",
            linesOfCode: 67,
          },
        ],
      },
      {
        id: "9",
        name: "lib",
        type: "folder",
        status: "in-progress",
        children: [
          {
            id: "10",
            name: "utils.ts",
            type: "file",
            status: "in-progress",
            linesOfCode: 15,
          },
        ],
      },
    ],
  },
];

const FileTreeItem = ({
  node,
  level = 0,
  onFileClick,
  currentPath = "",
}: {
  node: FileNode;
  level?: number;
  onFileClick?: (filePath: string, fileName: string) => void;
  currentPath?: string;
}) => {
  const [isExpanded, setIsExpanded] = useState(level < 2);

  const hasChildren = node.children && node.children.length > 0;
  const filePath = currentPath ? `${currentPath}/${node.name}` : node.name;
  
  const StatusIcon = () => {
    if (node.status === "complete") {
      return <span className="text-success text-xs">✓</span>;
    } else if (node.status === "in-progress") {
      return <span className="text-warning text-xs animate-spin">⚙</span>;
    } else {
      return <span className="text-muted-foreground text-xs">⏳</span>;
    }
  };

  const handleClick = () => {
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    } else if (node.type === "file" && onFileClick) {
      onFileClick(filePath, node.name);
    }
  };

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 py-1 px-2 rounded hover:bg-muted/50 cursor-pointer",
          node.type === "file" && "hover:bg-primary/10"
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={handleClick}
      >
        {hasChildren ? (
          isExpanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )
        ) : (
          <div className="w-4" />
        )}
        {node.type === "folder" ? (
          <Folder className="w-4 h-4 text-primary" />
        ) : (
          <File className="w-4 h-4 text-muted-foreground" />
        )}
        <span className="text-sm flex-1">{node.name}</span>
        <StatusIcon />
        {node.linesOfCode !== undefined && (
          <span className="text-xs text-muted-foreground">
            {node.linesOfCode} lines
          </span>
        )}
      </div>
      <AnimatePresence>
        {hasChildren && isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {node.children!.map((child) => (
              <FileTreeItem 
                key={child.id} 
                node={child} 
                level={level + 1}
                onFileClick={onFileClick}
                currentPath={filePath}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const ArchitecturePanel = ({ onFileClick }: ArchitecturePanelProps) => {
  return (
    <Card className="glass flex flex-col">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Architecture</h2>
      </div>

      <Tabs defaultValue="files" className="flex-1 flex flex-col">
        <TabsList className="mx-4 mt-4">
          <TabsTrigger value="files" className="flex items-center gap-2">
            <FolderTree className="w-4 h-4" />
            Files
          </TabsTrigger>
          <TabsTrigger value="components" className="flex items-center gap-2">
            <Box className="w-4 h-4" />
            Components
          </TabsTrigger>
          <TabsTrigger value="database" className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            Database
          </TabsTrigger>
          <TabsTrigger value="dependencies" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            Dependencies
          </TabsTrigger>
        </TabsList>

        <TabsContent value="files" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            <div className="space-y-1">
              {mockFileTree.map((node) => (
                <FileTreeItem key={node.id} node={node} onFileClick={onFileClick} />
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="components" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            <div className="text-sm text-muted-foreground">
              Component architecture view coming soon...
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="database" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            <div className="text-sm text-muted-foreground">
              Database schema view coming soon...
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="dependencies" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            <div className="text-sm text-muted-foreground">
              Dependencies view coming soon...
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </Card>
  );
};

