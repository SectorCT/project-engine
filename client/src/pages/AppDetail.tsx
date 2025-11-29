import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ArrowLeft,
  Code,
  FileText,
  Calendar,
  ExternalLink,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatTimeAgo } from "@/lib/jobUtils";
import { toast } from "sonner";

export default function AppDetail() {
  const { appId } = useParams<{ appId: string }>();
  const navigate = useNavigate();

  const { data: app, isLoading, error } = useQuery({
    queryKey: ['app', appId],
    queryFn: () => api.getApp(appId!),
    enabled: !!appId,
  });

  const handleDownloadSpec = () => {
    if (!app?.spec) return;

    const dataStr = JSON.stringify(app.spec, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `app-spec-${appId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success('App spec downloaded');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading app...</p>
      </div>
    );
  }

  if (error || !app) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-destructive mb-4">Failed to load app</p>
          <Button onClick={() => navigate("/dashboard")}>Go to Dashboard</Button>
        </div>
      </div>
    );
  }

  const appTitle = app.spec?.requirements?.substring(0, 50) || 'App';
  const appTitleFull = app.spec?.requirements || 'No description available';

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex-1 p-6 lg:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate("/dashboard")}
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  {appTitle}
                  {app.spec?.requirements?.length > 50 ? '...' : ''}
                </h1>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline" className="bg-status-complete/10 text-status-complete border-status-complete/20">
                    Complete
                  </Badge>
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    Created {formatTimeAgo(app.created_at)}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {app.job_id && (
                <Button
                  variant="outline"
                  onClick={() => navigate(`/build/${app.job_id}`)}
                  className="gap-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Job
                </Button>
              )}
              <Button
                variant="outline"
                onClick={handleDownloadSpec}
                className="gap-2"
              >
                <Download className="w-4 h-4" />
                Download Spec
              </Button>
            </div>
          </div>

          {/* Content Tabs */}
          <Tabs defaultValue="spec" className="space-y-4">
            <TabsList>
              <TabsTrigger value="spec" className="gap-2">
                <Code className="w-4 h-4" />
                App Spec
              </TabsTrigger>
              <TabsTrigger value="requirements" className="gap-2">
                <FileText className="w-4 h-4" />
                Requirements
              </TabsTrigger>
              {app.spec?.discussion && (
                <TabsTrigger value="discussion" className="gap-2">
                  <FileText className="w-4 h-4" />
                  Discussion
                </TabsTrigger>
              )}
              {app.spec?.summary && (
                <TabsTrigger value="summary" className="gap-2">
                  <FileText className="w-4 h-4" />
                  Summary
                </TabsTrigger>
              )}
            </TabsList>

            {/* App Spec Tab */}
            <TabsContent value="spec">
              <Card className="glass">
                <CardHeader>
                  <CardTitle>Application Specification</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[600px]">
                    <pre className="text-xs font-mono bg-muted/30 p-4 rounded-md overflow-auto">
                      {JSON.stringify(app.spec, null, 2)}
                    </pre>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Requirements Tab */}
            <TabsContent value="requirements">
              <Card className="glass">
                <CardHeader>
                  <CardTitle>Requirements</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[600px]">
                    <div className="prose prose-invert max-w-none">
                      <p className="text-sm whitespace-pre-wrap">
                        {app.spec?.requirements || 'No requirements available'}
                      </p>
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Discussion Tab */}
            {app.spec?.discussion && (
              <TabsContent value="discussion">
                <Card className="glass">
                  <CardHeader>
                    <CardTitle>Executive Discussion</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[600px]">
                      <div className="space-y-4">
                        {Array.isArray(app.spec.discussion) ? (
                          app.spec.discussion.map((entry: any, index: number) => (
                            <div
                              key={index}
                              className="border border-border rounded-lg p-4 bg-muted/20"
                            >
                              <div className="flex items-center gap-2 mb-2">
                                <Badge variant="outline">{entry.agent || 'Agent'}</Badge>
                                <span className="text-xs text-muted-foreground">
                                  Entry {index + 1}
                                </span>
                              </div>
                              <p className="text-sm whitespace-pre-wrap">
                                {entry.content || entry.message || JSON.stringify(entry, null, 2)}
                              </p>
                            </div>
                          ))
                        ) : (
                          <pre className="text-xs font-mono bg-muted/30 p-4 rounded-md overflow-auto">
                            {JSON.stringify(app.spec.discussion, null, 2)}
                          </pre>
                        )}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>
            )}

            {/* Summary Tab */}
            {app.spec?.summary && (
              <TabsContent value="summary">
                <Card className="glass">
                  <CardHeader>
                    <CardTitle>Project Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[600px]">
                      <div className="prose prose-invert max-w-none">
                        <p className="text-sm whitespace-pre-wrap">
                          {app.spec.summary}
                        </p>
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>
        </div>
      </div>
    </div>
  );
}

