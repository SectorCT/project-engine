import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { ProjectCard } from "@/components/ProjectCard";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Plus, Search, Filter, Code, Calendar, ExternalLink, Trash2 } from "lucide-react";
import { api, App } from "@/lib/api";
import { mapServerStatusToClient, calculateProgress, formatTimeAgo, extractTechStack, ClientJobStatus } from "@/lib/jobUtils";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";

interface Project {
  id: string;
  name: string;
  status: ClientJobStatus;
  progress: number;
  techStack: string[];
  createdAt: string;
  lastActivity: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"jobs" | "apps">("jobs");

  const queryClient = useQueryClient();
  
  const { data: jobs, isLoading, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.getJobs(),
  });

  const { data: apps, isLoading: isLoadingApps } = useQuery({
    queryKey: ['apps'],
    queryFn: () => api.getApps(),
    enabled: activeTab === 'apps',
  });

  const deleteJobMutation = useMutation({
    mutationFn: (jobId: string) => api.deleteJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success("Job deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error?.detail || "Failed to delete job");
    },
  });

  const handleDeleteJob = async (jobId: string) => {
    if (window.confirm("Are you sure you want to delete this project? This action cannot be undone.")) {
      await deleteJobMutation.mutateAsync(jobId);
    }
  };

  const purgeJobsMutation = useMutation({
    mutationFn: () => api.purgeJobs(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success(`Deleted ${data.deleted} job(s) successfully`);
    },
    onError: (error: any) => {
      toast.error(error?.detail || "Failed to purge jobs");
    },
  });

  const handlePurgeJobs = async () => {
    const confirmed = window.confirm(
      "⚠️ WARNING: This will delete ALL your jobs. This action cannot be undone!\n\nAre you absolutely sure?"
    );
    if (confirmed) {
      const doubleConfirm = window.confirm("This is your last chance. Delete ALL jobs?");
      if (doubleConfirm) {
        await purgeJobsMutation.mutateAsync();
      }
    }
  };

  // Check if in dev mode (for purge button visibility)
  const isDevMode = import.meta.env.DEV || import.meta.env.VITE_DEV_MODE === 'true';

  if (error) {
    toast.error("Failed to load jobs");
  }

  const projects: Project[] = (jobs || []).map((job) => ({
    id: job.id,
    name: job.initial_prompt.substring(0, 50) + (job.initial_prompt.length > 50 ? '...' : ''),
    status: mapServerStatusToClient(job.status),
    progress: calculateProgress(job),
    techStack: extractTechStack(job),
    createdAt: job.created_at,
    lastActivity: formatTimeAgo(job.updated_at),
  }));

  const filteredProjects = projects.filter((project) => {
    const matchesSearch = project.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesFilter =
      statusFilter === "all" || project.status === statusFilter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex-1 p-6 lg:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div className="space-y-3 mb-2">
            <div className="flex items-center justify-between">
              <div>
            <h1 className="text-4xl font-bold tracking-tight">Your Projects</h1>
            <p className="text-muted-foreground text-base">
              Build, manage, and deploy AI-powered applications
            </p>
          </div>
              {isDevMode && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handlePurgeJobs}
                  disabled={purgeJobsMutation.isPending}
                  className="gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  {purgeJobsMutation.isPending ? 'Purging...' : 'Purge All Jobs'}
                </Button>
              )}
            </div>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "jobs" | "apps")}>
            <TabsList>
              <TabsTrigger value="jobs">Jobs</TabsTrigger>
              <TabsTrigger value="apps">Apps</TabsTrigger>
            </TabsList>

            {/* Jobs Tab */}
            <TabsContent value="jobs" className="space-y-6">
          {/* Action Bar */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 sm:w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground z-10" />
              <Input
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-input/50 border-border/50 focus:border-border focus:ring-2 focus:ring-ring/20 transition-all"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="planning">Planning</SelectItem>
                <SelectItem value="building">Building</SelectItem>
                <SelectItem value="testing">Testing</SelectItem>
                <SelectItem value="complete">Complete</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={() => navigate("/create")}
              className="w-full sm:w-auto bg-gradient-primary text-primary-foreground font-medium shadow-md hover:shadow-lg transition-all duration-200"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Project
            </Button>
          </div>

        {/* Projects Grid */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-12 h-12 border-2 border-border border-t-primary rounded-full animate-spin mb-4"></div>
            <p className="text-muted-foreground">Loading projects...</p>
          </div>
        ) : filteredProjects.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project, index) => (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ProjectCard {...project} onDelete={handleDeleteJob} />
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 rounded-full bg-muted/30 border border-border/30 flex items-center justify-center mb-6">
              <Search className="w-8 h-8 text-muted-foreground" />
            </div>
            <h2 className="text-2xl font-semibold mb-3">No projects found</h2>
            <p className="text-muted-foreground mb-8 max-w-md">
              {searchQuery || statusFilter !== "all"
                ? "Try adjusting your search or filters"
                : "Create your first project to get started"}
            </p>
            {!searchQuery && statusFilter === "all" && (
              <Button 
                onClick={() => navigate("/create")}
                className="bg-gradient-primary text-primary-foreground font-medium shadow-md hover:shadow-lg transition-all duration-200"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Project
              </Button>
            )}
          </div>
        )}
            </TabsContent>

            {/* Apps Tab */}
            <TabsContent value="apps" className="space-y-6">
              {isLoadingApps ? (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                  <div className="w-12 h-12 border-2 border-border border-t-primary rounded-full animate-spin mb-4"></div>
                  <p className="text-muted-foreground">Loading apps...</p>
                </div>
              ) : apps && apps.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {apps.map((app, index) => (
                    <motion.div
                      key={app.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <Card className="glass hover:shadow-lg transition-shadow cursor-pointer"
                            onClick={() => navigate(`/build/${app.job_id}`)}>
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <CardTitle className="text-lg line-clamp-2">
                              {app.spec?.requirements?.substring(0, 50) || 'App'}
                              {app.spec?.requirements?.length > 50 ? '...' : ''}
                            </CardTitle>
                            <Badge variant="outline" className="bg-status-complete/10 text-status-complete border-status-complete/20">
                              Complete
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Calendar className="w-4 h-4" />
                            <span>Created {formatTimeAgo(app.created_at)}</span>
                          </div>
                          {app.spec?.summary && (
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {app.spec.summary}
                            </p>
                          )}
                          <div className="flex items-center gap-2 pt-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/build/${app.job_id}`);
                              }}
                            >
                              <ExternalLink className="w-4 h-4 mr-2" />
                              View Job
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/apps/${app.id}`);
                              }}
                            >
                              <Code className="w-4 h-4 mr-2" />
                              View App
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                  <div className="w-16 h-16 rounded-full bg-muted/30 border border-border/30 flex items-center justify-center mb-6">
                    <Code className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h2 className="text-2xl font-semibold mb-3">No apps found</h2>
                  <p className="text-muted-foreground mb-8 max-w-md">
                    Complete a project to see your apps here
                  </p>
                  <Button 
                    onClick={() => navigate("/create")}
                    className="bg-gradient-primary text-primary-foreground font-medium shadow-md hover:shadow-lg transition-all duration-200"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Project
                  </Button>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

