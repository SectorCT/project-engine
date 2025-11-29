import uuid
from typing import List, Dict, Optional

from django.apps import apps
from django.utils import timezone


class TicketSystem:
    """
    Simplified ticket repository that always uses Django models.
    agentLoop code passes job_id so every ticket is scoped to a projectEngine job in Postgres.
    """

    def __init__(self, job_id: str, owner_id: Optional[str] = None):
        if not job_id:
            raise ValueError('TicketSystem requires a job_id')

        JobModel = apps.get_model('jobs', 'Job')
        TicketModel = apps.get_model('jobs', 'Ticket')

        self.job = JobModel.objects.get(id=job_id)
        if owner_id and self.job.owner_id != owner_id:
            raise PermissionError('Job does not belong to requesting owner')

        self.TicketModel = TicketModel

    def create_ticket(
        self,
        type: str,
        title: str,
        description: str,
        assigned_to: str = "Unassigned",
        dependencies: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        ticket = self.TicketModel.objects.create(
            job=self.job,
            type=type,
            title=title,
            description=description,
            assigned_to=assigned_to,
        )
        if parent_id:
            self.update_ticket_parent(str(ticket.id), parent_id)
        if dependencies:
            self.update_ticket_dependencies(str(ticket.id), dependencies)
        return str(ticket.id)

    def update_ticket_dependencies(self, ticket_id: str, new_dependencies: List[str]):
        ticket = self._get_ticket(ticket_id)
        deps = self.TicketModel.objects.filter(id__in=new_dependencies, job=self.job)
        ticket.dependencies.set(deps)

    def update_ticket_parent(self, ticket_id: str, parent_id: str):
        ticket = self._get_ticket(ticket_id)
        parent = self._get_ticket(parent_id) if parent_id else None
        ticket.parent = parent
        ticket.save(update_fields=['parent', 'updated_at'])

    def get_tickets(self) -> List[Dict]:
        results: List[Dict] = []
        tickets = (
            self.TicketModel.objects.filter(job=self.job)
            .select_related('parent')
            .prefetch_related('dependencies')
            .order_by('created_at')
        )
        for ticket in tickets:
            results.append(
                {
                    'id': str(ticket.id),
                    'type': ticket.type,
                    'title': ticket.title,
                    'description': ticket.description,
                    'status': ticket.status,
                    'assigned_to': ticket.assigned_to,
                    'parent_id': str(ticket.parent_id) if ticket.parent_id else None,
                    'dependencies': [str(dep.id) for dep in ticket.dependencies.all()],
                    'created_at': ticket.created_at.isoformat(),
                }
            )
        return results

    def mark_done(self, ticket_id: str):
        ticket = self._get_ticket(ticket_id)
        ticket.status = 'done'
        ticket.updated_at = timezone.now()
        ticket.save(update_fields=['status', 'updated_at'])

    def _get_ticket(self, ticket_id: str):
        return self.TicketModel.objects.get(id=ticket_id, job=self.job)
