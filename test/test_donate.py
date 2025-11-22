import re
import requests

def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

def extract_donate_url(content):
    match = re.search(r'\[!\[Donate\]\(.*?\)\]\((.*?)\)', content)
    assert match is not None, "Link de doação não encontrado no README"
    return match.group(1)

def test_donate_link_is_absolute():
    content = read_readme()
    url = extract_donate_url(content)
    assert url.startswith("https://"), f"URL não é absoluta: {url}"

def test_donate_link_is_accessible():
    content = read_readme()
    url = extract_donate_url(content)
    response = requests.get(url)
    assert response.status_code == 200, f"Link inacessível: status {response.status_code} - {url}"
