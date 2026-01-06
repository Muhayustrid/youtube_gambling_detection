
// ===== PREPARATION & UTILS =====

window.detectUrlType = function (url) {
    if (!url) return 'unknown';
    if (url.includes('@') || url.includes('/channel/') || url.includes('/c/') || url.includes('/user/')) {
        return 'channel';
    }
    else if (url.includes('watch?v=') || url.includes('youtu.be') || url.includes('/shorts/') || url.includes('/live/')) {
        return 'video';
    }
    return 'unknown';
};

window.toggleInputFields = function () {
    const urlInput = document.getElementById('urlInput');
    const videoInputContainer = document.getElementById('videoInputContainer');
    const channelInputContainer = document.getElementById('channelInputContainer');
    const commentsPerVideoContainer = document.getElementById('commentsPerVideoContainer');
    const maxResultsSelect = document.getElementById('maxResults');
    const videoCountSelect = document.getElementById('videoCount');
    const commentsPerVideoSelect = document.getElementById('commentsPerVideo');

    if (!urlInput) return;

    const url = urlInput.value.trim();
    const urlType = window.detectUrlType(url);

    console.log("Input berubah, Tipe:", urlType);

    if (urlType === 'channel') {
        // MODE CHANNEL: Tampilkan input khusus channel
        if (videoInputContainer) videoInputContainer.classList.add('hidden');
        if (channelInputContainer) channelInputContainer.classList.remove('hidden');
        if (commentsPerVideoContainer) commentsPerVideoContainer.classList.remove('hidden');

        // Aktifkan select channel, Matikan select video
        if (maxResultsSelect) maxResultsSelect.disabled = true;
        if (videoCountSelect) videoCountSelect.disabled = false;
        if (commentsPerVideoSelect) commentsPerVideoSelect.disabled = false;

    } else {
        // MODE VIDEO (Default): Tampilkan input video biasa
        if (videoInputContainer) videoInputContainer.classList.remove('hidden');
        if (channelInputContainer) channelInputContainer.classList.add('hidden');
        if (commentsPerVideoContainer) commentsPerVideoContainer.classList.add('hidden');

        // Aktifkan select video, Matikan select channel
        if (maxResultsSelect) maxResultsSelect.disabled = false;
        if (videoCountSelect) videoCountSelect.disabled = true;
        if (commentsPerVideoSelect) commentsPerVideoSelect.disabled = true;
    }
};

window.updateFab = function () {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    const fabContainer = document.getElementById('fabContainer');
    const fabCount = document.getElementById('fabCount');
    const modCount = document.getElementById('modCountText');

    if (fabCount) fabCount.innerText = checkedBoxes.length;
    if (modCount) modCount.innerText = checkedBoxes.length;

    // Only show/hide FAB if it exists (user is logged in)
    if (fabContainer) {
        checkedBoxes.length > 0 ? fabContainer.classList.remove('hidden') : fabContainer.classList.add('hidden');
    }
};

window.autoCheckGamblingComments = function () {
    const checkboxes = document.querySelectorAll('.row-checkbox');
    if (checkboxes.length > 0) {
        let hasChecked = false;
        checkboxes.forEach(cb => {
            const row = cb.closest('tr');
            if (row && row.dataset.type === 'gambling' && !cb.checked) {
                cb.checked = true;
                hasChecked = true;
            }
        });
        if (hasChecked) {
            window.updateFab();
        }
    }
};

window.toggleAll = function (source) {
    const checkboxes = document.querySelectorAll('.row-checkbox');
    if (checkboxes.length === 0) return; // No checkboxes = user not logged in

    checkboxes.forEach(cb => {
        if (cb.closest('tr').style.display !== 'none') {
            cb.checked = source.checked;
        }
    });
    window.updateFab();
};

window.filterTable = function (value) {
    const rows = document.querySelectorAll('.comment-row');
    if (rows.length === 0) return; // No rows = no results or user not logged in

    rows.forEach(row => {
        if (value === 'all') row.style.display = '';
        else row.style.display = (row.dataset.type === value) ? '' : 'none';
    });
    window.updateFab();
};

// ===== MODAL HELPERS =====

window.openModerationModal = function () {
    // Cek apakah user sudah login dengan memeriksa elemen FAB
    const fabContainer = document.getElementById('fabContainer');

    if (!fabContainer) {
        // FAB tidak ada = user belum login
        const loginModal = document.getElementById('loginRequiredModal');
        if (loginModal) loginModal.classList.remove('hidden');
    } else {
        // FAB ada = user sudah login
        const modModal = document.getElementById('moderationModal');
        if (modModal) modModal.classList.remove('hidden');
    }
};

window.closeModerationModal = function () {
    const el = document.getElementById('moderationModal');
    if (el) el.classList.add('hidden');
};

window.closeLoginRequiredModal = function () {
    const el = document.getElementById('loginRequiredModal');
    if (el) el.classList.add('hidden');
};

window.closeErrorModal = function () {
    const el = document.getElementById('errorModal');
    if (el) el.classList.add('hidden');
};

window.closeSuccessModal = function () {
    const el = document.getElementById('successModal');
    if (el) el.classList.add('hidden');
};

window.openSuccessModal = function (msg) {
    const msgEl = document.getElementById('successModalMsg');
    const modalEl = document.getElementById('successModal');
    if (msgEl) msgEl.innerText = msg;
    if (modalEl) modalEl.classList.remove('hidden');
};

window.openErrorModal = function (msg) {
    const msgEl = document.getElementById('errorModalMsg');
    const modalEl = document.getElementById('errorModal');
    if (msgEl) msgEl.innerText = msg;
    if (modalEl) modalEl.classList.remove('hidden');
};

// ===== INITIALIZATION & EVENTS =====

window.initMain = function (config) {
    window.siteConfig = config || {};
    console.log("Main Script Initialized with Config");

    // --- Definisi Elemen Form ---
    const urlInput = document.getElementById('urlInput');

    // --- Pasang Event Listener Form ---
    if (urlInput) {
        urlInput.addEventListener('input', window.toggleInputFields);
        urlInput.addEventListener('change', window.toggleInputFields);
        window.toggleInputFields();
    }

    // --- Re-inisialisasi FAB saat load ---
    window.updateFab();

    // Event Listener Moderasi 
    const confirmBtn = document.getElementById('confirmModerationBtn');
    if (confirmBtn) {
        // Prevent multiple listeners if initMain is called multiple times? 
        // Usually initMain acts as DOMContentLoaded, called once per page load.
        confirmBtn.addEventListener('click', function () {
            const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
            const ids = Array.from(checkedBoxes).map(cb => cb.value);

            if (ids.length === 0) return;

            // UI Loading
            const originalText = this.innerHTML;
            this.innerHTML = 'Memproses...';
            this.disabled = true;

            // Data Blokir User
            const blockUserCheckbox = document.getElementById('blockUserCheckbox');
            const blockUserVal = blockUserCheckbox && blockUserCheckbox.checked ? '1' : '0';

            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', window.siteConfig.csrfToken);
            formData.append('action', 'reject');
            formData.append('block_user', blockUserVal);
            ids.forEach(id => formData.append('comment_id', id));

            if (!window.siteConfig.moderateUrl) {
                console.error("Moderate URL not found in config");
                window.openErrorModal("Konfigurasi URL tidak ditemukan.");
                this.innerHTML = originalText;
                this.disabled = false;
                return;
            }

            fetch(window.siteConfig.moderateUrl, {
                method: 'POST',
                body: formData
            })
                .then(res => res.json().then(data => ({ status: res.status, body: data })))
                .then(result => {
                    window.closeModerationModal();
                    if (result.body.ok) {
                        window.openSuccessModal(result.body.msg || "Berhasil!");
                        // Hapus baris dari tabel
                        checkedBoxes.forEach(cb => cb.closest('tr').remove());
                        window.updateFab();
                        const selectAll = document.getElementById('selectAllCheckbox');
                        if (selectAll) selectAll.checked = false;
                    } else {
                        window.openErrorModal(result.body.msg || "Gagal moderasi.");
                    }
                })
                .catch(err => {
                    console.error(err);
                    window.closeModerationModal();
                    window.openErrorModal("Koneksi server bermasalah.");
                })
                .finally(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                });
        });
    }
};

// HTMX Hooks
document.body.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.detail.target.id === "resultsContainer") {
        window.updateFab();
        // Auto-check komentar judol setelah partial dimuat
        setTimeout(window.autoCheckGamblingComments, 100);
    }
});

document.body.addEventListener('htmx:afterRequest', function (evt) {
    if (evt.detail.target.id === "resultsContainer" && evt.detail.successful) {
        window.updateFab();
        setTimeout(window.autoCheckGamblingComments, 100);
    }
});

document.body.addEventListener('htmx:afterSettle', function (evt) {
    if (evt.detail.target.id === "resultsContainer") {
        window.updateFab();
        setTimeout(window.autoCheckGamblingComments, 100);
    }
});
