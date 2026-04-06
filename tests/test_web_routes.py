from pathlib import Path
from unittest.mock import patch

import pytest
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


def test_save_result_uses_client_schedule_json_when_present():
    client = TestClient(app)
    payload = '{"day":{"2026-04-21":{"1":"Alice"}}, "night":{}}'

    with patch('web.routes.get_selected_variant_result') as mock_select, patch(
        'web.routes.append_generated_schedule_to_history'
    ) as mock_append:
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
                'schedule_json': payload,
            },
        )

    assert response.status_code == 200
    mock_select.assert_not_called()
    assert mock_append.called
    passed_schedule = mock_append.call_args[0][0]
    from datetime import date

    assert passed_schedule['day'][date(2026, 4, 21)][1] == 'Alice'


@pytest.fixture()
def client():
    return TestClient(app)


def test_history_save_endpoint_json(client, tmp_path, monkeypatch):
    import web.services as svc

    csv_path = tmp_path / 'hist.csv'
    csv_path.write_text(
        'date,shift_category,shift_index,person_name\n'
        '2026-04-20,Day,1,A\n'
        '2026-04-19,Day,2,B\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(svc, 'CSV_PATH', csv_path)

    response = client.post(
        '/history/save',
        json={
            'page': 1,
            'page_size': 2,
            'rows': [
                {
                    'date': '2026-04-20',
                    'shift_category': 'Day',
                    'shift_index': 1,
                    'person_name': 'Z',
                },
                {
                    'date': '2026-04-19',
                    'shift_category': 'Day',
                    'shift_index': 2,
                    'person_name': 'Y',
                },
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True