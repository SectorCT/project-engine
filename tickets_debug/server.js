require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

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

// Start server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});

