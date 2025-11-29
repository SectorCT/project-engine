require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const path = require('path');
const Docker = require('dockerode');

const app = express();
const PORT = process.env.PORT || 3000;

// Docker client
const docker = new Docker();

// Helper function to get container name from project_id
function getContainerName(projectId) {
    if (projectId) {
        return `project_engine_${projectId}_container`;
    }
    return 'project_engine_builder_container'; // Default for backward compatibility
}

// File watching state (per project)
let fileWatchers = new Map(); // projectId -> { previousFileState, isWatching, watchInterval }

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// MongoDB Connection
const connectDB = async () => {
    try {
        if (!process.env.MONGO_URI) {
            console.error('MONGO_URI is not defined in environment variables');
            return;
        }
        await mongoose.connect(process.env.MONGO_URI);
        console.log('MongoDB Connected');
    } catch (err) {
        console.error('MongoDB connection error:', err);
    }
};

connectDB();

// Ticket Schema
// Using strict: false to allow flexibility if the schema evolves
const ticketSchema = new mongoose.Schema({
    type: String,
    title: String,
    description: String,
    status: String,
    assigned_to: String,
    dependencies: [String], // Storing IDs as strings based on python code
    created_at: Date
}, { strict: false });

const Ticket = mongoose.model('Ticket', ticketSchema, 'tickets'); // Collection name 'tickets'

// API Routes

// Get all tickets
app.get('/api/tickets', async (req, res) => {
    try {
        const tickets = await Ticket.find().lean();
        // Convert ObjectIds to strings for frontend
        const formattedTickets = tickets.map(t => ({
            ...t,
            id: t._id.toString(),
            _id: t._id.toString(), // Keep _id as string too
            // Convert dependencies array from ObjectIds to strings
            dependencies: (t.dependencies || []).map(dep => {
                if (dep && typeof dep === 'object' && dep.toString) {
                    return dep.toString();
                }
                return String(dep);
            }),
            // Convert parent_id from ObjectId to string
            parent_id: t.parent_id ? (typeof t.parent_id === 'object' && t.parent_id.toString ? t.parent_id.toString() : String(t.parent_id)) : null
        }));
        res.json(formattedTickets);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Get single ticket
app.get('/api/tickets/:id', async (req, res) => {
    try {
        const ticket = await Ticket.findById(req.params.id);
        if (!ticket) return res.status(404).json({ message: 'Ticket not found' });
        res.json(ticket);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Docker file system API

// Get file structure from Docker container
app.get('/api/files/structure', async (req, res) => {
    try {
        const projectId = req.query.project_id || null;
        const containerName = getContainerName(projectId);
        const container = docker.getContainer(containerName);
        
        // Check if container exists and is running
        try {
            const containerInfo = await container.inspect();
            if (containerInfo.State.Status !== 'running') {
                return res.status(503).json({ error: 'Container is not running', status: containerInfo.State.Status });
            }
        } catch (err) {
            return res.status(404).json({ error: 'Container not found', details: err.message });
        }
        
        // Get file structure using find command
        // First get all files, then get all directories (including empty ones)
        const path = req.query.path || '/app';
        
        // Get files
        const execFiles = await container.exec({
            Cmd: ['sh', '-c', `find ${path} -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" | head -200`],
            AttachStdout: true,
            AttachStderr: true,
            WorkingDir: '/app'
        });
        
        const streamFiles = await execFiles.start({ hijack: true, stdin: false });
        let outputFiles = '';
        streamFiles.on('data', (chunk) => {
            outputFiles += chunk.toString();
        });
        await new Promise((resolve, reject) => {
            streamFiles.on('end', resolve);
            streamFiles.on('error', reject);
        });
        
        // Get directories (including empty ones)
        const execDirs = await container.exec({
            Cmd: ['sh', '-c', `find ${path} -type d -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" | head -200`],
            AttachStdout: true,
            AttachStderr: true,
            WorkingDir: '/app'
        });
        
        const streamDirs = await execDirs.start({ hijack: true, stdin: false });
        let outputDirs = '';
        streamDirs.on('data', (chunk) => {
            outputDirs += chunk.toString();
        });
        await new Promise((resolve, reject) => {
            streamDirs.on('end', resolve);
            streamDirs.on('error', reject);
        });
        
        const files = outputFiles.split('\n').filter(line => line.trim()).map(line => line.trim());
        const dirs = outputDirs.split('\n').filter(line => line.trim()).map(line => line.trim());
        
        // Build tree structure
        const tree = {};
        
        // First, add all directories to the tree
        for (const dirPath of dirs) {
            const relPath = dirPath.replace('/app', '').replace(/^\//, '');
            if (!relPath) continue;
            
            const parts = relPath.split('/').filter(part => part !== '.' && part !== '..');
            if (parts.length === 0) continue;
            
            let current = tree;
            
            for (let i = 0; i < parts.length; i++) {
                const part = parts[i];
                
                if (!current) break;
                
                // Skip . and .. directories
                if (part === '.' || part === '..') continue;
                
                if (!current[part]) {
                    current[part] = {
                        name: part,
                        path: null, // Directories never have paths
                        type: 'dir',
                        children: {}
                    };
                }
                
                if (!current[part].children) {
                    current[part].children = {};
                }
                current = current[part].children;
            }
        }
        
        // Then, add files and mark them as files
        for (const filePath of files) {
            const relPath = filePath.replace('/app', '').replace(/^\//, '');
            if (!relPath) continue;
            
            const parts = relPath.split('/').filter(part => part !== '.' && part !== '..');
            if (parts.length === 0) continue;
            
            let current = tree;
            
            for (let i = 0; i < parts.length; i++) {
                const part = parts[i];
                const isFile = i === parts.length - 1;
                
                if (!current) break;
                
                // Skip . and .. directories
                if (part === '.' || part === '..') continue;
                
                if (!current[part]) {
                    current[part] = {
                        name: part,
                        path: isFile ? filePath : null,
                        type: isFile ? 'file' : 'dir',
                        children: isFile ? null : {}
                    };
                } else {
                    // If it exists as a directory but is actually a file, convert it
                    if (current[part].type === 'dir' && isFile) {
                        current[part].type = 'file';
                        current[part].path = filePath;
                        current[part].children = null;
                    }
                }
                
                if (!isFile) {
                    if (!current[part].children) {
                        current[part].children = {};
                    }
                    current = current[part].children;
                }
            }
        }
        
        // Convert to list format
        function dictToList(d) {
            const result = [];
            for (const key of Object.keys(d).sort()) {
                const item = {
                    name: d[key].name,
                    path: d[key].path,
                    type: d[key].type
                };
                if (d[key].type === 'dir' && d[key].children) {
                    item.children = dictToList(d[key].children);
                }
                result.push(item);
            }
            return result;
        }
        
        const structure = dictToList(tree);
        res.json({ structure: structure || [] });
    } catch (err) {
        console.error('Error getting file structure:', err);
        res.status(500).json({ error: err.message, structure: [] });
    }
});

// Read file content from Docker container
app.get('/api/files/content', async (req, res) => {
    try {
        const filePath = req.query.path;
        if (!filePath) {
            return res.status(400).json({ error: 'File path is required' });
        }
        
        const projectId = req.query.project_id || null;
        const containerName = getContainerName(projectId);
        const container = docker.getContainer(containerName);
        
        // Check if container exists and is running
        try {
            const containerInfo = await container.inspect();
            if (containerInfo.State.Status !== 'running') {
                return res.status(503).json({ error: 'Container is not running', status: containerInfo.State.Status });
            }
        } catch (err) {
            return res.status(404).json({ error: 'Container not found', details: err.message });
        }
        
        // Read file using cat
        const exec = await container.exec({
            Cmd: ['cat', filePath],
            AttachStdout: true,
            AttachStderr: true,
            WorkingDir: '/app'
        });
        
        const stream = await exec.start({ hijack: true, stdin: false });
        
        let output = '';
        stream.on('data', (chunk) => {
            output += chunk.toString();
        });
        
        await new Promise((resolve, reject) => {
            stream.on('end', resolve);
            stream.on('error', reject);
        });
        
        // Check exit code
        const inspect = await exec.inspect();
        if (inspect.ExitCode !== 0) {
            return res.status(404).json({ error: 'File not found or cannot be read', details: output });
        }
        
        res.json({ 
            path: filePath,
            content: output || '',
            size: output ? output.length : 0
        });
    } catch (err) {
        console.error('Error reading file:', err);
        res.status(500).json({ error: err.message, content: '', size: 0 });
    }
});

// Save file content to Docker container
app.post('/api/files/save', async (req, res) => {
    try {
        const filePath = req.query.path;
        if (!filePath) {
            return res.status(400).json({ error: 'File path is required' });
        }
        
        const content = req.body.content;
        if (content === undefined) {
            return res.status(400).json({ error: 'File content is required' });
        }
        
        const projectId = req.query.project_id || null;
        const containerName = getContainerName(projectId);
        const container = docker.getContainer(containerName);
        
        // Check if container exists and is running
        try {
            const containerInfo = await container.inspect();
            if (containerInfo.State.Status !== 'running') {
                return res.status(503).json({ error: 'Container is not running', status: containerInfo.State.Status });
            }
        } catch (err) {
            return res.status(404).json({ error: 'Container not found', details: err.message });
        }
        
        // Write file using base64 encoding to handle special characters
        // We'll use Python to write the file reliably
        // Escape single quotes in file path for shell safety
        const escapedPath = filePath.replace(/'/g, "'\"'\"'");
        const contentBase64 = Buffer.from(content, 'utf-8').toString('base64');
        const pythonCmd = `python3 -c "import base64; open('${escapedPath}', 'wb').write(base64.b64decode('${contentBase64}'))"`;
        
        const exec = await container.exec({
            Cmd: ['sh', '-c', pythonCmd],
            AttachStdout: true,
            AttachStderr: true,
            WorkingDir: '/app'
        });
        
        const stream = await exec.start({ hijack: true, stdin: false });
        
        let output = '';
        let errorOutput = '';
        
        // Docker streams combine stdout and stderr
        stream.on('data', (chunk) => {
            const data = chunk.toString();
            output += data;
        });
        
        await new Promise((resolve, reject) => {
            stream.on('end', resolve);
            stream.on('error', reject);
        });
        
        // Check exit code
        const execInfo = await exec.inspect();
        if (execInfo.ExitCode !== 0) {
            return res.status(500).json({ 
                error: 'Failed to save file', 
                details: output || 'Unknown error' 
            });
        }
        
        res.json({ success: true, message: 'File saved successfully' });
    } catch (err) {
        console.error('Error saving file:', err);
        res.status(500).json({ error: err.message });
    }
});

// File watching functions

/**
 * Get current file state from Docker container
 * Returns a Map of file paths to { mtime, size }
 */
async function getCurrentFileState(projectId) {
    try {
        const containerName = getContainerName(projectId);
        const container = docker.getContainer(containerName);
        
        // Check if container exists and is running
        try {
            const containerInfo = await container.inspect();
            if (containerInfo.State.Status !== 'running') {
                return null; // Container not running
            }
        } catch (err) {
            return null; // Container not found
        }
        
        // Get files with modification times and sizes
        // Using find with stat to get mtime and size
        // Format: "mtime|size|path" for easier parsing
        const exec = await container.exec({
            Cmd: ['sh', '-c', `find /app -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" -exec sh -c 'stat -c "%Y|%s|%n" "$1"' _ {} \\; | head -500`],
            AttachStdout: true,
            AttachStderr: true,
            WorkingDir: '/app'
        });
        
        const stream = await exec.start({ hijack: true, stdin: false });
        
        let output = '';
        stream.on('data', (chunk) => {
            output += chunk.toString();
        });
        
        await new Promise((resolve, reject) => {
            stream.on('end', resolve);
            stream.on('error', reject);
        });
        
        const fileState = new Map();
        const lines = output.split('\n').filter(line => line.trim());
        
        for (const line of lines) {
            // Format: "mtime|size|path"
            const parts = line.trim().split('|');
            if (parts.length >= 3) {
                const mtime = parseInt(parts[0]);
                const size = parseInt(parts[1]);
                const path = parts.slice(2).join('|'); // Rejoin in case path contains |
                if (path && !isNaN(mtime) && !isNaN(size)) {
                    fileState.set(path, { mtime, size });
                }
            }
        }
        
        return fileState;
    } catch (err) {
        console.error('Error getting file state:', err);
        return null;
    }
}

/**
 * Compare file states and detect changes
 */
function detectFileChanges(currentState, previousState) {
    const changes = [];
    
    if (!currentState) return changes;
    
    // Check for new or modified files
    for (const [path, currentInfo] of currentState.entries()) {
        const previousInfo = previousState.get(path);
        
        if (!previousInfo) {
            // New file
            changes.push({ type: 'created', path, mtime: currentInfo.mtime, size: currentInfo.size });
        } else if (previousInfo.mtime !== currentInfo.mtime || previousInfo.size !== currentInfo.size) {
            // Modified file
            changes.push({ 
                type: 'modified', 
                path, 
                mtime: currentInfo.mtime, 
                size: currentInfo.size,
                previousMtime: previousInfo.mtime,
                previousSize: previousInfo.size
            });
        }
    }
    
    // Check for deleted files
    for (const [path] of previousState.entries()) {
        if (!currentState.has(path)) {
            changes.push({ type: 'deleted', path });
        }
    }
    
    return changes;
}

/**
 * Start file watching (polling-based) for a specific project
 */
function startFileWatcher(projectId) {
    const watcherKey = projectId || 'default';
    
    // Check if watcher already exists for this project
    if (fileWatchers.has(watcherKey) && fileWatchers.get(watcherKey).isWatching) {
        return; // Already watching
    }
    
    const POLL_INTERVAL = 2000; // Check every 2 seconds
    const previousFileState = new Map();
    let isWatching = true;
    
    console.log(`Starting file watcher for project: ${projectId || 'default'} (container: ${getContainerName(projectId)})...`);
    
    // Initial state
    getCurrentFileState(projectId).then(state => {
        if (state) {
            for (const [path, info] of state.entries()) {
                previousFileState.set(path, info);
            }
            console.log(`File watcher initialized with ${state.size} files for project: ${projectId || 'default'}`);
        }
    });
    
    // Poll for changes
    const watchInterval = setInterval(async () => {
        const currentState = await getCurrentFileState(projectId);
        
        if (!currentState) {
            // Container not running, skip this check
            return;
        }
        
        const changes = detectFileChanges(currentState, previousFileState);
        
        if (changes.length > 0) {
            // TO DO integrate with sockets
            for (const change of changes) {
                if (change.type === 'created') {
                    console.log(`[${projectId || 'default'}] [FILE CREATED] ${change.path} (size: ${change.size} bytes, mtime: ${new Date(change.mtime * 1000).toISOString()})`);
                } else if (change.type === 'modified') {
                    console.log(`[${projectId || 'default'}] [FILE MODIFIED] ${change.path} (size: ${change.size} bytes, mtime: ${new Date(change.mtime * 1000).toISOString()})`);
                } else if (change.type === 'deleted') {
                    console.log(`[${projectId || 'default'}] [FILE DELETED] ${change.path}`);
                }
            }
        }
        
        // Update previous state
        previousFileState.clear();
        for (const [path, info] of currentState.entries()) {
            previousFileState.set(path, info);
        }
    }, POLL_INTERVAL);
    
    // Store watcher state
    fileWatchers.set(watcherKey, {
        previousFileState,
        isWatching,
        watchInterval
    });
    
    // Cleanup on exit
    process.on('SIGINT', () => {
        if (fileWatchers.has(watcherKey)) {
            clearInterval(fileWatchers.get(watcherKey).watchInterval);
            fileWatchers.delete(watcherKey);
        }
    });
}

/**
 * Stop file watcher for a specific project
 */
function stopFileWatcher(projectId) {
    const watcherKey = projectId || 'default';
    if (fileWatchers.has(watcherKey)) {
        clearInterval(fileWatchers.get(watcherKey).watchInterval);
        fileWatchers.delete(watcherKey);
        console.log(`Stopped file watcher for project: ${projectId || 'default'}`);
    }
}

// API endpoint to start/stop file watcher for a project
app.post('/api/files/watch', (req, res) => {
    const { project_id, action } = req.body;
    if (action === 'start') {
        startFileWatcher(project_id || null);
        res.json({ message: `File watcher started for project: ${project_id || 'default'}` });
    } else if (action === 'stop') {
        stopFileWatcher(project_id || null);
        res.json({ message: `File watcher stopped for project: ${project_id || 'default'}` });
    } else {
        res.status(400).json({ error: 'Invalid action. Use "start" or "stop"' });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    // Note: File watchers are started on-demand via API or frontend
});

