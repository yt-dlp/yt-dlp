import { useEffect } from 'preact/hooks';
import { set, useStore } from '../state';
import { Btn } from '../ui';

const mod = navigator.platform.startsWith('Mac') ? '⌘' : 'Ctrl';
const shortcuts: [string, string][] = [
  [`${mod} N`, 'New download'], [`${mod} Shift V`, 'Paste links from the clipboard and open New download'], [`${mod} V`, 'Same, when no text box is active'],
  [`${mod} Enter`, 'Start the download from the New download screen'], [`${mod} 1 … 5`, 'Downloads, History, Presets, Logs, Engine'], [`${mod} ,`, 'Settings'],
  [`${mod} F`, 'Search the current list'], ['↑ ↓', 'Move through the list'], ['Space', 'Pause or resume the selected downloads'], ['Enter', 'Open the finished file'],
  ['Delete', 'Cancel a running download, or remove a finished one from the list'], [`${mod} A`, 'Select everything in the list'],
  [`${mod} Shift P / R`, 'Pause all, resume all'], ['Esc', 'Close a dialog, clear the selection or the search box'], ['F1', 'This page'],
];

const topics: { id: string; title: string; body: preact.ComponentChildren }[] = [
  { id: 'start', title: 'Downloading something', body: (
    <ul>
      <li>Copy the address of the page a video plays on. Choose <b>New download</b> and paste it. Several links can go in at once, one per line.</li>
      <li>After a moment each link shows its title, length and thumbnail. If it is a playlist or channel, <b>Choose items</b> lets you untick the ones you do not want.</li>
      <li>Pick <b>Video</b> or <b>Audio only</b>, a quality and a file type, then press <b>Download</b>. The date box next to the button starts it later instead.</li>
      <li>The file is saved in the folder shown under <b>Save to</b>. Double-click a finished row to open it.</li>
    </ul>
  ) },
  { id: 'queue', title: 'The queue', body: (
    <ul>
      <li>Downloads run a few at a time. The rest wait their turn. Change how many in Settings.</li>
      <li><b>Pause</b> stops a download and keeps what it already has. <b>Resume</b> carries on from there, even after you quit and reopen the app.</li>
      <li><b>Cancel</b> stops a download and removes the unfinished file.</li>
      <li>Select a row to see where it is up to, the files it made, its log and the exact command behind it.</li>
    </ul>
  ) },
  { id: 'formats', title: 'Quality and formats', body: (
    <ul>
      <li><b>MP4</b> is the safe choice. It plays on phones, TVs and in video editors. The app prefers H.264 video and AAC audio so that stays true.</li>
      <li><b>Whatever is best</b> takes the highest quality streams the site has, whatever they are. The result is often MKV or WebM.</li>
      <li>To pick one exact format, open <b>formats</b> in the preview of a link and choose a row.</li>
      <li>For audio, <b>Original, no conversion</b> keeps the sound exactly as the site sent it. Converting to MP3 always loses a little.</li>
    </ul>
  ) },
  { id: 'advanced', title: 'Advanced options', body: (
    <ul>
      <li>The <b>Advanced</b> tab lists every option the yt-dlp engine has, grouped by subject. Use the search box to find one by name or by its command-line flag.</li>
      <li>Point at an option to read what it does. Options you have changed are marked with a dot; the arrow on the right puts one back to its default.</li>
      <li>Advanced choices sit on top of the Simple ones. If both set the same thing, Advanced wins and the Simple tab tells you.</li>
      <li><b>Extra arguments</b> at the bottom of the list accepts anything else, typed as it would be in a terminal.</li>
      <li>The bar along the bottom shows the equivalent command. It is there for the curious; you never need to type it.</li>
    </ul>
  ) },
  { id: 'presets', title: 'Presets and config files', body: (
    <ul>
      <li>A preset remembers a set of options under a name. Make one with <b>Save as preset</b> on the New download screen.</li>
      <li><b>Import config file</b> on the Presets screen turns an existing <span class="mono">yt-dlp.conf</span> into a preset. <b>Export as config file</b> does the reverse.</li>
      <li>Options you want on every download, such as a proxy or a speed limit, go under Settings, <b>Options for every download</b>.</li>
      <li>By default the app ignores config files in your home folder, so a download depends only on what you see on screen. Turn off “Ignore yt-dlp config files” there to change that.</li>
    </ul>
  ) },
  { id: 'signin', title: 'Videos that need a login', body: (
    <ul>
      <li>Private, age-restricted and members-only videos need the site to know who you are.</li>
      <li>The simplest way: sign in to the site in your normal browser, then under Advanced, <b>Sign-in and cookies</b>, set <b>Use cookies from browser</b> to that browser.</li>
      <li>If the browser is running and the lookup fails, close the browser and try again.</li>
      <li>Passwords typed into the app are used for that download only. They are never written to logs or reports.</li>
    </ul>
  ) },
  { id: 'errors', title: 'When something fails', body: (
    <ul>
      <li>Select the failed row. The app says what went wrong, why it probably happened, at which step, and what to try.</li>
      <li>Where it can, it offers a button that does the fix for you: update the engine, retry, switch format, choose another folder, use browser cookies.</li>
      <li><b>Update engine and retry</b> solves most failures that appear out of nowhere. Sites change, and the engine is updated to follow them.</li>
      <li>If you need to ask for help, <b>Copy report</b> gathers the versions, the link and the log, with passwords, cookies and your user name removed.</li>
    </ul>
  ) },
  { id: 'live', title: 'Live streams and scheduling', body: (
    <ul>
      <li>A live stream downloads until it ends or you pause it. <b>Record live streams from the beginning</b> (Live and scheduling) starts from the first moment where the site allows it.</li>
      <li>For a stream that has not started, turn on <b>Wait for scheduled streams</b>. The download sits in the queue and begins when the stream does.</li>
      <li>To start any download at a set time, fill in the date box next to the Download button.</li>
    </ul>
  ) },
  { id: 'output', title: 'Lists, dry runs and JSON', body: (
    <ul>
      <li>Options under <b>Simulate and print</b> make the engine report instead of download: list formats, print chosen fields, or dump everything as JSON.</li>
      <li>The result appears in the <b>Output</b> tab of that row, where it can be copied or saved to a file.</li>
    </ul>
  ) },
  { id: 'updates', title: 'Updates', body: (
    <ul>
      <li>The app checks for a newer engine when it starts and tells you in the sidebar. The Engine screen updates it, or switches to nightly builds when a fix is not in a release yet.</li>
      <li>Every engine download is checked against its published checksum before it is used. <b>Use built-in engine</b> goes back to the one that came with the app.</li>
      <li>New versions of the app itself download in the background and install when you restart.</li>
    </ul>
  ) },
];

export function HelpView() {
  const s = useStore();
  useEffect(() => {
    if (!s.helpAnchor) return;
    document.getElementById(`help-${s.helpAnchor}`)?.scrollIntoView();
    set({ helpAnchor: null });
  }, [s.helpAnchor]);
  return (
    <div class="main">
      <div class="bar"><h1>Help</h1><div class="grow" /><Btn onClick={() => set({ welcome: true })}>Welcome guide</Btn></div>
      <div class="scroll grow">
        <div class="page help">
          <div class="toc">{topics.map((t) => <Btn small onClick={() => document.getElementById(`help-${t.id}`)?.scrollIntoView({ behavior: 'smooth' })}>{t.title}</Btn>)}</div>
          {topics.map((t) => <section id={`help-${t.id}`}><h2>{t.title}</h2>{t.body}</section>)}
          <section id="help-keys">
            <h2>Keyboard shortcuts</h2>
            <table><tbody>{shortcuts.map(([k, d]) => <tr><td>{k.split(' ').map((p) => (/^[…/]$/.test(p) ? ` ${p} ` : <><kbd>{p}</kbd> </>))}</td><td>{d}</td></tr>)}</tbody></table>
          </section>
        </div>
      </div>
    </div>
  );
}

export function Welcome({ onClose }: { onClose: () => void }) {
  return (
    <div class="scrim">
      <div class="dialog wide" role="dialog" aria-modal="true" aria-label="Welcome to Dubdeck" onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}>
        <header><h2>Welcome to Dubdeck</h2></header>
        <div class="content">
          <p>Dubdeck saves video and audio from the web to your computer. It runs the yt-dlp engine for you, so there is no terminal and nothing to install.</p>
          <ol class="steps">
            <li><div><b>Paste a link</b><span>Copy the address of a video, playlist or channel, then choose New download. Dropping a link onto the window works too.</span></div></li>
            <li><div><b>Choose what you want</b><span>Video or audio only, a quality, a file type. The defaults give you an MP4 that plays anywhere.</span></div></li>
            <li><div><b>Press Download</b><span>Progress shows in the queue. If something fails, select the row: the app explains why and offers a fix.</span></div></li>
          </ol>
          <p>Everything the engine can do is under the Advanced tab when you want it. Help is in the sidebar, or press F1.</p>
          <p class="small faint">Download only what you have the right to. Respect the terms of the sites you use and the people who made the work.</p>
        </div>
        <footer><Btn kind="primary" autoFocus onClick={onClose}>Get started</Btn></footer>
      </div>
    </div>
  );
}
