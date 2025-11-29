import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTheme } from "@/contexts/ThemeContext";
import { Palette, Moon, Sun, Monitor, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function Settings() {
  const { theme, colorScheme, setTheme, setColorScheme } = useTheme();

  const handleThemeChange = (newTheme: "dark" | "light" | "system") => {
    setTheme(newTheme);
    const displayTheme = newTheme === "system" ? "system (auto)" : newTheme;
    toast.success(`Switched to ${displayTheme} theme`);
  };

  const handleColorSchemeChange = (newScheme: "default" | "blue" | "green" | "purple") => {
    setColorScheme(newScheme);
    toast.success(`Color scheme changed to ${newScheme}`);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex-1 p-6 lg:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-muted-foreground">
              Customize your experience and preferences
            </p>
          </div>

          <div className="space-y-6">
            {/* Appearance Settings */}
            <Card className="glass">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Palette className="w-5 h-5" />
                  <CardTitle>Appearance</CardTitle>
                </div>
                <CardDescription>
                  Customize the look and feel of the application
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Theme Selection */}
                <div className="space-y-3">
                  <Label className="text-base font-semibold">Theme</Label>
                  <p className="text-sm text-muted-foreground">
                    Choose between dark and light themes
                  </p>
                  <RadioGroup
                    value={theme}
                    onValueChange={(value) => handleThemeChange(value as "dark" | "light" | "system")}
                    className="grid grid-cols-3 gap-4"
                  >
                    <label
                      className={`flex flex-col items-center justify-center rounded-lg border-2 p-4 cursor-pointer transition-all ${
                        theme === "dark"
                          ? "border-primary bg-primary/10"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      <RadioGroupItem value="dark" id="dark" className="sr-only" />
                      <Moon className="w-6 h-6 mb-2" />
                      <span className="text-sm font-medium">Dark</span>
                    </label>
                    <label
                      className={`flex flex-col items-center justify-center rounded-lg border-2 p-4 cursor-pointer transition-all ${
                        theme === "light"
                          ? "border-primary bg-primary/10"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      <RadioGroupItem value="light" id="light" className="sr-only" />
                      <Sun className="w-6 h-6 mb-2" />
                      <span className="text-sm font-medium">Light</span>
                    </label>
                    <label
                      className={`flex flex-col items-center justify-center rounded-lg border-2 p-4 cursor-pointer transition-all ${
                        theme === "system"
                          ? "border-primary bg-primary/10"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      <RadioGroupItem value="system" id="system" className="sr-only" />
                      <Monitor className="w-6 h-6 mb-2" />
                      <span className="text-sm font-medium">System</span>
                    </label>
                  </RadioGroup>
                </div>

                {/* Color Scheme Selection */}
                <div className="space-y-3">
                  <Label className="text-base font-semibold">Color Scheme</Label>
                  <p className="text-sm text-muted-foreground">
                    Choose your preferred accent color
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { value: "default", label: "Default", color: "bg-foreground" },
                      { value: "blue", label: "Blue", color: "bg-blue-500" },
                      { value: "green", label: "Green", color: "bg-green-500" },
                      { value: "purple", label: "Purple", color: "bg-purple-500" },
                    ].map((scheme) => (
                      <button
                        key={scheme.value}
                        onClick={() => handleColorSchemeChange(scheme.value as any)}
                        className={`flex flex-col items-center justify-center rounded-lg border-2 p-4 transition-all ${
                          colorScheme === scheme.value
                            ? "border-primary bg-primary/10"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        <div
                          className={`w-8 h-8 rounded-full ${scheme.color} mb-2 ${
                            scheme.value === "default"
                              ? "ring-2 ring-foreground ring-offset-2 ring-offset-background"
                              : ""
                          }`}
                        />
                        <span className="text-sm font-medium">{scheme.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Preferences */}
            <Card className="glass">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  <CardTitle>Preferences</CardTitle>
                </div>
                <CardDescription>
                  Configure application behavior and features
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <Label htmlFor="language" className="text-base font-semibold">
                    Language
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Select your preferred language
                  </p>
                  <Select defaultValue="en">
                    <SelectTrigger id="language" className="w-full md:w-[300px]">
                      <SelectValue placeholder="Select language" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Español</SelectItem>
                      <SelectItem value="fr">Français</SelectItem>
                      <SelectItem value="de">Deutsch</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-3">
                  <Label htmlFor="notifications" className="text-base font-semibold">
                    Notifications
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Manage notification preferences
                  </p>
                  <div className="space-y-2">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        defaultChecked
                        className="w-4 h-4 rounded border-input"
                      />
                      <span className="text-sm">Email notifications</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        defaultChecked
                        className="w-4 h-4 rounded border-input"
                      />
                      <span className="text-sm">Build status updates</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        className="w-4 h-4 rounded border-input"
                      />
                      <span className="text-sm">Marketing emails</span>
                    </label>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* About */}
            <Card className="glass">
              <CardHeader>
                <CardTitle>About</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Project Engine - AI-powered autonomous software development platform
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Version 1.0.0
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

