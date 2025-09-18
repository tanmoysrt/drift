// Copyright (c) 2025, Tanmoy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Drift Session", {
	refresh(frm) {
		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Destroy Remote Session"), function () {
				frm.call("destroy_remote_session").then(() => {
                    frm.reload_doc();
                });
			});
		}

		if (frm.doc.video_download_status === "Downloaded") {
			frm.add_custom_button(__("Delete Downloaded Videos"), function () {
				frm.call("delete_downloaded_videos").then(() => {
                    frm.reload_doc();
                });
            });

            playRecordedVideos();
        }
	},
});

function loadPlyr(callback) {
    if (window.Plyr) {
        callback();
        return;
    }

    // Load CSS
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://cdn.jsdelivr.net/npm/plyr@3/dist/plyr.css";
    document.head.appendChild(link);

    // Load JS
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/plyr@3/dist/plyr.polyfilled.min.js";
    script.onload = callback;
    document.body.appendChild(script);
}

async function playRecordedVideos() {
    loadPlyr(async () => {
        // Fetch URLs from server
        const e = await cur_frm.call("get_recorded_video_urls");
        const videoLinks = e.message || [];

        if (!Array.isArray(videoLinks) || videoLinks.length === 0) {
            console.warn("No video URLs received");
            return;
        }

        const container = document.getElementById("video_container");

        // Clear container
        container.innerHTML = "";

        // Create <video> element
        const videoEl = document.createElement("video");
        videoEl.id = "video_html";
        videoEl.playsInline = true;
        videoEl.muted = true; // required for autoplay
        videoEl.style.width = "100%";
        videoEl.style.background = "#000";

        const source = document.createElement("source");
        videoEl.appendChild(source);

        container.appendChild(videoEl);

        // Init Plyr
        const player = new Plyr(videoEl, {
            controls: [
                'play', 'progress', 'current-time',
                 'fullscreen', 'next', 'previous'
            ],
            speed: {
                selected: 1,
                options: [1, 2, 4, 8]
            }
		});

		player.on('ready', () => {
			const controlsBar = player.elements.controls;

			// Create speed dropdown
			const select = document.createElement("select");
			select.style.padding = "8px 8px";
			select.style.fontSize = "14px";
			select.className = "plyr__controls__item plyr__control";
			select.id = "playback_rate";

			[1, 2, 4, 8].forEach(rate => {
				const option = document.createElement("option");
				option.value = rate;
				option.textContent = rate + "x";
				if (rate === 1) option.selected = true;
				select.appendChild(option);
			});

			// Change playback speed
			select.addEventListener("change", () => {
				player.speed = parseFloat(select.value);
			});

			controlsBar.appendChild(select);
		});
		
		document.addEventListener("keydown", (e) => {
			if (e.code === "Space") {
				e.preventDefault();
				if (player.playing) {
					player.pause();
				} else {
					player.play();
				}
			}
		});


        // Create custom control bar (Prev / Next / Info)
        const controls = document.createElement("div");
        controls.style.marginTop = "8px";
        controls.style.display = "flex";
        controls.style.justifyContent = "center";
        controls.style.alignItems = "center";
        controls.style.gap = "10px";
        container.appendChild(controls);

        const prevBtn = document.createElement("button");
        prevBtn.classList.add("btn", "btn-default", "ellipsis");
        prevBtn.textContent = "Prev";
        controls.appendChild(prevBtn);

        const info = document.createElement("span");
        info.textContent = "Video 0/0";
        controls.appendChild(info);

        const nextBtn = document.createElement("button");
        nextBtn.classList.add("btn", "btn-default", "ellipsis");
        nextBtn.textContent = "Next";
        controls.appendChild(nextBtn);

        let idx = 0;

        function updateInfo() {
            info.textContent = `Video ${idx + 1} / ${videoLinks.length}`;
        }

        function playIndex(i) {
            if (i < 0 || i >= videoLinks.length) {
                alert("No more videos");
                return;
            }
            idx = i;

            source.src = videoLinks[i];
            videoEl.load();

            videoEl.onloadedmetadata = () => {
				updateInfo();
				const selectedRate = parseFloat(document.getElementById("playback_rate").value);
		        player.speed = selectedRate;

                player.play().catch(err => {
                    console.warn("Autoplay blocked:", err);
                });
            };
        }

        // Auto-advance on end
        player.on('ended', () => {
            if (idx + 1 < videoLinks.length) {
                playIndex(idx + 1);
            }
        });

        // Button handlers
        prevBtn.addEventListener("click", () => {
            if (idx > 0) playIndex(idx - 1);
        });
        nextBtn.addEventListener("click", () => {
            if (idx + 1 < videoLinks.length) playIndex(idx + 1);
        });

        // Start with first video
        playIndex(0);
    });
}

