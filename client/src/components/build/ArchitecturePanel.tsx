import { useState, useEffect, useRef, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FolderTree, Box, Package, ChevronRight, ChevronDown, File, Folder, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { api, FileStructureNode } from "@/lib/api";

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
  jobId?: string;
  onFileClick?: (filePath: string, fileName: string) => void;
}

// Transform backend FileStructureNode to FileNode format
const transformFileStructure = (nodes: FileStructureNode[], parentPath: string = ""): FileNode[] => {
  return nodes.map((node, index) => {
    const nodePath = node.path || (parentPath ? `${parentPath}/${node.name}` : node.name);
    const id = nodePath.replace(/[^a-zA-Z0-9]/g, "_");
    
    const fileNode: FileNode = {
      id,
      name: node.name,
      type: node.type === "dir" ? "folder" : "file",
      status: "complete", // Backend doesn't provide status, defaulting to complete
      path: nodePath,
    };

    if (node.type === "dir" && node.children && node.children.length > 0) {
      fileNode.children = transformFileStructure(node.children, nodePath);
    }

    return fileNode;
  });
};

// Find components folder in the file tree
const findComponentsFolder = (nodes: FileNode[]): FileNode | null => {
  for (const node of nodes) {
    if (node.name.toLowerCase() === "components" && node.type === "folder") {
      return node;
    }
    if (node.children) {
      const found = findComponentsFolder(node.children);
      if (found) return found;
    }
  }
  return null;
};

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
    } else if (node.type === "file" && onFileClick && node.path) {
      // Use the full path from the node if available, otherwise construct it
      const fullPath = node.path || filePath;
      onFileClick(fullPath, node.name);
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

export const ArchitecturePanel = ({ jobId, onFileClick }: ArchitecturePanelProps) => {
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [packageJsonContent, setPackageJsonContent] = useState<string | null>(null);
  const [isLoadingPackageJson, setIsLoadingPackageJson] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchFileStructure = useCallback(async () => {
    if (!jobId) {
      setFileTree([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getFileStructure(jobId, "/app", 200);
      const transformed = transformFileStructure(response.structure);
      setFileTree(transformed);
    } catch (err: any) {
      // Don't show error if container is not running or not found - just show empty state
      const errorMessage = err?.detail || err?.message || "Failed to fetch file structure";
      if (errorMessage.includes("not running") || errorMessage.includes("not found") || errorMessage.includes("Container")) {
        setFileTree([]);
        setError(null);
      } else {
        setError(errorMessage);
        console.error("Error fetching file structure:", err);
      }
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  const fetchPackageJson = useCallback(async () => {
    if (!jobId) {
      setPackageJsonContent(null);
      return;
    }

    setIsLoadingPackageJson(true);
    try {
      const response = await api.getFileContent(jobId, "/app/package.json");
      setPackageJsonContent(response.content);
    } catch (err: any) {
      // Don't show error if file doesn't exist yet
      const errorMessage = err?.detail || err?.message || "";
      if (errorMessage.includes("not found") || errorMessage.includes("not running") || errorMessage.includes("Container")) {
        setPackageJsonContent(null);
      } else {
        console.error("Error fetching package.json:", err);
        setPackageJsonContent(null);
      }
    } finally {
      setIsLoadingPackageJson(false);
    }
  }, [jobId]);

  useEffect(() => {
    // Fetch immediately on mount or when jobId changes
    fetchFileStructure();
    fetchPackageJson();

    // Set up polling every 5 seconds
    if (jobId) {
      intervalRef.current = setInterval(() => {
        fetchFileStructure();
        fetchPackageJson();
      }, 5000);
    }

    // Cleanup interval on unmount or when jobId changes
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId, fetchFileStructure, fetchPackageJson]);

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
          <TabsTrigger value="dependencies" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            Dependencies
          </TabsTrigger>
        </TabsList>

        <TabsContent value="files" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            {isLoading && fileTree.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="text-sm text-muted-foreground py-8 text-center">
                {error}
              </div>
            ) : fileTree.length === 0 ? (
              <div className="text-sm text-muted-foreground py-8 text-center">
                No files yet. Files will appear here once the project starts building.
              </div>
            ) : (
              <div className="space-y-1">
                {fileTree.map((node) => (
                  <FileTreeItem key={node.id} node={node} onFileClick={onFileClick} />
                ))}
              </div>
            )}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="components" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            {isLoading && fileTree.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : (() => {
              const componentsFolder = findComponentsFolder(fileTree);
              if (!componentsFolder) {
                return (
                  <div className="text-sm text-muted-foreground py-8 text-center">
                    Components folder not found yet. It will appear here once created.
                  </div>
                );
              }
              return (
                <div className="space-y-1">
                  <FileTreeItem key={componentsFolder.id} node={componentsFolder} onFileClick={onFileClick} />
                </div>
              );
            })()}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="dependencies" className="flex-1 mt-0">
          <ScrollArea className="h-full p-4">
            {isLoadingPackageJson ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : !packageJsonContent ? (
              <div className="text-sm text-muted-foreground py-8 text-center">
                package.json not found yet. It will appear here once the project is initialized.
              </div>
            ) : (
              <div className="bg-muted/30 rounded-lg p-4">
                <pre className="text-xs font-mono text-foreground whitespace-pre-wrap break-words overflow-x-auto">
                  <code>{(() => {
                    try {
                      const parsed = JSON.parse(packageJsonContent);
                      return JSON.stringify(parsed, null, 2);
                    } catch {
                      return packageJsonContent;
                    }
                  })()}</code>
                </pre>
              </div>
            )}
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </Card>
  );
};

