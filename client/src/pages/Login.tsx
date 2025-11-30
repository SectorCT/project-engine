import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Github } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (element: HTMLElement, config: {
            type: string;
            text: string;
            theme?: string;
            size?: string;
            width?: string;
          }) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const particleVariants: any = {
  animate: {
    y: [0, -20, 0],
    opacity: [0.3, 0.6, 0.3],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

const Particle = ({ delay = 0 }: { delay?: number }) => (
  <motion.div
    className="absolute w-2 h-2 bg-foreground/20 rounded-full"
    variants={particleVariants}
    animate="animate"
    transition={{ delay }}
    style={{
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
    }}
  />
);

export default function Login() {
  const navigate = useNavigate();
  const { login, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const googleButtonContainerRef = useRef<HTMLDivElement>(null);

  const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, password);
      toast.success("Logged in successfully");
      navigate("/dashboard");
    } catch (error: any) {
      toast.error(error?.detail || error?.message || "Failed to login");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignIn = () => {
    if (!GOOGLE_CLIENT_ID) {
      toast.error("Google Sign-In is not configured");
      return;
    }

    if (!window.google?.accounts?.id) {
      toast.error("Google Sign-In is still loading. Please try again.");
      return;
    }

    // Find and click the hidden Google button
    const googleButton = googleButtonContainerRef.current?.querySelector('div[role="button"]') as HTMLElement;
    if (googleButton) {
      googleButton.click();
    } else {
      // Fallback: trigger the prompt directly
      window.google.accounts.id.prompt();
    }
  };

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !googleButtonContainerRef.current) {
      return;
    }

    // Wait for Google Identity Services to load
    const checkGoogleLoaded = setInterval(() => {
      if (window.google?.accounts?.id && googleButtonContainerRef.current) {
        clearInterval(checkGoogleLoaded);
        
        // Initialize Google Identity Services
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            setIsGoogleLoading(true);
            try {
              await loginWithGoogle(response.credential);
              toast.success("Logged in successfully with Google");
              navigate("/dashboard");
            } catch (error: any) {
              toast.error(error?.detail || error?.message || "Failed to login with Google");
              setIsGoogleLoading(false);
            }
          },
        });

        // Render Google button in hidden container
        try {
          window.google.accounts.id.renderButton(googleButtonContainerRef.current, {
            type: "standard",
            text: "signin_with",
            theme: "outline",
            size: "large",
          });
        } catch (error) {
          console.error("Error rendering Google button:", error);
        }
      }
    }, 100);

    return () => {
      clearInterval(checkGoogleLoaded);
    };
  }, [GOOGLE_CLIENT_ID, loginWithGoogle, navigate]);

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-gradient-dark">
      {/* Left Panel - Animated Background */}
      <div className="relative hidden lg:flex items-center justify-center p-12 overflow-hidden">
        <div className="absolute inset-0 bg-foreground/5"></div>
        {Array.from({ length: 20 }).map((_, i) => (
          <Particle key={i} delay={i * 0.1} />
        ))}
        <div className="relative z-10 text-center space-y-6">
          <div className="flex justify-center mb-4">
            <img 
              src="/logo.png" 
              alt="Project Engine" 
              className="h-24 w-auto"
            />
          </div>
          <p className="text-xl text-foreground/80">
            Watch AI Build Your Ideas in Real-Time
          </p>
          <p className="text-muted-foreground max-w-md">
            Multiple AI agents collaborating to build your software projects
          </p>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex items-center justify-center p-6 lg:p-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <div className="lg:hidden text-center mb-8">
            <div className="flex justify-center mb-4">
              <img 
                src="/logo.png" 
                alt="Project Engine" 
                className="h-20 w-auto"
              />
            </div>
            <p className="text-muted-foreground">
              Watch AI Build Your Ideas in Real-Time
            </p>
          </div>

          <Card className="glass">
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl text-center">Welcome back</CardTitle>
              <CardDescription className="text-center">
                Sign in to your account to continue
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    <a
                      href="#"
                      className="text-sm text-primary hover:underline"
                    >
                      Forgot password?
                    </a>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="remember"
                    checked={rememberMe}
                    onCheckedChange={(checked) =>
                      setRememberMe(checked === true)
                    }
                  />
                  <Label
                    htmlFor="remember"
                    className="text-sm font-normal cursor-pointer"
                  >
                    Remember me
                  </Label>
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? "Signing in..." : "Sign In"}
                </Button>
              </form>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-border"></span>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">OR</span>
                </div>
              </div>

              <div className="space-y-3">
                {/* Hidden Google button container */}
                <div ref={googleButtonContainerRef} className="hidden" aria-hidden="true" />
                
                <Button 
                  variant="outline" 
                  className="w-full" 
                  type="button" 
                  onClick={handleGoogleSignIn}
                  disabled={!GOOGLE_CLIENT_ID || isGoogleLoading}
                >
                  {isGoogleLoading ? (
                    "Signing in with Google..."
                  ) : (
                    <>
                      <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                        <path
                          fill="currentColor"
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        />
                        <path
                          fill="currentColor"
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        />
                        <path
                          fill="currentColor"
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                        />
                        <path
                          fill="currentColor"
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        />
                      </svg>
                      Continue with Google
                    </>
                  )}
                </Button>
                <Button variant="outline" className="w-full" type="button" disabled>
                  <Github className="w-4 h-4 mr-2" />
                  Continue with GitHub
                </Button>
              </div>

              <p className="mt-6 text-center text-sm text-muted-foreground">
                Don't have an account?{" "}
                <Link to="/register" className="text-primary hover:underline">
                  Sign up
                </Link>
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

