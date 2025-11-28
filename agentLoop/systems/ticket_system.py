import os
import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime

class TicketSystem:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI")
        self.use_mongo = False
        self.db = None
        self.collection = None
        self.local_file = "project_data/tickets.json"
        
        # Try to connect to MongoDB if URI is provided
        if self.mongo_uri:
            try:
                from pymongo import MongoClient
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                self.client.server_info() # Trigger connection to check status
                self.db = self.client.get_database("project_engine")
                self.collection = self.db.get_collection("tickets")
                self.use_mongo = True
                print("Connected to Ticket System (MongoDB)")
            except Exception as e:
                print(f"MongoDB connection failed: {e}. Falling back to local JSON.")
                self.use_mongo = False
        else:
            print("No MONGO_URI found. Using local JSON ticket system.")
            
        if not self.use_mongo:
            self._ensure_local_file()

    def _ensure_local_file(self):
        if not os.path.exists("project_data"):
            os.makedirs("project_data")
        if not os.path.exists(self.local_file):
            with open(self.local_file, 'w') as f:
                json.dump([], f)

    def create_ticket(self, type: str, title: str, description: str, assigned_to: str = "Unassigned", dependencies: List[str] = [], parent_id: Optional[str] = None) -> str:
        """
        Create a new ticket (Epic or Story) and save it.
        Returns the Ticket ID.
        """
        ticket_id = str(uuid.uuid4())[:8]
        ticket = {
            "id": ticket_id,
            "type": type, # "epic" or "story"
            "title": title,
            "description": description,
            "status": "todo",
            "assigned_to": assigned_to,
            "dependencies": dependencies,
            "parent_id": parent_id,
            "created_at": datetime.now().isoformat()
        }

        if self.use_mongo:
            # Let MongoDB generate the _id, but keep our ID as 'id' or use _id as the main ID
            # For simplicity, we'll insert and then update the 'id' to match _id if we want strictly mongo IDs
            del ticket['id']
            result = self.collection.insert_one(ticket)
            ticket_id = str(result.inserted_id)
        else:
            self._save_local_ticket(ticket)
            
        return ticket_id

    def update_ticket_dependencies(self, ticket_id: str, new_dependencies: List[str]):
        # Convert string IDs to ObjectIds for MongoDB
        if self.use_mongo:
            from bson.objectid import ObjectId
            try:
                oid = ObjectId(ticket_id)
                # Convert dependency strings to ObjectIds
                dep_objectids = []
                for dep_id in new_dependencies:
                    try:
                        dep_objectids.append(ObjectId(dep_id))
                    except:
                        # If it's not a valid ObjectId string, skip it
                        pass
                
                self.collection.update_one(
                    {"_id": oid},
                    {"$set": {"dependencies": dep_objectids}}
                )
            except:
                self.collection.update_one(
                    {"id": ticket_id},
                    {"$set": {"dependencies": new_dependencies}}
                )
        else:
            with open(self.local_file, 'r') as f:
                tickets = json.load(f)
            
            for t in tickets:
                if t.get('id') == ticket_id:
                    t['dependencies'] = new_dependencies
                    break
            
            with open(self.local_file, 'w') as f:
                json.dump(tickets, f, indent=2)

    def update_ticket_parent(self, ticket_id: str, parent_id: str):
        if self.use_mongo:
            from bson.objectid import ObjectId
            try:
                oid = ObjectId(ticket_id)
                # Convert parent_id string to ObjectId
                try:
                    parent_oid = ObjectId(parent_id)
                    self.collection.update_one(
                        {"_id": oid},
                        {"$set": {"parent_id": parent_oid}}
                    )
                except:
                    # If parent_id is not a valid ObjectId, skip
                    pass
            except:
                self.collection.update_one(
                    {"id": ticket_id},
                    {"$set": {"parent_id": parent_id}}
                )
        else:
            with open(self.local_file, 'r') as f:
                tickets = json.load(f)
            
            for t in tickets:
                if t.get('id') == ticket_id:
                    t['parent_id'] = parent_id
                    break
            
            with open(self.local_file, 'w') as f:
                json.dump(tickets, f, indent=2)

    def _save_local_ticket(self, ticket: Dict):
        with open(self.local_file, 'r') as f:
            tickets = json.load(f)
        tickets.append(ticket)
        with open(self.local_file, 'w') as f:
            json.dump(tickets, f, indent=2)

    def get_tickets(self) -> List[Dict]:
        if self.use_mongo:
            # Convert ObjectIds to strings for consistent output
            tickets = list(self.collection.find({}))
            for t in tickets:
                t['_id'] = str(t['_id'])
                # If we have dependencies or parent_id as string, that's fine.
            return tickets
        else:
            with open(self.local_file, 'r') as f:
                return json.load(f)
