import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add local directory to path to import modules
sys.path.append(os.getcwd())

import orchestrator
import db
import notifier

class TestAutoPause(unittest.TestCase):
    
    @patch('orchestrator.db')
    @patch('orchestrator.notifier')
    @patch('orchestrator.requests')
    def test_auto_pause_on_failed_session(self, mock_requests, mock_notifier, mock_db):
        # Setup mock for db.update_session_state
        mock_db.update_session_state = MagicMock()
        mock_db.set_paused = MagicMock()
        mock_notifier.notify_failed = MagicMock()
        mock_db.is_paused.return_value = False
        
        # We need two responses:
        # 1. POST /sessions (creation)
        # 2. GET /sessions/{id} (polling) -> FAILED

        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {'id': 'test_session_id'}
        
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {'state': 'FAILED', 'id': 'test_session_id'}
        
        # Configure side_effect for requests.post and requests.get
        # Note: run_jules_api_session calls db.get_repo_info which calls requests.get too.
        # We should probably mock get_repo_info or ensure requests.get handles it.
        
        with patch('orchestrator.get_repo_info', return_value=('source_name', 'main')):
            mock_requests.post.return_value = mock_post_response
            mock_requests.get.return_value = mock_get_response
            
            # Mock db.get_session_by_issue to return None (new session)
            mock_db.get_session_by_issue.return_value = None
            
            # run_jules_api_session will loop. We need requests.get to return successfully once then we need to break loop?
            # Actually, if state is FAILED, it returns None immediately (break loop).
            
            orchestrator.run_jules_api_session({'number': 123, 'title': 'Test Issue', 'body': 'body'})

        # Verify calls
        mock_notifier.notify_failed.assert_called_with(123, 'test_session_id')
        mock_db.set_paused.assert_called_with(True)

    @patch('orchestrator.db')
    @patch('orchestrator.notifier')
    def test_auto_pause_on_stuck_merge(self, mock_notifier, mock_db):
        # Setup mocks
        mock_db.get_active_sessions.return_value = [
            ('session_123', 123, 'Test Issue', 'repo', 'COMPLETED')
        ]
        
        # Mock merge_pull_request to return False
        with patch('orchestrator.merge_pull_request', return_value=False):
            # We need to simulate the retry counter increasing
            orchestrator.merge_retries = {'session_123': 3} # Set to 3 so next call makes it 4 ( > 3)
            
            orchestrator.process_one_active_session()

        # Verify calls
        mock_notifier.notify_failed.assert_called_with(123, 'session_123')
        mock_db.set_paused.assert_called_with(True)

if __name__ == '__main__':
    unittest.main()
