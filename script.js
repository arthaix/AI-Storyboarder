async function generateStoryboard() {
    const userPrompt = document.getElementById("storyInput").value;
    const selectedStyle = document.getElementById("styleSelect").value;
    const outputDiv = document.getElementById("output");
    const loadingDiv = document.getElementById("loading");
    const generateBtn = document.getElementById("generateBtn");

    outputDiv.innerHTML = "";
    loadingDiv.style.display = "block";  // Показываем индикатор загрузки
    generateBtn.disabled = true;  // Отключаем кнопку

    try {
        const response = await fetch("http://127.0.0.1:5000/generate-storyboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: userPrompt, style: selectedStyle })
        });

        const data = await response.json();
        loadingDiv.style.display = "none";  // Скрываем индикатор загрузки
        generateBtn.disabled = false;  // Включаем кнопку

        if (!data.storyboard || !Array.isArray(data.storyboard)) {
            throw new Error("Invalid response from server");
        }

        // 🔄 Сортировка сцен по порядку (1 → 2 → 3)
        data.storyboard.sort((a, b) => {
            return parseInt(a.scene.split(" ")[1]) - parseInt(b.scene.split(" ")[1]);
        });

        data.storyboard.forEach(scene => {
            const sceneDiv = document.createElement("div");
            sceneDiv.classList.add("scene");

            const title = document.createElement("h2");
            title.innerText = scene.scene;

            const description = document.createElement("p");
            description.innerText = scene.description;

            const img = document.createElement("img");
            img.src = scene.image_url;
            img.alt = "Generated scene";

            const downloadBtn = document.createElement("button");
            downloadBtn.innerText = "Download Image";
            downloadBtn.onclick = () => downloadImage(scene.image_url, scene.scene);

            sceneDiv.appendChild(title);
            sceneDiv.appendChild(description);
            sceneDiv.appendChild(img);
            sceneDiv.appendChild(downloadBtn);
            outputDiv.appendChild(sceneDiv);
        });

    } catch (error) {
        console.error("🚨 Error:", error);
        loadingDiv.style.display = "none";
        outputDiv.innerHTML = "<p style='color: red;'>Error generating storyboard. Please try again.</p>";
    }
}

// Функция для скачивания изображения
function downloadImage(url, sceneName) {
    const link = document.createElement("a");
    link.href = url;
    link.download = `${sceneName}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
