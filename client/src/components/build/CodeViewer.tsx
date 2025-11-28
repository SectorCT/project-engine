import { ScrollArea } from "@/components/ui/scroll-area";
import { File } from "lucide-react";

interface CodeViewerProps {
  filePath: string;
  content: string;
  language?: string;
}

// Mock code content for different files
const mockCodeContent: Record<string, string> = {
  "Header.tsx": `import React from 'react';
import { Button } from '@/components/ui/button';

export const Header = () => {
  return (
    <header className="border-b border-border bg-background-elevated">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Task Management App</h1>
        <nav className="flex items-center gap-4">
          <Button variant="ghost">Dashboard</Button>
          <Button variant="ghost">Tasks</Button>
          <Button variant="ghost">Settings</Button>
        </nav>
      </div>
    </header>
  );
};`,
  "Sidebar.tsx": `import React from 'react';
import { NavLink } from '@/components/NavLink';

export const Sidebar = () => {
  return (
    <aside className="w-64 border-r border-border bg-background-elevated">
      <nav className="p-4 space-y-2">
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/tasks">Tasks</NavLink>
        <NavLink to="/projects">Projects</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
    </aside>
  );
};`,
  "TaskList.tsx": `import React from 'react';
import { TaskCard } from '@/components/TaskCard';

interface Task {
  id: string;
  title: string;
  status: 'todo' | 'in-progress' | 'done';
}

export const TaskList = ({ tasks }: { tasks: Task[] }) => {
  return (
    <div className="space-y-2">
      {tasks.map(task => (
        <TaskCard key={task.id} task={task} />
      ))}
    </div>
  );
};`,
  "Dashboard.tsx": `import React from 'react';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { TaskList } from '@/components/TaskList';

export const Dashboard = () => {
  const tasks = [
    { id: '1', title: 'Design user interface', status: 'todo' },
    { id: '2', title: 'Set up database', status: 'todo' },
    { id: '3', title: 'Implement authentication', status: 'in-progress' },
  ];

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <Header />
        <TaskList tasks={tasks} />
      </main>
    </div>
  );
};`,
  "Settings.tsx": `import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export const Settings = () => {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Preferences</h2>
        <div className="space-y-4">
          <div>
            <label>Theme</label>
            <select className="w-full mt-2">
              <option>Dark</option>
              <option>Light</option>
            </select>
          </div>
          <Button>Save Changes</Button>
        </div>
      </Card>
    </div>
  );
};`,
  "utils.ts": `export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

export function cn(...classes: (string | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}`,
};

export const CodeViewer = ({ filePath, content, language }: CodeViewerProps) => {
  const fileName = filePath.split("/").pop() || filePath;
  const codeContent = content || mockCodeContent[fileName] || `// No content available for ${fileName}`;

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      <ScrollArea className="flex-1">
        <div className="p-4">
          <pre className="text-sm font-mono leading-relaxed">
            <code className="text-foreground whitespace-pre">{codeContent}</code>
          </pre>
        </div>
      </ScrollArea>
    </div>
  );
};

