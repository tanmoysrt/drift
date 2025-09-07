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

async function playRecordedVideos() {
    // Fetch URLs from server
	const e = await cur_frm.call("get_recorded_video_urls");
	const videoLinks = e.message || [];

	if (!Array.isArray(videoLinks) || videoLinks.length === 0) {
		console.warn("No video URLs received");
		info.textContent = "No videos found";
		return;
    }
    
	const container = document.getElementById("video_container");

	// Clear container
	container.innerHTML = "";

	// Create <video> element
	const videoEl = document.createElement("video");
	videoEl.id = "video_html";
	videoEl.controls = true;
	videoEl.playsInline = true;
	videoEl.muted = true; // required for autoplay
	videoEl.style.width = "100%";
	videoEl.style.maxWidth = "800px";
	videoEl.style.background = "#000";
	container.appendChild(videoEl);

	// Create control bar
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
		videoEl.src = videoLinks[i];
		videoEl.load();

		videoEl.onloadedmetadata = () => {
			updateInfo();
			console.log(
				"Loaded:",
				videoLinks[i],
				"Duration:",
				videoEl.duration,
				"Resolution:",
				videoEl.videoWidth + "x" + videoEl.videoHeight
			);

			// force decode of first frame
			if (videoEl.currentTime === 0) {
				try { videoEl.currentTime = 0.01; } catch (e) {}
			}

			videoEl.play().catch((err) => {
				console.warn("Autoplay blocked:", err);
			});
		};
	}

	// Auto-advance on end
	videoEl.addEventListener("ended", () => {
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

	playIndex(0);
}
