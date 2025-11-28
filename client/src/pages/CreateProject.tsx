import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ArrowRight, Sparkles, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProjectFormData {
  name: string;
  description: string;
  platform: "web" | "mobile" | "desktop";
  techStack: {
    frontend: string[];
    backend: string[];
    database: string[];
    other: string[];
  };
  complexity: "simple" | "medium" | "complex";
  features: string[];
}

const examplePrompts = [
  "A task management app with teams, projects, and real-time collaboration",
  "An e-commerce platform with inventory management and payment processing",
  "A social media dashboard with analytics and scheduling features",
];

const steps = [
  { id: 1, name: "Project Idea", description: "Describe what you want to build" },
  { id: 2, name: "Configuration", description: "Choose your tech preferences" },
  { id: 3, name: "Agent Assignment", description: "Review your AI team" },
  { id: 4, name: "Confirm & Launch", description: "Start building" },
];

export default function CreateProject() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<ProjectFormData>({
    name: "",
    description: "",
    platform: "web",
    techStack: {
      frontend: [],
      backend: [],
      database: [],
      other: [],
    },
    complexity: "medium",
    features: [],
  });

  const updateFormData = (updates: Partial<ProjectFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleLaunch = () => {
    // Mock project creation - navigate to live build
    navigate("/project/1");
  };

  const toggleTechStack = (
    category: keyof ProjectFormData["techStack"],
    value: string
  ) => {
    setFormData((prev) => {
      const current = prev.techStack[category];
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return {
        ...prev,
        techStack: { ...prev.techStack, [category]: updated },
      };
    });
  };

  const toggleFeature = (feature: string) => {
    setFormData((prev) => ({
      ...prev,
      features: prev.features.includes(feature)
        ? prev.features.filter((f) => f !== feature)
        : [...prev.features, feature],
    }));
  };

  const canProceed = () => {
    if (currentStep === 1) {
      return formData.description.length >= 20;
    }
    return true;
  };

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      <Navbar />
      <div className="flex-1 p-4 lg:p-6 overflow-hidden">
        <div className="max-w-6xl mx-auto h-full flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between mb-4 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold">Create New Project</h1>
                <p className="text-xs text-muted-foreground">
                  Step {currentStep} of 4
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              Cancel
            </Button>
          </div>

          {/* Progress Indicator */}
          <div className="mb-4 flex-shrink-0">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div
                      className={cn(
                        "w-12 h-12 rounded-full flex items-center justify-center font-semibold transition-all text-white",
                        currentStep >= step.id
                          ? "bg-gradient-primary shadow-lg"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {currentStep > step.id ? "✓" : step.id}
                    </div>
                    <div className="mt-3 text-center">
                      <p className="text-sm font-medium text-foreground">
                        {step.name}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {step.description}
                      </p>
                    </div>
                  </div>
                  {index < steps.length - 1 && (
                    <div
                      className={cn(
                        "h-1 flex-1 mx-4 transition-colors",
                        currentStep > step.id ? "bg-gradient-primary" : "bg-muted"
                      )}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

        <Card className="glass flex-1 flex flex-col min-h-0">
          <CardHeader className="flex-shrink-0 pb-3">
            <CardTitle className="text-lg">Step {currentStep}: {steps[currentStep - 1].name}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto p-4">
            <AnimatePresence mode="wait">
              {/* Step 1: Project Idea */}
              {currentStep === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="space-y-2">
                    <h2 className="text-2xl font-bold">What do you want to build?</h2>
                    <p className="text-sm text-muted-foreground">
                      Describe your project idea in detail. The more specific you are, the better our AI agents can help.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Textarea
                      id="description"
                      placeholder="Example: A real-time collaborative task management app with team workspaces, drag-and-drop kanban boards, integrated chat, and mobile responsiveness. Users should be able to assign tasks, set due dates, and receive notifications."
                      value={formData.description}
                      onChange={(e) =>
                        updateFormData({ description: e.target.value })
                      }
                      rows={8}
                      minLength={20}
                      className="text-sm resize-none"
                    />
                  </div>
                  <div className="space-y-2 pt-3 border-t border-border">
                    <div className="flex items-center gap-2">
                      <Lightbulb className="w-4 h-4 text-warning" />
                      <Label className="text-sm font-semibold">Example Prompts</Label>
                    </div>
                    <ul className="space-y-1.5 list-disc list-inside text-sm text-muted-foreground">
                      {examplePrompts.map((prompt, index) => (
                        <li
                          key={index}
                          className="cursor-pointer hover:text-foreground transition-colors"
                          onClick={() =>
                            updateFormData({ description: prompt })
                          }
                        >
                          {prompt}
                        </li>
                      ))}
                    </ul>
                  </div>
                </motion.div>
              )}

              {/* Step 2: Configuration */}
              {currentStep === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="space-y-2">
                    <Label className="text-sm">Platform</Label>
                    <RadioGroup
                      value={formData.platform}
                      onValueChange={(value: "web" | "mobile" | "desktop") =>
                        updateFormData({ platform: value })
                      }
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="web" id="web" />
                        <Label htmlFor="web" className="cursor-pointer">
                          Web App
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="mobile" id="mobile" />
                        <Label htmlFor="mobile" className="cursor-pointer">
                          Mobile App
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="desktop" id="desktop" />
                        <Label htmlFor="desktop" className="cursor-pointer">
                          Desktop App
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm">Tech Stack</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-sm">Frontend</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["React", "Vue", "Next.js", "Angular"].map(
                            (tech) => (
                              <Badge
                                key={tech}
                                variant={
                                  formData.techStack.frontend.includes(tech)
                                    ? "default"
                                    : "outline"
                                }
                                className="cursor-pointer"
                                onClick={() =>
                                  toggleTechStack("frontend", tech)
                                }
                              >
                                {tech}
                              </Badge>
                            )
                          )}
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm">Backend</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["Node.js", "Python", "Ruby", "Go"].map((tech) => (
                            <Badge
                              key={tech}
                              variant={
                                formData.techStack.backend.includes(tech)
                                  ? "default"
                                  : "outline"
                              }
                              className="cursor-pointer"
                              onClick={() => toggleTechStack("backend", tech)}
                            >
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm">Database</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["PostgreSQL", "MongoDB", "MySQL"].map((tech) => (
                            <Badge
                              key={tech}
                              variant={
                                formData.techStack.database.includes(tech)
                                  ? "default"
                                  : "outline"
                              }
                              className="cursor-pointer"
                              onClick={() => toggleTechStack("database", tech)}
                            >
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm">Other</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["TypeScript", "Tailwind CSS"].map((tech) => (
                            <Badge
                              key={tech}
                              variant={
                                formData.techStack.other.includes(tech)
                                  ? "default"
                                  : "outline"
                              }
                              className="cursor-pointer"
                              onClick={() => toggleTechStack("other", tech)}
                            >
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Complexity</Label>
                    <Select
                      value={formData.complexity}
                      onValueChange={(value: "simple" | "medium" | "complex") =>
                        updateFormData({ complexity: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="simple">
                          Simple - Basic CRUD, 1-2 weeks
                        </SelectItem>
                        <SelectItem value="medium">
                          Medium - Multiple features, 2-4 weeks
                        </SelectItem>
                        <SelectItem value="complex">
                          Complex - Advanced features, 4+ weeks
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm">Features</Label>
                    <div className="space-y-1.5">
                      {[
                        "Authentication",
                        "Payment Processing",
                        "Real-time Updates",
                        "File Upload",
                        "Email Notifications",
                        "Admin Dashboard",
                      ].map((feature) => (
                        <div key={feature} className="flex items-center space-x-2">
                          <Checkbox
                            id={feature}
                            checked={formData.features.includes(feature)}
                            onCheckedChange={() => toggleFeature(feature)}
                          />
                          <Label
                            htmlFor={feature}
                            className="cursor-pointer font-normal"
                          >
                            {feature}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Step 3: Preview */}
              {currentStep === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="space-y-3">
                    <div>
                      <h3 className="text-sm font-semibold mb-2">Project Summary</h3>
                      <div className="bg-muted/30 p-3 rounded-lg space-y-1.5 text-xs">
                        <p>
                          <span className="font-medium">Name:</span>{" "}
                          {formData.name}
                        </p>
                        <p>
                          <span className="font-medium">Platform:</span>{" "}
                          {formData.platform}
                        </p>
                        <p>
                          <span className="font-medium">Complexity:</span>{" "}
                          {formData.complexity}
                        </p>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold mb-2">Agents</h3>
                      <div className="space-y-1.5">
                        {[
                          "Business Analyst",
                          "Project Manager",
                          "Architect",
                          "Developers (1-3)",
                          "QA Tester",
                        ].map((role) => (
                          <div
                            key={role}
                            className="flex items-center gap-2 p-1.5 bg-muted/30 rounded"
                          >
                            <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-semibold">
                              {role.charAt(0)}
                            </div>
                            <span className="text-xs">{role}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Step 4: Launch */}
              {currentStep === 4 && (
                <motion.div
                  key="step4"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="text-center space-y-3">
                    <div className="flex justify-center">
                      <Sparkles className="w-12 h-12 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold">
                      Ready to Start Building?
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Your project will be created and AI agents will begin
                      working immediately.
                    </p>
                  </div>
                  <div className="bg-muted/30 p-3 rounded-lg space-y-1.5 text-xs">
                    <p>
                      <span className="font-medium">Estimated Time:</span>{" "}
                      {formData.complexity === "simple"
                        ? "1-2 weeks"
                        : formData.complexity === "medium"
                        ? "2-4 weeks"
                        : "4+ weeks"}
                    </p>
                    <p>
                      <span className="font-medium">Estimated Cost:</span> $50-200
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="terms" />
                    <Label htmlFor="terms" className="cursor-pointer text-sm">
                      I agree to the terms of service
                    </Label>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Navigation */}
            <div className="flex justify-between mt-4 pt-4 border-t border-border flex-shrink-0">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBack}
                disabled={currentStep === 1}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Cancel
              </Button>
              {currentStep < 4 ? (
                <Button 
                  onClick={handleNext} 
                  disabled={!canProceed()}
                  size="sm"
                  className="bg-gradient-primary hover:opacity-90 text-white"
                >
                  Next
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button 
                  onClick={handleLaunch} 
                  size="default"
                  className="bg-gradient-primary hover:opacity-90 text-white"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Start Building
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        </div>
      </div>
    </div>
  );
}

