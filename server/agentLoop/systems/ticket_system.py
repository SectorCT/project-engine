from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

try:  # Optional dependency so this module still works in CLI-only mode
    from django.apps import apps
    from django.core.exceptions import AppRegistryNotReady
except ImportError:  # pragma: no cover - happens outside Django
    apps = None
    AppRegistryNotReady = Exception  # type: ignore


class TicketSystem:
    """
    Persists tickets either via the Django ORM (preferred) or a local JSON file
    when Django isn't available (standalone CLI/dev usage).
    """

    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id
        self._use_django = False
        self._ticket_model = None
        self._job = None

        if self.job_id and apps is not None:
            try:
                self._ticket_model = apps.get_model('jobs', 'Ticket')
                job_model = apps.get_model('jobs', 'Job')
                self._job = job_model.objects.get(id=self.job_id)
                self._use_django = True
            except (LookupError, AppRegistryNotReady, Exception):
                # Fall back to local storage if Django apps aren't ready yet
                self._use_django = False

        if not self._use_django:
            self.local_file = os.path.join('project_data', 'tickets.json')
            self._ensure_local_file()

    # --------------------------------------------------------------------- #
    # Django-backed helpers
    # --------------------------------------------------------------------- #
    def _create_ticket_django(
        self,
        *,
        type: str,
        title: str,
        description: str,
        assigned_to: str,
    ) -> str:
        ticket = self._ticket_model.objects.create(
            job=self._job,
            type=type,
            title=title,
            description=description,
            assigned_to=assigned_to,
            status='todo',
        )
        return str(ticket.id)

    def _update_dependencies_django(self, ticket_id: str, dependencies: List[str]) -> None:
        ticket = self._ticket_model.objects.get(id=ticket_id, job=self._job)
        dep_qs = self._ticket_model.objects.filter(id__in=dependencies, job=self._job)
        ticket.dependencies.set(dep_qs)

    def _update_parent_django(self, ticket_id: str, parent_id: str) -> None:
        ticket = self._ticket_model.objects.get(id=ticket_id, job=self._job)
        parent = None
        if parent_id:
            parent = self._ticket_model.objects.filter(id=parent_id, job=self._job).first()
        ticket.parent = parent
        ticket.save(update_fields=['parent'])

    def _get_tickets_django(self) -> List[Dict[str, Any]]:
        tickets: List[Dict[str, Any]] = []
        for ticket in self._ticket_model.objects.filter(job=self._job).prefetch_related('dependencies'):
            tickets.append(
                {
                    "id": str(ticket.id),
                    "type": ticket.type,
                    "title": ticket.title,
                    "description": ticket.description,
                    "status": ticket.status,
                    "assigned_to": ticket.assigned_to,
                    "dependencies": [str(dep.id) for dep in ticket.dependencies.all()],
                    "parent_id": str(ticket.parent_id) if ticket.parent_id else None,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat(),
                }
            )
        return tickets

    # --------------------------------------------------------------------- #
    # Local JSON helpers (CLI fallback)
    # --------------------------------------------------------------------- #
    def _ensure_local_file(self) -> None:
        os.makedirs(os.path.dirname(self.local_file), exist_ok=True)
        if not os.path.exists(self.local_file):
            with open(self.local_file, 'w', encoding='utf-8') as fh:
                json.dump([], fh)

    def _save_local_ticket(self, ticket: Dict[str, Any]) -> None:
        tickets = self.get_tickets()
        tickets.append(ticket)
        with open(self.local_file, 'w', encoding='utf-8') as fh:
            json.dump(tickets, fh, indent=2)

    def _update_local_ticket(self, ticket_id: str, *, key: str, value: Any) -> None:
        tickets = self.get_tickets()
        for ticket in tickets:
            if ticket.get('id') == ticket_id:
                ticket[key] = value
                break
        with open(self.local_file, 'w', encoding='utf-8') as fh:
            json.dump(tickets, fh, indent=2)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def create_ticket(
        self,
        type: str,
        title: str,
        description: str,
        assigned_to: str = "Unassigned",
        dependencies: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        """
        Create a new ticket (Epic or Story) and return its ID.
        """
        dependencies = dependencies or []
        if self._use_django:
            ticket_id = self._create_ticket_django(
                type=type,
                title=title,
                description=description,
                assigned_to=assigned_to,
            )
            if dependencies:
                self._update_dependencies_django(ticket_id, dependencies)
            if parent_id:
                self._update_parent_django(ticket_id, parent_id)
            return ticket_id

        ticket_id = str(uuid.uuid4())
        ticket = {
            "id": ticket_id,
            "type": type,
            "title": title,
            "description": description,
            "status": "todo",
            "assigned_to": assigned_to,
            "dependencies": dependencies,
            "parent_id": parent_id,
        }
        self._save_local_ticket(ticket)
        return ticket_id

    def update_ticket_dependencies(self, ticket_id: str, new_dependencies: List[str]) -> None:
        if self._use_django:
            self._update_dependencies_django(ticket_id, new_dependencies)
            return
        self._update_local_ticket(ticket_id, key='dependencies', value=new_dependencies)

    def update_ticket_parent(self, ticket_id: str, parent_id: Optional[str]) -> None:
        if self._use_django:
            self._update_parent_django(ticket_id, parent_id or '')
            return
        self._update_local_ticket(ticket_id, key='parent_id', value=parent_id)

    def get_tickets(self) -> List[Dict[str, Any]]:
        if self._use_django:
            return self._get_tickets_django()
        if not os.path.exists(self.local_file):
            return []
        with open(self.local_file, 'r', encoding='utf-8') as fh:
            return json.load(fh)
