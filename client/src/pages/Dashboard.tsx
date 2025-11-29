import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { ProjectCard } from "@/components/ProjectCard";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Search, Filter } from "lucide-react";
import { api } from "@/lib/api";
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

  const queryClient = useQueryClient();
  
  const { data: jobs, isLoading, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.getJobs(),
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
            <h1 className="text-4xl font-bold tracking-tight">Your Projects</h1>
            <p className="text-muted-foreground text-base">
              Build, manage, and deploy AI-powered applications
            </p>
          </div>

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
        </div>
      </div>
    </div>
  );
}

