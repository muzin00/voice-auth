import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from vca_infra.storages.local_storage import LocalStorage


class TestLocalStorage:
    """LocalStorageの統合テスト."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str, None, None]:
        """一時ディレクトリを作成."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage(self, temp_dir: str) -> LocalStorage:
        """LocalStorageインスタンスを作成."""
        return LocalStorage(base_path=temp_dir)

    def test_upload(self, storage: LocalStorage, temp_dir: str):
        """ファイルのアップロードが成功する."""
        data = b"test audio data"
        path = "voices/1/test.wav"

        result = storage.upload(data, path, content_type="audio/wav")

        # 結果のパスが正しい
        expected_path = str(Path(temp_dir) / path)
        assert result == expected_path

        # ファイルが実際に作成されている
        assert Path(result).exists()

        # ファイルの内容が正しい
        with open(result, "rb") as f:
            assert f.read() == data

    def test_upload_creates_parent_directories(
        self, storage: LocalStorage, temp_dir: str
    ):
        """親ディレクトリが自動的に作成される."""
        data = b"test data"
        path = "voices/speaker_1/subfolder/audio.mp3"

        result = storage.upload(data, path)

        assert Path(result).exists()
        assert Path(result).parent.exists()

    def test_delete_existing_file(self, storage: LocalStorage, temp_dir: str):
        """存在するファイルを削除できる."""
        data = b"test data"
        path = "voices/1/test.wav"

        # まずファイルをアップロード
        file_path = storage.upload(data, path)
        assert Path(file_path).exists()

        # ファイルを削除
        storage.delete(file_path)
        assert not Path(file_path).exists()

    def test_delete_with_relative_path(self, storage: LocalStorage, temp_dir: str):
        """相対パスでファイルを削除できる."""
        data = b"test data"
        path = "voices/1/test.wav"

        # ファイルをアップロード
        storage.upload(data, path)
        full_path = Path(temp_dir) / path
        assert full_path.exists()

        # 相対パスで削除
        storage.delete(path)
        assert not full_path.exists()

    def test_get_url(self, storage: LocalStorage, temp_dir: str):
        """URLを取得できる（ローカルではファイルパスを返す）."""
        data = b"test data"
        path = "voices/1/test.wav"

        file_path = storage.upload(data, path)
        url = storage.get_url(file_path)

        # ローカルストレージではパスをそのまま返す
        assert url == file_path

    def test_get_url_with_expires_in(self, storage: LocalStorage, temp_dir: str):
        """expires_in引数が指定されても動作する."""
        data = b"test data"
        path = "voices/1/test.wav"

        file_path = storage.upload(data, path)
        url = storage.get_url(file_path, expires_in=7200)

        assert url == file_path

    def test_multiple_uploads_to_same_directory(
        self, storage: LocalStorage, temp_dir: str
    ):
        """同じディレクトリに複数ファイルをアップロードできる."""
        files = [
            ("voices/1/test1.wav", b"data1"),
            ("voices/1/test2.mp3", b"data2"),
            ("voices/1/test3.ogg", b"data3"),
        ]

        for path, data in files:
            result = storage.upload(data, path)
            assert Path(result).exists()

        # すべてのファイルが存在する
        for path, data in files:
            file_path = Path(temp_dir) / path
            assert file_path.exists()
            with open(file_path, "rb") as f:
                assert f.read() == data

    def test_upload_overwrites_existing_file(
        self, storage: LocalStorage, temp_dir: str
    ):
        """既存ファイルが上書きされる."""
        path = "voices/1/test.wav"
        original_data = b"original data"
        new_data = b"new data"

        # 最初のアップロード
        storage.upload(original_data, path)

        # 同じパスに再アップロード
        result = storage.upload(new_data, path)

        # 新しいデータが保存されている
        with open(result, "rb") as f:
            assert f.read() == new_data

    def test_base_path_initialization(self, temp_dir: str):
        """base_pathが正しく初期化される."""
        storage = LocalStorage(base_path=temp_dir)
        assert storage.base_path == Path(temp_dir)
        assert storage.base_path.exists()
