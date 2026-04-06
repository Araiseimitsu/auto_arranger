from unittest.mock import patch

import main


def test_main_launches_desktop_app():
    with patch('main.launch_desktop_app') as mock_launch:
        main.main()

    mock_launch.assert_called_once_with()