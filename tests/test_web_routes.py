from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from web.app import app


def test_save_result_passes_csv_path_to_history_append():
    client = TestClient(app)
    schedule = {'day': {}, 'night': {}}

    with patch('web.routes.get_selected_variant_result') as mock_select, patch(
        'web.routes.append_generated_schedule_to_history'
    ) as mock_append:
        mock_select.return_value = (
            True,
            {'selected': {'schedule': schedule}},
            'ok',
        )
        mock_append.return_value = {
            'path': 'data/duty_roster_2021_2025.csv',
            'added_count': 1,
            'skipped_count': 0,
        }

        response = client.post(
            '/save_result',
            data={
                'start_date': '2026-04-21',
                'variant_index': '0',
                'variants': '1',
                'variant_top_k': '3',
            },
        )

    assert response.status_code == 200
    mock_append.assert_called_once_with(schedule, Path('data/duty_roster_2021_2025.csv'))