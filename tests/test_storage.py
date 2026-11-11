import json

from tgtg_bot.storage import DEFAULT_SETTINGS, Storage


def test_migrates_legacy_txt_files(tmp_path):
    (tmp_path / "users_login_data.txt").write_text(
        json.dumps({"111": {"access_token": "a", "refresh_token": "r", "cookie": "datadome=x"}, "222": {}})
    )
    (tmp_path / "users_settings_data.txt").write_text(
        json.dumps({"111": {"sold_out": 1, "new_stock": 0, "stock_reduced": 0, "stock_increased": 1}})
    )
    (tmp_path / "available_items_favorites.txt").write_text("{}")
    s = Storage(tmp_path / "data", legacy_dir=tmp_path)
    assert list(s.users) == ["111"]
    assert s.credentials("111")["refresh_token"] == "r"
    assert s.settings("111") == {"new_stock": False, "sold_out": True, "stock_reduced": False, "stock_increased": True}
    assert (tmp_path / "users_login_data.txt.migrated").exists()
    assert not (tmp_path / "users_login_data.txt").exists()
    # reload from the new files
    assert Storage(tmp_path / "data", legacy_dir=tmp_path).credentials("111")["cookie"] == "datadome=x"


def test_settings_credentials_and_active_users(tmp_path):
    s = Storage(tmp_path, legacy_dir=None)
    s.set_credentials("1", {"refresh_token": "r"}, email="a@b.de")
    assert s.settings("1") == DEFAULT_SETTINGS
    assert s.active_users() == ["1"]
    for k in DEFAULT_SETTINGS:
        s.set_setting("1", k, False)
    assert s.active_users() == []
    s.set_setting("1", "sold_out", True)
    s.update_credentials("1", {"refresh_token": "r2"})
    reloaded = Storage(tmp_path, legacy_dir=None)
    assert reloaded.credentials("1") == {"refresh_token": "r2"}
    assert reloaded.email("1") == "a@b.de"
    s.mark_needs_login("1")
    assert not s.is_logged_in("1") and s.active_users() == []
    s.remove_user("1")
    assert "1" not in Storage(tmp_path, legacy_dir=None).users
