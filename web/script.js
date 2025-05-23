document.addEventListener('DOMContentLoaded', () => {
    const videoUrlInput = document.getElementById('videoUrl');
    const fetchButton = document.getElementById('fetchButton');
    const videoInfoDiv = document.getElementById('videoInfo');

    fetchButton.addEventListener('click', async () => {
        const url = videoUrlInput.value.trim();
        if (!url) {
            alert('Please enter a video URL.');
            return;
        }

        videoInfoDiv.innerHTML = '<p>Fetching video information...</p>';

        try {
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                videoInfoDiv.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
            } else if (data.formats && data.formats.length > 0) {
                displayFormats(data.formats, url, data.title || 'Video');
            } else {
                videoInfoDiv.innerHTML = '<p>No downloadable formats found or error in processing.</p>';
            }

        } catch (error) {
            console.error('Fetch error:', error);
            videoInfoDiv.innerHTML = `<p style="color: red;">Failed to fetch video information: ${error.message}</p>`;
        }
    });

    function displayFormats(formats, originalUrl, videoTitle) {
        videoInfoDiv.innerHTML = `<h2>${videoTitle}</h2>`;
        const list = document.createElement('ul');
        list.style.listStyleType = 'none';
        list.style.padding = '0';

        formats.forEach(format => {
            const listItem = document.createElement('li');
            listItem.className = 'format-item';

            let formatDescription = `${format.ext} - ${format.format_note || format.resolution || format.format_id}`;
            if (format.filesize) {
                formatDescription += ` (${(format.filesize / 1024 / 1024).toFixed(2)} MB)`;
            } else if (format.filesize_approx) {
                formatDescription += ` (~${(format.filesize_approx / 1024 / 1024).toFixed(2)} MB)`;
            }


            const descriptionSpan = document.createElement('span');
            descriptionSpan.textContent = formatDescription;

            const downloadButton = document.createElement('a');
            downloadButton.href = `/download_video?url=${encodeURIComponent(originalUrl)}&format_id=${encodeURIComponent(format.format_id)}`;
            downloadButton.textContent = 'Download';
            downloadButton.className = 'download-button';
            downloadButton.target = '_blank'; // Open download in a new tab

            listItem.appendChild(descriptionSpan);
            listItem.appendChild(downloadButton);
            list.appendChild(listItem);
        });
        videoInfoDiv.appendChild(list);
    }
});
