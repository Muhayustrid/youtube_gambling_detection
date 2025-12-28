document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let isLoggedIn = false;
    let mockData = [];
    let checkedCount = 0;

    // --- Elements ---
    const profileContainer = document.getElementById('profileContainer');
    const profileIcon = document.getElementById('profileIcon');
    const suggestLoginMenu = document.getElementById('suggestLoginMenu');
    const closeSuggestBtn = document.getElementById('closeSuggestBtn');

    // Auth Modals
    const loginModal = document.getElementById('loginModal');
    const googleLoginBtn = document.getElementById('googleLoginBtn');
    const cancelLoginBtn = document.getElementById('cancelLoginBtn');

    // Analysis
    const analyzeBtn = document.getElementById('analyzeBtn');
    const urlInput = document.getElementById('urlInput');
    const maxResultsSelect = document.getElementById('maxResults');
    const loadingState = document.getElementById('loadingState');
    const resultsSection = document.getElementById('resultsSection');
    const resultsBody = document.getElementById('resultsBody');
    const filterSelect = document.getElementById('filterSelect');

    // Moderation
    const fabContainer = document.getElementById('fabContainer');
    const fabBtn = document.getElementById('fabBtn');
    const fabCount = document.getElementById('fabCount');
    const moderationModal = document.getElementById('moderationModal');
    const cancelModerationBtn = document.getElementById('cancelModerationBtn');
    const confirmModerationBtn = document.getElementById('confirmModerationBtn');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');

    // --- Mock Data Generator ---
    const users = ["Rizky_Gaming", "BudiSantoso", "Siska99", "SlotGacor_Official", "DediCorbuzierFan", "AdminJudi88", "Warga62", "MamaMuda"];
    const comments = [
        { text: "Videonya sangat bermanfaat bang, terima kasih!", type: "clean" },
        { text: "Yang mau menang mudah cek link di bio kakak!", type: "gambling" },
        { text: "Keren kontennya, lanjut terus.", type: "clean" },
        { text: "GACOR PARAH HARI INI, MAXWIN DI DEPAN MATA!!", type: "gambling" },
        { text: "Info loker min?", type: "clean" },
        { text: "Situs terpercaya wd cair itungan detik", type: "gambling" },
        { text: "Jangan lupa subrek ya guys", type: "clean" }
    ];

    function generateMockData(count) {
        const results = [];
        for (let i = 0; i < count; i++) {
            const randomUser = users[Math.floor(Math.random() * users.length)];
            const randomCommentObj = comments[Math.floor(Math.random() * comments.length)];

            let probability;
            if (randomCommentObj.type === 'gambling') {
                probability = (0.8 + Math.random() * 0.19).toFixed(2);
            } else {
                probability = (0.01 + Math.random() * 0.1).toFixed(2);
            }

            const now = new Date();
            now.setMinutes(now.getMinutes() - Math.floor(Math.random() * 1000));

            results.push({
                id: i, // add ID for tracking checkboxes
                username: randomUser,
                comment: randomCommentObj.text,
                prediction: randomCommentObj.type,
                probability: probability,
                date: now.toLocaleString('id-ID'),
                checked: randomCommentObj.type === 'gambling' // Auto-check if gambling
            });
        }
        return results;
    }

    // --- Auth Logic ---

    // Suggest Login Menu (Persistent)
    closeSuggestBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        suggestLoginMenu.style.display = 'none';
    });

    const profileDropdown = document.getElementById('profileDropdown');
    const logoutBtn = document.getElementById('logoutBtn');

    // Profile Click
    profileContainer.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent bubbling
        if (!isLoggedIn) {
            openLoginModal();
        } else {
            // Toggle Dropdown
            profileDropdown.classList.toggle('hidden');
        }
    });

    // Close Dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (isLoggedIn && !profileContainer.contains(e.target) && !profileDropdown.contains(e.target)) {
            profileDropdown.classList.add('hidden');
        }
    });

    // Logout Click
    logoutBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        isLoggedIn = false;
        profileDropdown.classList.add('hidden'); // Hide dropdown
        updateProfileUI();
        // Optional: Show feedback
        alert("Anda telah logout.");
    });

    function openLoginModal() {
        loginModal.classList.remove('hidden');
    }

    function closeLoginModal() {
        loginModal.classList.add('hidden');
    }

    cancelLoginBtn.addEventListener('click', closeLoginModal);

    googleLoginBtn.addEventListener('click', () => {
        // Mock Login Success
        isLoggedIn = true;
        closeLoginModal();
        updateProfileUI();
    });

    function updateProfileUI() {
        if (isLoggedIn) {
            profileIcon.classList.add('logged-in');
            // Use a specific image for the user profile
            profileIcon.innerHTML = `<img src="https://ui-avatars.com/api/?name=User+Demo&background=random" style="width:100%; height:100%; border-radius:50%; object-fit: cover;" alt="User" />`;
            suggestLoginMenu.classList.add('hidden'); // Hide suggest menu permanently when logged in
        } else {
            profileIcon.classList.remove('logged-in');
            profileIcon.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span>Login</span>`;
            suggestLoginMenu.classList.remove('hidden'); // Show suggest menu
            suggestLoginMenu.style.display = 'block'; // Ensure it's visible if it was closed
            profileDropdown.classList.add('hidden'); // Ensure dropdown is hidden
        }
    }

    // --- Analysis Logic ---
    analyzeBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        if (!url) {
            alert("Mohon masukkan URL YouTube terlebih dahulu.");
            return;
        }

        resultsSection.classList.add('hidden');
        loadingState.classList.remove('hidden');
        fabContainer.classList.add('hidden'); // Hide FAB during new analysis
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analyzing...';

        setTimeout(() => {
            loadingState.classList.add('hidden');
            resultsSection.classList.remove('hidden');
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analyze Comments';

            const count = parseInt(maxResultsSelect.value);
            mockData = generateMockData(count);
            renderTable(mockData);
        }, 2000);
    });

    filterSelect.addEventListener('change', (e) => {
        const value = e.target.value;
        filterTable(value);
    });

    function filterTable(filterValue) {
        if (filterValue === 'all') {
            renderTable(mockData);
        } else {
            const filtered = mockData.filter(item => item.prediction === filterValue);
            renderTable(filtered);
        }
    }

    // --- Render Table & Checkbox Logic ---
    function renderTable(data) {
        // Update Stats
        const total = data.length;
        const gamblingCount = data.filter(d => d.prediction === 'gambling').length;
        const cleanCount = total - gamblingCount;

        document.getElementById('statTotal').innerText = total;
        document.getElementById('statClean').innerText = cleanCount;
        document.getElementById('statGambling').innerText = gamblingCount;

        generateAIInsight(total, gamblingCount);

        resultsBody.innerHTML = '';

        if (data.length === 0) {
            resultsBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">Tidak ada data.</td></tr>`;
            return;
        }

        data.forEach(row => {
            const tr = document.createElement('tr');

            const badgeClass = row.prediction === 'gambling' ? 'badge-gambling' : 'badge-clean';
            const badgeText = row.prediction === 'gambling' ? 'Komentar Judol' : 'Komentar Bersih';
            const isChecked = row.checked ? 'checked' : '';

            tr.innerHTML = `
                <td><input type="checkbox" class="row-checkbox" data-id="${row.id}" ${isChecked}></td>
                <td style="font-weight:500;">${row.username}</td>
                <td style="max-width:300px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${row.comment}">${row.comment}</td>
                <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                <td>${row.probability}</td>
                <td style="color:var(--text-secondary); font-size: 0.85rem;">${row.date}</td>
            `;
            resultsBody.appendChild(tr);
        });

        // Re-attach listeners to new checkboxes
        attachCheckboxListeners();
        updateFAB();
    }

    function attachCheckboxListeners() {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        checkboxes.forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = parseInt(e.target.getAttribute('data-id'));
                const item = mockData.find(d => d.id === id);
                if (item) {
                    item.checked = e.target.checked;
                }
                updateFAB();
            });
        });
    }

    function updateFAB() {
        const checkedItems = mockData.filter(d => d.checked);
        checkedCount = checkedItems.length;

        fabCount.innerText = checkedCount;

        if (checkedCount > 0) {
            fabContainer.classList.remove('hidden');
        } else {
            fabContainer.classList.add('hidden');
        }
    }

    // Select All Logic
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            mockData.forEach(d => d.checked = isChecked);
            renderTable(mockData); // Re-render to update all checkboxes visually
        });
    }

    // --- Moderation Modal Logic ---
    fabBtn.addEventListener('click', () => {
        moderationModal.classList.remove('hidden');
    });

    cancelModerationBtn.addEventListener('click', () => {
        moderationModal.classList.add('hidden');
    });

    confirmModerationBtn.addEventListener('click', () => {
        alert(`${checkedCount} komentar telah dimoderasi!`);
        moderationModal.classList.add('hidden');
        fabContainer.classList.add('hidden');
        // Optional: Remove checked items from board or mark as 'Deleted'
        // For now just uncheck them
        mockData.forEach(d => d.checked = false);
        renderTable(mockData);
    });

    function generateAIInsight(total, gamblingCount) {
        const insightText = document.getElementById('aiInsightText');
        if (total === 0) {
            insightText.innerText = "Tidak ada data untuk dianalisa.";
            return;
        }
        const gamblingPercentage = ((gamblingCount / total) * 100).toFixed(0);
        let message = "";
        if (gamblingPercentage > 50) {
            message = `Perhatian! Terdeteksi aktivitas promosi judi online yang sangat tinggi (${gamblingPercentage}%). Kolom komentar video ini sangat terkontaminasi oleh bot atau akun spam judol. Disarankan untuk segera melakukan pembersihan filter komentar.`;
        } else if (gamblingPercentage > 10) {
            message = `Terdeteksi adanya indikasi promosi judi online sebesar ${gamblingPercentage}%. Meskipun didominasi komentar bersih, tetap waspada terhadap akun-akun yang menyisipkan link mencurigakan.`;
        } else {
            message = `Kabar baik! Kolom komentar terlihat relatif bersih. Hanya ${gamblingPercentage}% komentar yang terindikasi sebagai spam atau promosi judi online. Interaksi pengguna asli mendominasi video ini.`;
        }
        insightText.textContent = message;
    }
});
