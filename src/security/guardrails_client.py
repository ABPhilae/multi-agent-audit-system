import httpx
import logging
from src.config import get_settings

logger = logging.getLogger(__name__)


class GuardrailsClient:
    """HTTP client for the NeMo Guardrails sidecar container."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.guardrails_url
        self.enabled = self.settings.use_guardrails

    async def validate_input(self, message: str) -> dict:
        """Run all input rails. Returns {'safe': bool, 'message': str, 'blocked_reason': str}."""
        if not self.enabled:
            return {'safe': True, 'message': message, 'blocked_reason': None}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f'{self.base_url}/v1/rails/input',
                    json={'input': message}
                )
                data = resp.json()
                return {
                    'safe': data.get('safe', True),
                    'message': message,
                    'blocked_reason': data.get('reason'),
                }
        except Exception as e:
            logger.warning(f'Guardrails input check failed: {e}. Allowing through.')
            return {'safe': True, 'message': message, 'blocked_reason': None}

    async def validate_output(self, response: str) -> dict:
        """Run all output rails. Returns {'safe': bool, 'response': str}."""
        if not self.enabled:
            return {'safe': True, 'response': response}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f'{self.base_url}/v1/rails/output',
                    json={'output': response}
                )
                data = resp.json()
                return {
                    'safe': data.get('safe', True),
                    'response': data.get('filtered_output', response),
                }
        except Exception as e:
            logger.warning(f'Guardrails output check failed: {e}. Passing through.')
            return {'safe': True, 'response': response}


guardrails = GuardrailsClient()
