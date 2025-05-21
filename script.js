let currentStoryboard = [];

async function generateStoryboard() {
    const userPrompt = document.getElementById("storyInput").value;
    const selectedStyle = document.getElementById("styleSelect").value;
    const characterDesc = document.getElementById("characterInput").value;
    const cameraAngle = document.getElementById("cameraSelect").value;

    const outputDiv = document.getElementById("output");
    const loadingDiv = document.getElementById("loading");
    const generateBtn = document.getElementById("generateBtn");

    outputDiv.innerHTML = "";
    document.getElementById("resultsTitle").style.display = "none";
    loadingDiv.style.display = "block";
    generateBtn.disabled = true;

    try {
        const response = await fetch("http://127.0.0.1:5000/generate-storyboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                prompt: userPrompt,
                style: selectedStyle,
                character: characterDesc,
                camera: cameraAngle
            })
        });

        const data = await response.json();
        loadingDiv.style.display = "none";
        generateBtn.disabled = false;

        currentStoryboard = data.storyboard || [];
        renderStoryboard();

    } catch (error) {
        console.error("Error:", error);
        loadingDiv.style.display = "none";
        outputDiv.innerHTML = "<p style='color: red;'>Error generating storyboard. Please try again.</p>";
    }
}

function renderStoryboard() {
    const outputDiv = document.getElementById("output");
    outputDiv.innerHTML = "";
    if (!Array.isArray(currentStoryboard)) return;
    document.getElementById("resultsTitle").style.display = "block";

    currentStoryboard.forEach((scene, sceneIndex) => {
        const sceneWrapper = document.createElement("div");
        sceneWrapper.classList.add("scene");

        // Scene header with editable title
        const sceneHeader = document.createElement("h3");
        sceneHeader.innerText = `Scene ${scene.scene_number}: ${scene.title}`;
        sceneWrapper.appendChild(sceneHeader);

        // Display narrative if available
        if (scene.narrative) {
            const narrativePara = document.createElement("p");
            narrativePara.innerText = scene.narrative;
            sceneWrapper.appendChild(narrativePara);
        }

        // Section for manual editing of scene title and narrative
        const editSection = document.createElement("div");
        editSection.classList.add("edit-scene");

        const editTitleInput = document.createElement("input");
        editTitleInput.type = "text";
        editTitleInput.value = scene.title;
        editTitleInput.placeholder = "Edit scene title";
        editTitleInput.onchange = () => {
            scene.title = editTitleInput.value;
            sceneHeader.innerText = `Scene ${scene.scene_number}: ${scene.title}`;
        };

        const editNarrativeInput = document.createElement("textarea");
        editNarrativeInput.value = scene.narrative || "";
        editNarrativeInput.placeholder = "Edit scene narrative";
        editNarrativeInput.onchange = () => {
            scene.narrative = editNarrativeInput.value;
        };

        editSection.appendChild(editTitleInput);
        editSection.appendChild(editNarrativeInput);
        sceneWrapper.appendChild(editSection);

        // Allow per-scene style override
        const sceneStyleLabel = document.createElement("label");
        sceneStyleLabel.innerText = "Scene Style:";
        const sceneStyleSelect = document.createElement("select");
        ["cinematic", "realism", "anime", "comic"].forEach(styleOption => {
            const opt = document.createElement("option");
            opt.value = styleOption;
            opt.innerText = styleOption;
            if (scene.scene_style && scene.scene_style === styleOption) {
                opt.selected = true;
            }
            sceneStyleSelect.appendChild(opt);
        });
        sceneStyleSelect.onchange = () => {
            scene.scene_style = sceneStyleSelect.value;
            // Optionally, you can trigger regeneration of the scene images here
        };
        sceneWrapper.appendChild(sceneStyleLabel);
        sceneWrapper.appendChild(sceneStyleSelect);

        // Render shots
        const shotsContainer = document.createElement("div");
        shotsContainer.classList.add("shots-container");

        scene.shots.forEach((shot, shotIndex) => {
            const shotCard = document.createElement("div");
            shotCard.classList.add("shot-card");

            const img = document.createElement("img");
            img.src = shot.image_url || "";
            img.alt = "Shot frame";

            const info = document.createElement("div");
            info.innerHTML = `
                <b>Shot ${shot.frame_number}</b><br>
                <b>Description:</b> ${shot.description}<br>
                <b>Camera:</b> ${shot.camera_angle}<br>
                <b>Shot Type:</b> ${shot.shot_type}<br>
                <b>Emotion:</b> ${shot.emotion}
                ${shot.dialogue && shot.dialogue.toLowerCase() !== "none"
                    ? `<br><b>Dialogue:</b> <i>"${shot.dialogue}"</i>` : ""}
            `;

            const btnRow = document.createElement("div");
            btnRow.style.marginTop = "10px";

            const downloadBtn = document.createElement("button");
            downloadBtn.innerText = "Download";
            downloadBtn.onclick = () => downloadImage(shot.image_url, `scene${scene.scene_number}_shot${shot.frame_number}`);

            const regenShotBtn = document.createElement("button");
            regenShotBtn.innerText = "Regenerate Shot";
            regenShotBtn.onclick = async () => {
                const res = await fetch("http://127.0.0.1:5000/regenerate-shot", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        shot: shot,
                        style: scene.scene_style || document.getElementById("styleSelect").value,
                        character: document.getElementById("characterInput").value
                    })
                });
                const updated = await res.json();
                currentStoryboard[sceneIndex].shots[shotIndex] = updated;
                renderStoryboard();
            };

            const deleteBtn = document.createElement("button");
            deleteBtn.innerText = "Delete Shot";
            deleteBtn.onclick = () => {
                currentStoryboard[sceneIndex].shots.splice(shotIndex, 1);
                renderStoryboard();
            };

            const addBtn = document.createElement("button");
            addBtn.innerText = "Add Shot Below";
            addBtn.onclick = async () => {
                const res = await fetch("http://127.0.0.1:5000/add-shot", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        description: "Follow-up action",
                        frame_number: shot.frame_number + 1,
                        style: scene.scene_style || document.getElementById("styleSelect").value,
                        character: document.getElementById("characterInput").value,
                        camera: document.getElementById("cameraSelect").value
                    })
                });
                const newShot = await res.json();
                currentStoryboard[sceneIndex].shots.splice(shotIndex + 1, 0, newShot);
                renderStoryboard();
            };

            [downloadBtn, regenShotBtn, deleteBtn, addBtn].forEach(b => {
                b.style.marginRight = "5px";
                btnRow.appendChild(b);
            });

            shotCard.appendChild(img);
            shotCard.appendChild(info);
            shotCard.appendChild(btnRow);
            shotsContainer.appendChild(shotCard);
        });

        sceneWrapper.appendChild(shotsContainer);

        // Scene-level control: regenerate entire scene
        const sceneControls = document.createElement("div");
        sceneControls.style.marginTop = "10px";
        const regenSceneBtn = document.createElement("button");
        regenSceneBtn.innerText = "Regenerate Scene";
        regenSceneBtn.onclick = async () => {
            const res = await fetch("http://127.0.0.1:5000/regenerate-scene", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scene: scene,
                    style: scene.scene_style || document.getElementById("styleSelect").value,
                    character: document.getElementById("characterInput").value
                })
            });
            const updated = await res.json();
            currentStoryboard[sceneIndex] = updated;
            renderStoryboard();
        };
        sceneControls.appendChild(regenSceneBtn);
        sceneWrapper.appendChild(sceneControls);

        outputDiv.appendChild(sceneWrapper);
    });
}

function downloadImage(url, name) {
    const link = document.createElement("a");
    link.href = url;
    link.download = `${name}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}