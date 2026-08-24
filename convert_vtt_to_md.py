import re
p = r"C:\Users\kenny\copilot-worktrees\yt-dlp\kennytruong0303-silver-lamp\NB7k7E01z18.en.vtt"
with open(p, encoding='utf-8') as f:
    s = f.read()
lines = []
for line in s.splitlines():
    line = line.rstrip('\r')
    if not line.strip():
        lines.append('')
        continue
    if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
        continue
    if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3} -->", line):
        continue
    line = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line)
    line = re.sub(r"<c>", "", line)
    line = re.sub(r"</c>", "", line)
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"^\[.*?\]$", "", line)
    lines.append(line.strip())
out = []
prev_blank = False
for l in lines:
    if l == '':
        if not prev_blank:
            out.append('')
        prev_blank = True
    else:
        out.append(l)
        prev_blank = False
transcript = '\n'.join(out).strip()
md = []
md.append('# Transcript — Takaki Komiyama — Imaging Neural Ensembles During Learning')
md.append('')
md.append('Source: https://www.youtube.com/watch?v=NB7k7E01z18')
md.append('')
md.append('Metadata:')
md.append('- id: NB7k7E01z18')
md.append('- uploader/channel: Center for Science of Information NSF STC')
md.append('- upload_date: 2014-10-16')
md.append('- duration_seconds: 3344')
md.append('')
md.append('---')
md.append('')
md.append(transcript)
md_text = '\n'.join(md)
out_path = r"C:\Users\kenny\copilot-worktrees\yt-dlp\kennytruong0303-silver-lamp\NB7k7E01z18_transcript.md"
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md_text)
print('FILE:'+out_path)
print(md_text)
