interface LivePreviewContentProps {
  device: "desktop" | "tablet" | "mobile";
  tickets?: any[];
}

export const LivePreviewContent = ({ device, tickets = [] }: LivePreviewContentProps) => {
  return (
    <div className="bg-background-elevated rounded-lg border border-border overflow-hidden w-full aspect-video flex flex-col">
      {/* Browser Controls */}
      <div className="flex items-center gap-2 p-2 bg-background-overlay border-b border-border">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-status-failed"></div>
          <div className="w-3 h-3 rounded-full bg-warning"></div>
          <div className="w-3 h-3 rounded-full bg-success"></div>
        </div>
        <div className="flex-1 bg-input rounded-md px-3 py-1.5 text-xs text-muted-foreground flex items-center gap-2">
          <span>🔒</span>
          <span>localhost:3000</span>
        </div>
      </div>

      {/* Preview Content - Mock Website */}
      <div className="flex-1 overflow-auto bg-background">
        <div className="min-h-full">
          {/* Header */}
          <header className="bg-background-elevated border-b border-border p-4">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold">My Application</h1>
              <nav className="flex gap-4">
                <a href="#" className="text-sm text-muted-foreground hover:text-foreground">Home</a>
                <a href="#" className="text-sm text-muted-foreground hover:text-foreground">Features</a>
                <a href="#" className="text-sm text-muted-foreground hover:text-foreground">About</a>
              </nav>
            </div>
          </header>

          {/* Hero Section */}
          <section className="p-8 text-center">
            <h2 className="text-3xl font-bold mb-4">Welcome to Your Application</h2>
            <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
              This is a preview of the application being built by the AI agents based on your requirements.
            </p>
            <button className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:opacity-90">
              Get Started
            </button>
          </section>

          {/* Features Grid */}
          <section className="p-8 bg-muted/30">
            <h3 className="text-2xl font-semibold mb-6 text-center">Features</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
              <div className="bg-card p-6 rounded-lg border border-border">
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-2xl">⚡</span>
                </div>
                <h4 className="font-semibold mb-2">Fast Performance</h4>
                <p className="text-sm text-muted-foreground">
                  Optimized for speed and efficiency
                </p>
              </div>
              <div className="bg-card p-6 rounded-lg border border-border">
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-2xl">🔒</span>
                </div>
                <h4 className="font-semibold mb-2">Secure</h4>
                <p className="text-sm text-muted-foreground">
                  Built with security best practices
                </p>
              </div>
              <div className="bg-card p-6 rounded-lg border border-border">
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-2xl">📱</span>
                </div>
                <h4 className="font-semibold mb-2">Responsive</h4>
                <p className="text-sm text-muted-foreground">
                  Works on all devices and screen sizes
                </p>
              </div>
            </div>
          </section>

          {/* Footer */}
          <footer className="bg-background-elevated border-t border-border p-6 mt-8">
            <div className="text-center text-sm text-muted-foreground">
              <p>© 2024 My Application. Built with AI assistance.</p>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
};

