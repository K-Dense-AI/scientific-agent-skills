"""Distinguish public URL paths from machine-specific filesystem paths."""

import skill_contract


def test_public_web_paths_do_not_hide_local_paths(tmp_path):
    document = tmp_path / "SKILL.md"
    document.write_text(
        '<https://www.vendor.example/de/de/home/life-science/materials>\n'
        '[API](https://service.example/Users/records/items)\n'
        'url = "HTTP://vendor.example/home/catalog/items"\n'
        'https://vendor.example/home/catalog/ then /home/alice/data/input.csv\n'
        '/Users/alice/data.csv and /mnt/c/Users/bob/data.csv\n'
        'file:///home/alice/data.csv\n'
        'https://service.example/download?file=/home/alice/data.csv\n',
        encoding="utf-8",
    )
    problems = skill_contract.structure.personal_path_problems(tmp_path)
    assert len(problems) == 5
    assert all(any(f":{line} " in problem for line in (4, 5, 6, 7)) for problem in problems)


def test_service_accounts_and_placeholders_remain_portable(tmp_path):
    (tmp_path / "SKILL.md").write_text(
        '/home/dnanexus/work/ /home/$USER/work/ /Users/<you>/data/\n',
        encoding="utf-8",
    )
    assert skill_contract.structure.personal_path_problems(tmp_path) == []
