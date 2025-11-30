import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { User, Mail, Calendar, Save, LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

export default function Profile() {
  const navigate = useNavigate();
  const { user: authUser, logout } = useAuth();
  const { data: user, isLoading } = useQuery({
    queryKey: ['currentUser'],
    queryFn: () => api.getCurrentUser(),
  });

  const displayUser = user || authUser;

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
  };

  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (email) {
      return email[0].toUpperCase();
    }
    return 'U';
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <div className="flex-1 p-6 lg:p-8 flex items-center justify-center">
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex-1 p-6 lg:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Profile Settings</h1>
            <p className="text-muted-foreground">
              Manage your account settings and preferences
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Profile Info */}
            <div className="lg:col-span-1 space-y-6">
              <Card className="glass">
                <CardContent className="p-6">
                  <div className="flex flex-col items-center space-y-4">
                    <div className="w-24 h-24 rounded-full bg-gradient-primary flex items-center justify-center text-2xl font-bold text-white">
                      {getInitials(displayUser?.name, displayUser?.email)}
                    </div>
                    <div className="text-center">
                      <h2 className="text-xl font-semibold">{displayUser?.name || "User"}</h2>
                      <p className="text-sm text-muted-foreground">{displayUser?.email}</p>
                    </div>
                    <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                      Active
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass">
                <CardHeader>
                  <CardTitle className="text-lg">Account Info</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3 text-sm">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-muted-foreground">Email</p>
                      <p className="font-medium">{displayUser?.email || "N/A"}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-muted-foreground">User ID</p>
                      <p className="font-medium font-mono text-xs">{displayUser?.id || "N/A"}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Column - Edit Form */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="glass">
                <CardHeader>
                  <CardTitle>Personal Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input id="name" defaultValue={displayUser?.name || ""} disabled />
                    <p className="text-xs text-muted-foreground">Name cannot be changed</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" type="email" defaultValue={displayUser?.email || ""} disabled />
                    <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="userId">User ID</Label>
                    <Input id="userId" defaultValue={displayUser?.id || ""} disabled className="font-mono text-xs" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass">
                <CardHeader>
                  <CardTitle>Security</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="currentPassword">Current Password</Label>
                    <Input id="currentPassword" type="password" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="newPassword">New Password</Label>
                    <Input id="newPassword" type="password" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm New Password</Label>
                    <Input id="confirmPassword" type="password" />
                  </div>
                  <Button variant="outline" className="mt-4">
                    Update Password
                  </Button>
                </CardContent>
              </Card>

              <Card className="glass border-destructive/20">
                <CardHeader>
                  <CardTitle className="text-destructive">Account Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Sign out of your account. You will need to log in again to access your projects.
                    </p>
                    <div className="flex gap-3">
                      <Button variant="destructive" onClick={async () => {
                        await logout();
                        toast.success("Logged out successfully");
                        navigate("/login");
                      }}>
                        <LogOut className="w-4 h-4 mr-2" />
                        Logout
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

