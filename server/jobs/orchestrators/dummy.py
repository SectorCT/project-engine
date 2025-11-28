import time


def run_job(job_id, prompt, callbacks, **kwargs):
    """Lightweight stub orchestrator used for local testing."""
    callbacks.on_status(callbacks.Status.RUNNING, 'Agents are assembling the plan')
    time.sleep(0.1)
    callbacks.on_step(agent_name='Architect', message=f'Planning application for prompt: {prompt}', order=1)
    time.sleep(0.1)
    callbacks.on_step(agent_name='BestPractices', message='Validating schema and ensuring compliance', order=2)
    time.sleep(0.1)
    callbacks.on_step(agent_name='Builder', message='Synthesizing UI + API specification', order=3)
    time.sleep(0.1)
    callbacks.on_app(
        {
            'prompt': prompt,
            'screens': [
                {'name': 'Home', 'components': ['hero', 'cta', 'features']},
            ],
            'generatedBy': 'dummy-orchestrator',
            'metadata': kwargs.get('metadata', {}),
        }
    )

