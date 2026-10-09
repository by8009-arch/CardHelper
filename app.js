document.addEventListener('DOMContentLoaded', () => {
    const pendingImgList = document.getElementById('pendingImgList');
    const doneImgList = document.getElementById('doneImgList');
    const pendingCountBadge = document.getElementById('pendingCountBadge');
    const doneCountBadge = document.getElementById('doneCountBadge');
    const dbCountBadge = document.getElementById('dbCountBadge');
    const searchResultCount = document.getElementById('searchResultCount');

    const refreshImgBtn = document.getElementById('refreshImgBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const extractBtn = document.getElementById('extractBtn');
    const extractDefaultNotes = document.getElementById('extractDefaultNotes');
    const toggleDoneBtn = document.getElementById('toggleDoneBtn');
    const doneSection = document.getElementById('doneSection');
    const restoreAllBtn = document.getElementById('restoreAllBtn');

    const cardForm = document.getElementById('cardForm');
    const cardList = document.getElementById('cardList');
    const searchInput = document.getElementById('searchInput');
    const searchFieldSelect = document.getElementById('searchFieldSelect');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const companyFilterBar = document.getElementById('companyFilterBar');
    const alertContainer = document.getElementById('alertContainer');
    const exportCsvBtn = document.getElementById('exportCsvBtn');

    const togglePendingBtn = document.getElementById('togglePendingBtn');
    const pendingCardsBody = document.getElementById('pendingCardsBody');
    const pendingSectionToggle = document.getElementById('pendingSectionToggle');

    const toggleManualBtn = document.getElementById('toggleManualBtn');
    const manualFormBody = document.getElementById('manualFormBody');
    const manualFormToggle = document.getElementById('manualFormToggle');
    const formHeaderTitle = document.getElementById('formHeaderTitle');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const submitCardBtn = document.getElementById('submitCardBtn');
    const editCardIdInput = document.getElementById('editCardId');

    // Conflict Modal elements
    const conflictModal = document.getElementById('conflictModal');
    const conflictModalTitle = document.getElementById('conflictModalTitle');
    const conflictModalSubtitle = document.getElementById('conflictModalSubtitle');
    const conflictQueueBadge = document.getElementById('conflictQueueBadge');
    const conflictComparisonBody = document.getElementById('conflictComparisonBody');
    const applyAllConflictWrap = document.getElementById('applyAllConflictWrap');
    const applyAllConflictCheck = document.getElementById('applyAllConflictCheck');
    const conflictUpdateBtn = document.getElementById('conflictUpdateBtn');
    const conflictReplaceBtn = document.getElementById('conflictReplaceBtn');
    const conflictCreateNewBtn = document.getElementById('conflictCreateNewBtn');
    const conflictSkipBtn = document.getElementById('conflictSkipBtn');

    // Merge 2 Cards Modal & Toolbar elements
    const mergeSelectionHint = document.getElementById('mergeSelectionHint');
    const clearCardSelectionBtn = document.getElementById('clearCardSelectionBtn');
    const mergeSelectedCardsBtn = document.getElementById('mergeSelectedCardsBtn');
    const mergeSelectedCount = document.getElementById('mergeSelectedCount');
    const mergeCardsModal = document.getElementById('mergeCardsModal');
    const mergeCardsComparisonBody = document.getElementById('mergeCardsComparisonBody');
    const swapMergeOrderBtn = document.getElementById('swapMergeOrderBtn');
    const cancelMergeModalBtn = document.getElementById('cancelMergeModalBtn');
    const confirmMergeModalBtn = document.getElementById('confirmMergeModalBtn');

    let pendingFiles = [];
    let doneFiles = [];
    let selectedFiles = new Set();
    let selectedMergeCardIds = []; // Up to 2 card IDs in selection order [primaryId, secondaryId]
    let cards = [];
    let activeCompanyFilter = '';

    function showAlert(message, type = 'success') {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show shadow-sm" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" onclick="this.parentElement.remove()"></button>
            </div>
        `;
        alertContainer.prepend(wrapper.firstElementChild);
        setTimeout(() => {
            if (alertContainer.lastElementChild) {
                alertContainer.lastElementChild.remove();
            }
        }, 6500);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function highlightText(str, query) {
        const safeStr = escapeHtml(str);
        if (!query || !safeStr) return safeStr;
        const escapedQ = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQ})`, 'gi');
        return safeStr.replace(regex, '<mark class="search-highlight">$1</mark>');
    }

    function normalizePhoneCore(phoneStr) {
        if (!phoneStr) return '';
        const primary = String(phoneStr).trim().split(/[(（/]/)[0].trim();
        const m = primary.match(/^(?:\+|00)\s*(886|852|853|86|81|82|65|60|66|84|62|63|91|44|49|33|61|1)[\s\-]*/);
        if (m) {
            const rest = primary.slice(m[0].length);
            return rest.replace(/\D+/g, '').replace(/^0+/, '');
        }
        let digits = primary.replace(/\D+/g, '');
        if (digits.startsWith('886') && digits.length >= 11) {
            digits = digits.slice(3);
        } else if (digits.startsWith('81') && digits.length >= 11) {
            digits = digits.slice(2);
        }
        return digits.replace(/^0+/, '');
    }

    function isSamePhone(p1, p2) {
        const c1 = normalizePhoneCore(p1);
        const c2 = normalizePhoneCore(p2);
        return Boolean(c1 && c2 && c1 === c2);
    }

    function renderComparisonCard(cardObj, badgeText, badgeClass, otherObj, isNewSide) {
        const fields = [
            { key: 'name', label: '姓名' },
            { key: 'english_name', label: '英文名' },
            { key: 'company', label: '公司' },
            { key: 'title', label: '職稱' },
            { key: 'tax_id', label: '統一編號' },
            { key: 'phone', label: '公司電話', isPhone: true },
            { key: 'mobile', label: '個人電話', isPhone: true },
            { key: 'fax', label: '傳真', isPhone: true },
            { key: 'email', label: 'Email' },
            { key: 'address', label: '地址' },
            { key: 'website', label: '網址' },
            { key: 'notes', label: '備註' }
        ];

        const rowsHtml = fields.map(f => {
            const val = (cardObj[f.key] || '').trim();
            const otherVal = (otherObj[f.key] || '').trim();
            const samePhoneNoCC = f.isPhone && isSamePhone(val, otherVal);
            const isDiff = isNewSide && val !== otherVal && val !== '' && !samePhoneNoCC;
            const samePhoneBadge = (isNewSide && f.isPhone && val && otherVal && val !== otherVal && samePhoneNoCC)
                ? '<span class="badge bg-secondary-subtle text-secondary ms-1 fw-normal">去國碼相同</span>'
                : '';
            return `
                <div class="d-flex justify-content-between border-bottom py-1 small gap-2">
                    <span class="text-muted text-nowrap">${f.label}：</span>
                    <span class="text-end text-break ${isDiff ? 'diff-changed' : ''}">
                        ${val ? escapeHtml(val) + samePhoneBadge : '<span class="text-muted fst-italic">（未填寫）</span>'}
                    </span>
                </div>
            `;
        }).join('');

        return `
            <div class="col-md-6">
                <div class="border rounded-3 p-3 h-100 ${isNewSide ? 'bg-success-subtle border-success' : 'bg-white'}">
                    <div class="mb-2 d-flex justify-content-between align-items-center">
                        <span class="badge ${badgeClass}">${badgeText}</span>
                        ${cardObj.source_file ? `<small class="text-muted text-truncate ms-2" style="max-width: 190px;" title="${escapeHtml(cardObj.source_file)}">📷 ${escapeHtml(cardObj.source_file)}</small>` : ''}
                    </div>
                    ${rowsHtml}
                </div>
            </div>
        `;
    }

    function promptSingleConflict(item, index, total) {
        return new Promise((resolve) => {
            const existing = item.existing_card || {};
            const incoming = item.new_card || {};
            const merged = item.merged_preview || {};
            const matchReason = item.match_reason || '相同姓名或同公司同 Email';

            const exName = (existing.name || '').trim();
            const inName = (incoming.name || '').trim();
            const namesDiffer = exName && inName && exName.toLowerCase() !== inName.toLowerCase();

            if (namesDiffer) {
                conflictModalTitle.textContent = `發現同一人的名片：「${exName}」 ⇄ 「${inName}」`;
            } else {
                conflictModalTitle.textContent = `發現相同人員的名片：「${inName || exName}」`;
            }

            const srcFname = item.source_filename || item.filename;
            const multiCardNote = (item.total_cards_in_file && item.total_cards_in_file > 1)
                ? `［單檔多張：第 ${item.card_index} / ${item.total_cards_in_file} 張］`
                : '';
            conflictModalSubtitle.textContent = srcFname && srcFname !== 'manual'
                ? `來源圖檔：${srcFname} ${multiCardNote}（判定原因：${matchReason}）— 請選擇要「更新 / 新增欄位」還是「取代」`
                : `判定原因：${matchReason} — 請選擇要「更新 / 新增欄位」還是「取代」`;

            if (total > 1) {
                conflictQueueBadge.textContent = `第 ${index + 1} / ${total} 筆重複`;
                conflictQueueBadge.classList.remove('d-none');
                applyAllConflictWrap.classList.remove('d-none');
            } else {
                conflictQueueBadge.classList.add('d-none');
                applyAllConflictWrap.classList.add('d-none');
            }

            const mergedPreviewHtml = merged.name ? `
                <div class="col-12">
                    <div class="p-2 px-3 rounded-3 bg-primary-subtle border border-primary-subtle small">
                        <div class="fw-bold text-primary mb-1">
                            ✨ 若選擇「🔄 更新 / 新增欄位」，合併後結果預覽：
                        </div>
                        <div class="row g-2 text-dark">
                            <div class="col-md-6">
                                <strong>👤 合併後姓名：</strong>
                                <span class="badge bg-primary fs-6">${escapeHtml(merged.name)}</span>
                                ${namesDiffer ? '<span class="text-muted ms-1">(英文名自動置於中文名後)</span>' : ''}
                            </div>
                            <div class="col-md-6">
                                <strong>🏢 合併後公司：</strong> ${escapeHtml(merged.company || '')}
                            </div>
                            ${merged.title ? `<div class="col-md-6"><strong>💼 合併後職稱：</strong> ${escapeHtml(merged.title)}</div>` : ''}
                            ${merged.tax_id ? `<div class="col-md-6"><strong>🧾 統一編號：</strong> ${escapeHtml(merged.tax_id)}</div>` : ''}
                            ${merged.email ? `<div class="col-md-6"><strong>✉️ Email：</strong> ${escapeHtml(merged.email)}</div>` : ''}
                        </div>
                    </div>
                </div>
            ` : '';

            conflictComparisonBody.innerHTML =
                renderComparisonCard(existing, '📂 資料庫現有名片', 'bg-secondary', incoming, false) +
                renderComparisonCard(incoming, '✨ 新輸入 / 提取名片', 'bg-success', existing, true) +
                mergedPreviewHtml;

            conflictModal.classList.remove('d-none');

            function cleanup(action) {
                const applyAll = total > 1 && applyAllConflictCheck.checked;
                conflictUpdateBtn.onclick = null;
                conflictReplaceBtn.onclick = null;
                conflictCreateNewBtn.onclick = null;
                conflictSkipBtn.onclick = null;
                resolve({ action, applyAll, target_id: existing.id });
            }

            conflictUpdateBtn.onclick = () => cleanup('update');
            conflictReplaceBtn.onclick = () => cleanup('replace');
            conflictCreateNewBtn.onclick = () => cleanup('create');
            conflictSkipBtn.onclick = () => cleanup('skip');
        });
    }

    async function promptConflictResolution(conflictsList) {
        const resolutions = {};
        applyAllConflictCheck.checked = false;
        let batchAction = null;

        for (let i = 0; i < conflictsList.length; i++) {
            const item = conflictsList[i];
            if (batchAction) {
                resolutions[item.filename] = {
                    action: batchAction,
                    target_id: (item.existing_card || {}).id
                };
                continue;
            }
            const choice = await promptSingleConflict(item, i, conflictsList.length);
            resolutions[item.filename] = {
                action: choice.action,
                target_id: choice.target_id
            };
            if (choice.applyAll) {
                batchAction = choice.action;
            }
        }

        conflictModal.classList.add('d-none');
        return resolutions;
    }

    function updateSelectionUI() {
        const countSpan = document.getElementById('selectedCount');
        if (countSpan) countSpan.textContent = selectedFiles.size;
        extractBtn.disabled = selectedFiles.size === 0;
        document.querySelectorAll('.img-select-card').forEach(el => {
            const fname = el.getAttribute('data-filename');
            if (selectedFiles.has(fname)) {
                el.classList.add('selected');
            } else {
                el.classList.remove('selected');
            }
        });
    }

    function renderPendingImages() {
        pendingCountBadge.textContent = pendingFiles.length;
        doneCountBadge.textContent = doneFiles.length;

        if (doneFiles.length > 0) {
            restoreAllBtn.classList.remove('d-none');
        } else {
            restoreAllBtn.classList.add('d-none');
        }

        const currentNames = new Set(pendingFiles.map(f => f.filename));
        for (const name of Array.from(selectedFiles)) {
            if (!currentNames.has(name)) {
                selectedFiles.delete(name);
            }
        }

        if (pendingFiles.length === 0) {
            pendingImgList.innerHTML = `
                <div class="col-12 text-center py-4 text-muted">
                    <div class="fs-2 mb-2">🎉</div>
                    <p class="mb-1 fw-semibold">目前 <code>img/</code> 目錄中沒有待處理的名片圖檔！</p>
                    <small>您可以將新的名片照片放入 <code>img/</code> 資料夾後點擊「重新掃描目錄」，或從下方 <code>done/</code> 目錄還原名片測試。</small>
                </div>
            `;
        } else {
            pendingImgList.innerHTML = '';
            pendingFiles.forEach(item => {
                const isSelected = selectedFiles.has(item.filename);
                const cardCount = item.card_count || 1;
                const multiBadgeHtml = cardCount > 1
                    ? `<span class="badge bg-warning text-dark position-absolute bottom-0 start-0 m-2 shadow-sm">📇 內含 ${cardCount} 張名片</span>`
                    : '';
                const col = document.createElement('div');
                col.className = 'col-sm-6 col-md-4 col-lg-3';
                col.innerHTML = `
                    <div class="img-select-card h-100 ${isSelected ? 'selected' : ''}" data-filename="${escapeHtml(item.filename)}">
                        <div class="img-thumb-wrapper">
                            <div class="select-badge">✓</div>
                            <img src="${item.preview_url}" alt="${escapeHtml(item.filename)}" loading="lazy">
                            ${multiBadgeHtml}
                            <button type="button" class="zoom-btn" title="點擊放大檢視">🔍 放大</button>
                        </div>
                        <div class="p-2">
                            <div class="small fw-semibold text-truncate" title="${escapeHtml(item.filename)}">
                                ${escapeHtml(item.filename)}
                            </div>
                            <div class="d-flex justify-content-between align-items-center mt-1">
                                <span class="badge bg-light text-secondary border">${(item.size / 1024).toFixed(0)} KB</span>
                                <button type="button" class="btn btn-link btn-sm p-0 text-success fw-semibold single-extract-btn">
                                    ${cardCount > 1 ? `⚡ 提取 (${cardCount}張)` : '⚡ 單張提取'}
                                </button>
                            </div>
                        </div>
                    </div>
                `;

                const cardEl = col.querySelector('.img-select-card');
                cardEl.addEventListener('click', () => {
                    if (selectedFiles.has(item.filename)) {
                        selectedFiles.delete(item.filename);
                    } else {
                        selectedFiles.add(item.filename);
                    }
                    updateSelectionUI();
                });

                const zoomBtn = col.querySelector('.zoom-btn');
                zoomBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    openImageModal(item.preview_url, item.filename);
                });

                const singleBtn = col.querySelector('.single-extract-btn');
                singleBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    extractFiles([item.filename]);
                });

                pendingImgList.appendChild(col);
            });
        }

        renderDoneImages();
        updateSelectionUI();
    }

    function renderDoneImages() {
        doneImgList.innerHTML = '';
        if (doneFiles.length === 0) {
            doneImgList.innerHTML = '<div class="col-12 text-muted small">目前 done/ 目錄尚無已歸檔的名片圖檔。</div>';
            return;
        }
        doneFiles.forEach(item => {
            const sizeKb = Math.round((item.size || 0) / 1024);
            const col = document.createElement('div');
            col.className = 'col-sm-6 col-md-4 col-lg-3';
            col.innerHTML = `
                <div class="border rounded p-2 bg-light d-flex align-items-center justify-content-between gap-2">
                    <img src="${item.preview_url}" alt="${escapeHtml(item.filename)}" class="card-source-thumb" onclick="openImageModal('${item.preview_url}', '${escapeHtml(item.filename)}')">
                    <div class="flex-grow-1 overflow-hidden">
                        <div class="small fw-semibold text-truncate" title="${escapeHtml(item.filename)}">${escapeHtml(item.filename)}</div>
                        <div class="d-flex align-items-center justify-content-between mt-1">
                            <span class="badge bg-white text-secondary border" style="font-size: 11px;">${sizeKb} KB</span>
                            <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2 restore-btn" style="font-size: 12px;">
                                ↩️ 移回 img
                            </button>
                        </div>
                    </div>
                </div>
            `;
            col.querySelector('.restore-btn').addEventListener('click', () => {
                restoreFiles([item.filename]);
            });
            doneImgList.appendChild(col);
        });
    }

    function updateMergeCardSelectionUI() {
        const existingIds = new Set(cards.map(c => c.id));
        selectedMergeCardIds = selectedMergeCardIds.filter(id => existingIds.has(id));

        const count = selectedMergeCardIds.length;
        if (mergeSelectedCount) mergeSelectedCount.textContent = count;
        if (mergeSelectedCardsBtn) mergeSelectedCardsBtn.disabled = count !== 2;
        if (clearCardSelectionBtn) {
            if (count > 0) {
                clearCardSelectionBtn.classList.remove('d-none');
            } else {
                clearCardSelectionBtn.classList.add('d-none');
            }
        }
        if (mergeSelectionHint) {
            if (count === 0) {
                mergeSelectionHint.textContent = '勾選任意 2 張名片即可合併';
            } else if (count === 1) {
                mergeSelectionHint.textContent = '已選 1 張，請再勾選第 2 張名片';
            } else {
                mergeSelectionHint.textContent = '已選滿 2 張，請點擊右側按鈕合併';
            }
        }

        document.querySelectorAll('.card-item[data-card-id]').forEach(cardEl => {
            const cid = cardEl.getAttribute('data-card-id');
            const idx = selectedMergeCardIds.indexOf(cid);
            const checkInput = cardEl.querySelector('.card-merge-checkbox');
            const checkText = cardEl.querySelector('.card-merge-check-text');
            if (idx !== -1) {
                cardEl.classList.add('merge-selected');
                if (checkInput) checkInput.checked = true;
                if (checkText) {
                    checkText.textContent = idx === 0 ? '已選取 #1 (主名片)' : '已選取 #2 (併入)';
                }
            } else {
                cardEl.classList.remove('merge-selected');
                if (checkInput) checkInput.checked = false;
                if (checkText) {
                    checkText.textContent = '勾選合併';
                }
            }
        });
    }

    function toggleMergeCardSelect(cardId) {
        const idx = selectedMergeCardIds.indexOf(cardId);
        if (idx !== -1) {
            selectedMergeCardIds.splice(idx, 1);
        } else {
            if (selectedMergeCardIds.length >= 2) {
                showAlert('ℹ️ 一次只能選擇 2 張名片進行合併！若要更換，請先取消勾選其中一張。', 'warning');
                updateMergeCardSelectionUI();
                return;
            }
            selectedMergeCardIds.push(cardId);
        }
        updateMergeCardSelectionUI();
    }

    async function openMergeCardsModal() {
        if (selectedMergeCardIds.length !== 2) return;
        try {
            const res = await fetch('/api/cards/merge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    card_ids: selectedMergeCardIds,
                    preview_only: true
                })
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
                showAlert(data.error || '無法載入合併預覽', 'danger');
                return;
            }

            const c1 = data.card1 || {};
            const c2 = data.card2 || {};
            const mp = data.merged_preview || {};

            mergeCardsComparisonBody.innerHTML =
                renderComparisonCard(c1, '1️⃣ 主名片 (#1)', 'bg-primary', c2, false) +
                renderComparisonCard(c2, '2️⃣ 併入名片 (#2)', 'bg-success', c1, true);

            const fieldKeys = ['name', 'english_name', 'tax_id', 'company', 'title', 'phone', 'mobile', 'fax', 'email', 'website', 'address', 'notes'];
            fieldKeys.forEach(k => {
                const el = document.getElementById(`merge_${k}`);
                if (el) el.value = mp[k] || '';
            });

            mergeCardsModal.classList.remove('d-none');
        } catch (err) {
            showAlert('載入合併預覽失敗：' + err.message, 'danger');
        }
    }

    async function executeMergeSelectedCards() {
        if (selectedMergeCardIds.length !== 2) return;
        const mergedData = {};
        const fieldKeys = ['name', 'english_name', 'tax_id', 'company', 'title', 'phone', 'mobile', 'fax', 'email', 'website', 'address', 'notes'];
        fieldKeys.forEach(k => {
            const el = document.getElementById(`merge_${k}`);
            if (el) mergedData[k] = el.value.trim();
        });

        confirmMergeModalBtn.disabled = true;
        try {
            const res = await fetch('/api/cards/merge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    card_ids: selectedMergeCardIds,
                    preview_only: false,
                    merged_data: mergedData
                })
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
                showAlert(data.error || '合併失敗', 'danger');
                return;
            }

            mergeCardsModal.classList.add('d-none');
            selectedMergeCardIds = [];
            cards = data.cards || [];
            renderCards();
            const mergedName = (data.merged_card && data.merged_card.name) || mergedData.name || '名片';
            showAlert(`🔗 已成功將兩張名片合併為「<strong>${escapeHtml(mergedName)}</strong>」！`, 'success');
        } catch (err) {
            showAlert('合併過程發生錯誤：' + err.message, 'danger');
        } finally {
            confirmMergeModalBtn.disabled = false;
        }
    }

    const COUNTRY_DEFINITIONS = [
        { key: 'TW', label: '🇹🇼 台灣', name: '台灣 Taiwan' },
        { key: 'JP', label: '🇯🇵 日本', name: '日本 Japan' },
        { key: 'IN', label: '🇮🇳 印度', name: '印度 India' },
        { key: 'US', label: '🇺🇸 美國', name: '美國 USA' },
        { key: 'CN', label: '🇨🇳 中國', name: '中國 China' },
        { key: 'HK', label: '🇭🇰 香港', name: '香港 Hong Kong' },
        { key: 'SG', label: '🇸🇬 新加坡', name: '新加坡 Singapore' },
        { key: 'KR', label: '🇰🇷 韓國', name: '韓國 Korea' }
    ];

    function detectCardCountries(card) {
        const comp = (card.company || '').trim();
        const addr = (card.address || '').trim();
        const title = (card.title || '').trim();
        const phoneStr = [card.phone, card.mobile, card.fax].filter(Boolean).join(' ');
        const emailWeb = [card.email, card.website].filter(Boolean).join(' ').toLowerCase();
        const taxId = (card.tax_id || '').trim();

        const matched = [];

        // 日本 (JP)
        if (
            /(株式会社|有限会社|合同会社|〒|\bJapan\b|\bTokyo\b|\bOsaka\b|\bChiba\b|東京都|千葉県|大阪府|神奈川県|京都府|北海道|福岡県|渋谷区|中央区)/i.test(comp + ' ' + addr) ||
            /(?:\+81[\s\-]|\b0[789]0-\d{4}-\d{4}|\b03-\d{4}-\d{4}|\b043-\d{3}-\d{4})/.test(phoneStr) ||
            /\.jp(?:\b|\/|$)/.test(emailWeb)
        ) {
            matched.push('JP');
        }

        // 印度 (IN)
        if (
            /(\bIndia\b|\bNew Delhi\b|\bDelhi\b|\bChennai\b|\bTamil Nadu\b|\bBengaluru\b|\bBangalore\b|\bKarnataka\b|\bMumbai\b|\bPvt\.?\s*Ltd)/i.test(comp + ' ' + addr + ' ' + title) ||
            /(?:\+91[\s\-]|\b91[\s\-]+\d{2,5})/.test(phoneStr) ||
            /\.in(?:\b|\/|$)/.test(emailWeb)
        ) {
            matched.push('IN');
        }

        // 美國 (US)
        if (
            /(\bUSA\b|\bU\.S\.A\.\b|\bUnited States\b|\bCalifornia\b|\bNew York\b)/i.test(addr) ||
            /(?:^\+1[\s\-]|\s\+1[\s\-])/.test(phoneStr)
        ) {
            matched.push('US');
        }

        // 中國 (CN)
        if (
            /(\bChina\b|\bP\.R\.C\.\b|北京市|上海市|深圳市|廣州市|广东省|江苏省|浙江省)/i.test(addr) ||
            /(?:\+86[\s\-])/.test(phoneStr) ||
            /\.cn(?:\b|\/|$)/.test(emailWeb)
        ) {
            matched.push('CN');
        }

        // 香港 (HK)
        if (
            /(\bHong Kong\b|\bKowloon\b|香港|九龍)/i.test(addr) ||
            /(?:\+852[\s\-])/.test(phoneStr) ||
            /\.hk(?:\b|\/|$)/.test(emailWeb)
        ) {
            matched.push('HK');
        }

        // 新加坡 (SG)
        if (
            /(\bSingapore\b|新加坡)/i.test(addr) ||
            /(?:\+65[\s\-])/.test(phoneStr) ||
            /\.sg(?:\b|\/|$)/.test(emailWeb)
        ) {
            matched.push('SG');
        }

        // 韓國 (KR)
        if (
            /(\bKorea\b|\bSeoul\b|韓國|首爾)/i.test(addr) ||
            /(?:\+82[\s\-])/.test(phoneStr) ||
            /\.kr(?:\b|\/|$)/.test(emailWeb)
        ) {
            matched.push('KR');
        }

        // 台灣 (TW)
        if (
            /(\bTaiwan\b|R\.O\.C|台灣|臺灣|台北|新北|桃園|桃國|新竹|苗栗|台中|彰化|南投|雲林|嘉義|台南|高雄|屏東|宜蘭|花蓮|台東|\bTaipei\b|\bTaoyuan\b|\bTaichung\b|\bTainan\b|\bKaohsiung\b|\bHsinchu\b|\bChang Hua\b)/i.test(addr) ||
            /(?:\+?886[\s\-]|\(0[2-8]\)|0[2-8]-\d{3,4}|\b09\d{2}[\s\-]?\d{3}[\s\-]?\d{3}\b)/.test(phoneStr) ||
            /^\d{8}$/.test(taxId) ||
            (/股份有限公司|\(股\)公司|有限公司/.test(comp) && !/株式会社|有限会社|合同会社/.test(comp)) ||
            (matched.length === 0 && /\.tw(?:\b|\/|$)/.test(emailWeb))
        ) {
            matched.push('TW');
        }

        if (matched.length === 0) {
            matched.push('TW');
        }

        return matched;
    }

    function renderCompanyFilters() {
        companyFilterBar.innerHTML = '';
        if (cards.length === 0) return;

        const importantCount = cards.filter(c => c.important).length;

        const label = document.createElement('span');
        label.className = 'small text-muted me-1';
        label.textContent = '🌍 快速篩選：';
        companyFilterBar.appendChild(label);

        const allBtn = document.createElement('button');
        allBtn.type = 'button';
        allBtn.className = `btn btn-sm company-pill ${activeCompanyFilter === '' ? 'btn-primary' : 'btn-outline-secondary'}`;
        allBtn.textContent = `全部 (${cards.length})`;
        allBtn.addEventListener('click', () => {
            activeCompanyFilter = '';
            renderCards();
        });
        companyFilterBar.appendChild(allBtn);

        const impBtn = document.createElement('button');
        impBtn.type = 'button';
        impBtn.className = `btn btn-sm company-pill fw-semibold ${activeCompanyFilter === '__important__' ? 'btn-warning text-dark' : 'btn-outline-warning text-dark'}`;
        impBtn.innerHTML = `⭐ 重要 (${importantCount})`;
        impBtn.addEventListener('click', () => {
            activeCompanyFilter = activeCompanyFilter === '__important__' ? '' : '__important__';
            renderCards();
        });
        companyFilterBar.appendChild(impBtn);

        COUNTRY_DEFINITIONS.forEach(country => {
            const count = cards.filter(c => detectCardCountries(c).includes(country.key)).length;
            if (count === 0) return;
            const filterKey = `country:${country.key}`;
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `btn btn-sm company-pill ${activeCompanyFilter === filterKey ? 'btn-primary' : 'btn-outline-secondary'}`;
            btn.textContent = `${country.label} (${count})`;
            btn.addEventListener('click', () => {
                activeCompanyFilter = activeCompanyFilter === filterKey ? '' : filterKey;
                renderCards();
            });
            companyFilterBar.appendChild(btn);
        });
    }

    function renderCards() {
        dbCountBadge.textContent = `名片庫：${cards.length} 張`;
        renderCompanyFilters();

        const q = (searchInput.value || '').trim().toLowerCase();
        const field = searchFieldSelect.value;

        if (q || activeCompanyFilter) {
            clearSearchBtn.classList.remove('d-none');
        } else {
            clearSearchBtn.classList.add('d-none');
        }

        const filtered = cards.filter(c => {
            const cardCountries = detectCardCountries(c);
            if (activeCompanyFilter === '__important__') {
                if (!c.important) return false;
            } else if (activeCompanyFilter && activeCompanyFilter.startsWith('country:')) {
                const targetCountry = activeCompanyFilter.slice('country:'.length);
                if (!cardCountries.includes(targetCountry)) return false;
            } else if (activeCompanyFilter && (c.company || '').trim() !== activeCompanyFilter) {
                return false;
            }
            if (!q) return true;

            const countrySearchNames = cardCountries
                .map(k => (COUNTRY_DEFINITIONS.find(d => d.key === k) || {}).name || '')
                .join(' ');

            let fieldsToSearch = [];
            if (field === 'name') {
                fieldsToSearch = [c.name, c.english_name];
            } else if (field === 'company') {
                fieldsToSearch = [c.company, c.tax_id];
            } else if (field === 'tax_id') {
                fieldsToSearch = [c.tax_id];
            } else if (field === 'title') {
                fieldsToSearch = [c.title];
            } else if (field === 'contact') {
                fieldsToSearch = [c.phone, c.mobile, c.fax, c.email];
            } else if (field === 'address') {
                fieldsToSearch = [c.address, c.website, countrySearchNames];
            } else if (field === 'notes') {
                fieldsToSearch = [c.notes];
            } else {
                fieldsToSearch = [c.name, c.english_name, c.company, c.tax_id, c.title, c.phone, c.mobile, c.fax, c.email, c.address, c.website, c.notes, countrySearchNames, c.important ? '重要' : ''];
            }

            return fieldsToSearch.some(val => val && String(val).toLowerCase().includes(q));
        });

        searchResultCount.textContent = `顯示 ${filtered.length} / ${cards.length} 張`;

        cardList.innerHTML = '';
        if (filtered.length === 0) {
            cardList.innerHTML = `
                <div class="col-12 text-center py-5 text-muted">
                    <div class="fs-1 mb-2">📇</div>
                    <p class="mb-0">${cards.length === 0 ? '名片資料庫目前是空的，請從上方選擇 img/ 名片圖檔自動提取，或手動新增名片！' : '找不到符合搜尋或篩選條件的名片。'}</p>
                </div>
            `;
            updateMergeCardSelectionUI();
            return;
        }

        filtered.forEach(card => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4';
            const previewUrl = card.source_file
                ? `/api/preview?folder=done&file=${encodeURIComponent(card.source_file)}`
                : '';

            const nameStr = (card.name || '').trim();
            const engStr = (card.english_name || '').trim();
            const showSeparateEng = engStr && !nameStr.toLowerCase().includes(engStr.toLowerCase());

            const allSources = [card.source_file, ...(Array.isArray(card.extra_source_files) ? card.extra_source_files : [])].filter(Boolean);
            const mergeIdx = selectedMergeCardIds.indexOf(card.id);
            const isMergeSelected = mergeIdx !== -1;
            const isImportant = Boolean(card.important);
            const cardCountries = detectCardCountries(card);
            const countryBadgesHtml = cardCountries
                .map(k => {
                    const def = COUNTRY_DEFINITIONS.find(d => d.key === k);
                    return def ? `<span class="badge bg-light text-secondary border" style="font-size: 11px;">${def.label}</span>` : '';
                })
                .join('');

            col.innerHTML = `
                <div class="card card-item h-100 shadow-sm bg-white ${isMergeSelected ? 'merge-selected' : ''} ${isImportant ? 'border-warning border-2' : ''}" data-card-id="${escapeHtml(card.id)}">
                    <div class="card-body d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-1">
                            <label class="card-merge-check-label d-inline-flex align-items-center gap-1 mb-0" title="勾選此名片以與另一張名片合併">
                                <input type="checkbox" class="form-check-input mt-0 card-merge-checkbox" ${isMergeSelected ? 'checked' : ''}>
                                <span class="card-merge-check-text">${isMergeSelected ? (mergeIdx === 0 ? '已選取 #1 (主名片)' : '已選取 #2 (併入)') : '勾選合併'}</span>
                            </label>
                            <div class="d-flex align-items-center gap-1 flex-wrap">
                                ${countryBadgesHtml}
                                ${allSources.length > 1 ? `<span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size: 11px;">已合併 ${allSources.length} 張圖檔</span>` : ''}
                                <button type="button" class="btn btn-sm py-0 px-2 fw-semibold toggle-important-btn ${isImportant ? 'btn-warning text-dark shadow-sm' : 'btn-outline-warning text-dark'}" style="font-size: 12px;" title="${isImportant ? '點擊取消「重要」標記（並從電腦聯絡人移除）' : '標定為「重要」並自動加入電腦的聯絡人資訊'}">
                                    ${isImportant ? '⭐ 重要 (已入聯絡人)' : '☆ 標記重要'}
                                </button>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                            <div>
                                <h5 class="card-title text-primary fw-bold mb-1">
                                    ${isImportant ? '<span title="重要名片">⭐</span> ' : ''}${highlightText(card.name || '（未填寫姓名）', q)}
                                    ${showSeparateEng ? `<span class="text-secondary fs-6 fw-normal">(${highlightText(card.english_name, q)})</span>` : ''}
                                </h5>
                                <div class="text-dark fw-semibold small">${highlightText(card.company || '未填寫公司', q)}</div>
                                ${card.title ? `<div class="text-muted small">${highlightText(card.title, q)}</div>` : ''}
                            </div>
                            ${previewUrl ? `
                                <img src="${previewUrl}" class="card-source-thumb flex-shrink-0" title="點擊查看原始名片圖檔 (${escapeHtml(card.source_file)})" onclick="openImageModal('${previewUrl}', '${escapeHtml(card.source_file)}')">
                            ` : ''}
                        </div>
                        <hr class="my-2">
                        <div class="small flex-grow-1 d-flex flex-column gap-1">
                            ${card.tax_id ? `<div><strong>🧾 統一編號：</strong>${highlightText(card.tax_id, q)}</div>` : ''}
                            ${card.phone ? `<div><strong>☎️ 公司電話：</strong><a href="tel:${escapeHtml(card.phone)}" class="text-decoration-none">${highlightText(card.phone, q)}</a></div>` : ''}
                            ${card.mobile ? `<div><strong>📱 個人電話：</strong><a href="tel:${escapeHtml(card.mobile)}" class="text-decoration-none">${highlightText(card.mobile, q)}</a></div>` : ''}
                            ${card.fax ? `<div><strong>📠 傳真號碼：</strong>${highlightText(card.fax, q)}</div>` : ''}
                            ${card.email ? `<div><strong>✉️ 電子郵件：</strong><a href="mailto:${escapeHtml(card.email)}">${highlightText(card.email, q)}</a></div>` : ''}
                            ${card.address ? `<div><strong>📍 公司地址：</strong>${highlightText(card.address, q)}</div>` : ''}
                            ${card.website ? `<div><strong>🌐 公司網址：</strong><a href="${escapeHtml(card.website)}" target="_blank" rel="noopener">${highlightText(card.website, q)}</a></div>` : ''}

                            <!-- 備註顯示與快速編輯區塊 -->
                            <div class="mt-2 pt-1">
                                <div class="notes-display-area">
                                    ${card.notes
                                        ? `<div class="notes-box d-flex justify-content-between align-items-start gap-2">
                                               <div><strong>📝 備註：</strong>${highlightText(card.notes, q)}</div>
                                               <button type="button" class="btn btn-sm btn-link p-0 text-secondary text-decoration-none flex-shrink-0 quick-note-btn" title="修改備註">✏️</button>
                                           </div>`
                                        : `<div class="notes-empty quick-note-btn">➕ 點擊新增備註...</div>`
                                    }
                                </div>
                                <div class="notes-edit-area d-none mt-1">
                                    <textarea class="form-control form-control-sm mb-1 quick-note-input" rows="2" placeholder="輸入備註內容...">${escapeHtml(card.notes || '')}</textarea>
                                    <div class="d-flex justify-content-end gap-1">
                                        <button type="button" class="btn btn-sm btn-light py-0 px-2 cancel-note-btn">取消</button>
                                        <button type="button" class="btn btn-sm btn-success py-0 px-2 save-note-btn">儲存備註</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="mt-3 pt-2 border-top d-flex justify-content-end align-items-center">
                            <div class="d-flex gap-1 flex-shrink-0">
                                <button type="button" class="btn btn-sm btn-outline-primary py-0 px-2 edit-card-btn">編輯全部</button>
                                <button type="button" class="btn btn-sm btn-outline-danger py-0 px-2 delete-card-btn">刪除</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const mergeCheck = col.querySelector('.card-merge-checkbox');
            mergeCheck.addEventListener('change', () => {
                toggleMergeCardSelect(card.id);
            });

            const impToggleBtn = col.querySelector('.toggle-important-btn');
            impToggleBtn.addEventListener('click', () => {
                toggleCardImportant(card);
            });

            const displayArea = col.querySelector('.notes-display-area');
            const editArea = col.querySelector('.notes-edit-area');
            const noteInput = col.querySelector('.quick-note-input');

            col.querySelector('.quick-note-btn').addEventListener('click', () => {
                displayArea.classList.add('d-none');
                editArea.classList.remove('d-none');
                noteInput.focus();
            });

            col.querySelector('.cancel-note-btn').addEventListener('click', () => {
                noteInput.value = card.notes || '';
                editArea.classList.add('d-none');
                displayArea.classList.remove('d-none');
            });

            col.querySelector('.save-note-btn').addEventListener('click', async () => {
                const newNotes = noteInput.value.trim();
                await quickUpdateNotes(card.id, newNotes);
            });

            col.querySelector('.edit-card-btn').addEventListener('click', () => startEditCard(card));
            col.querySelector('.delete-card-btn').addEventListener('click', () => deleteCard(card.id, card.name));
            cardList.appendChild(col);
        });

        updateMergeCardSelectionUI();
    }

    async function toggleCardImportant(card) {
        const nextImportant = !Boolean(card.important);
        try {
            const res = await fetch('/api/cards/important', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: card.id,
                    important: nextImportant
                })
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
                showAlert(data.error || '更新重要標記失敗', 'danger');
                return;
            }
            cards = data.cards || [];
            renderCards();
            const personLabel = escapeHtml(card.name || card.company || '名片');
            if (nextImportant) {
                if (data.contacts_synced) {
                    showAlert(`⭐ 已將「<strong>${personLabel}</strong>」標定為<strong>重要名片</strong>，並已自動加入 Mac 電腦的「聯絡人」資訊！`, 'success');
                } else {
                    showAlert(`⭐ 已將「<strong>${personLabel}</strong>」標定為重要名片（聯絡人同步提示：${escapeHtml(data.contacts_info || '請確認聯絡人權限')}）。`, 'warning');
                }
            } else {
                showAlert(`ℹ️ 已取消「<strong>${personLabel}</strong>」的重要標記，並已從電腦「聯絡人」移除。`, 'secondary');
            }
        } catch (err) {
            showAlert('切換重要標記時發生錯誤：' + err.message, 'danger');
        }
    }

    async function quickUpdateNotes(cardId, newNotes) {
        try {
            const res = await fetch(`/api/cards/${encodeURIComponent(cardId)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: newNotes })
            });
            const data = await res.json();
            if (res.ok) {
                cards = data.cards || [];
                renderCards();
                showAlert('📝 備註已儲存！', 'success');
            }
        } catch (err) {
            showAlert('儲存備註失敗：' + err.message, 'danger');
        }
    }

    async function fetchImgFiles() {
        try {
            const res = await fetch('/api/img-files');
            const data = await res.json();
            pendingFiles = data.pending || [];
            doneFiles = data.done || [];
            renderPendingImages();
        } catch (err) {
            showAlert('無法讀取 img 目錄，請確認 CardHelper 伺服器是否正在執行。', 'danger');
        }
    }

    async function fetchCards() {
        try {
            const res = await fetch('/api/cards');
            const data = await res.json();
            cards = data.cards || [];
            renderCards();
        } catch (err) {
            console.error(err);
        }
    }

    async function extractFiles(fileList) {
        if (!fileList || fileList.length === 0) return;
        extractBtn.disabled = true;
        extractBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> 正在提取名片資料 (${fileList.length} 張)...`;

        try {
            const defaultNotes = (extractDefaultNotes.value || '').trim();
            const res = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: fileList, notes: defaultNotes })
            });
            let data = await res.json();
            if (!res.ok) {
                showAlert(data.error || '提取失敗', 'danger');
                return;
            }

            let totalCreated = (data.extracted || []).length;
            let totalUpdated = (data.updated || []).length;
            let totalReplaced = (data.replaced || []).length;
            let totalSkipped = (data.skipped || []).length;
            let allRenamed = [...(data.renamed || [])];
            let allMultiCardFiles = [...(data.multi_card_files || [])];

            // Update intermediate state
            (data.moved || []).forEach(f => selectedFiles.delete(f));
            pendingFiles = data.pending || [];
            doneFiles = data.done || [];
            cards = data.cards || [];
            renderPendingImages();
            renderCards();

            // Check if any conflicts need user resolution ("更新" vs "取代")
            if (data.conflicts && data.conflicts.length > 0) {
                const resolutions = await promptConflictResolution(data.conflicts);
                const conflictFiles = Array.from(new Set(
                    data.conflicts.map(c => c.source_filename || String(c.filename || '').split('#')[0]).filter(Boolean)
                ));
                const res2 = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        files: conflictFiles,
                        notes: defaultNotes,
                        resolutions
                    })
                });
                const data2 = await res2.json();
                if (res2.ok) {
                    totalCreated += (data2.extracted || []).length;
                    totalUpdated += (data2.updated || []).length;
                    totalReplaced += (data2.replaced || []).length;
                    totalSkipped += (data2.skipped || []).length;
                    allRenamed.push(...(data2.renamed || []));
                    allMultiCardFiles.push(...(data2.multi_card_files || []));
                    (data2.moved || []).forEach(f => selectedFiles.delete(f));
                    pendingFiles = data2.pending || [];
                    doneFiles = data2.done || [];
                    cards = data2.cards || [];
                    renderPendingImages();
                    renderCards();
                }
            }

            const summaryParts = [];
            if (totalCreated > 0) summaryParts.push(`新增 <strong>${totalCreated}</strong> 張`);
            if (totalUpdated > 0) summaryParts.push(`更新合併 <strong>${totalUpdated}</strong> 張`);
            if (totalReplaced > 0) summaryParts.push(`覆蓋取代 <strong>${totalReplaced}</strong> 張`);
            if (totalSkipped > 0) summaryParts.push(`取消變更資料庫 <strong>${totalSkipped}</strong> 張`);

            const multiCardNote = allMultiCardFiles.length > 0
                ? `<div class="small mt-1">📇 單檔多張名片辨識：${allMultiCardFiles.map(m => `從 <code>${escapeHtml(m.filename)}</code> 自動辨識出 <strong>${m.count}</strong> 張名片（${(m.names || []).map(n => escapeHtml(n)).join('、')}）`).join('；')}</div>`
                : '';

            const changedNames = allRenamed
                .filter(r => r.from && r.to && r.from !== r.to)
                .map(r => `<code>${escapeHtml(r.from)}</code> ➔ <code>${escapeHtml(r.to)}</code>`);
            const renameNote = changedNames.length > 0
                ? `<div class="small mt-1">📁 已重新命名並移至 <code>done/</code>：${changedNames.join('、')}</div>`
                : '';

            if (summaryParts.length > 0) {
                showAlert(
                    `✅ 名片處理完成：${summaryParts.join('、')}！名片圖檔皆已依「公司名稱.名字」移至 <code>done/</code> 目錄。${multiCardNote}${renameNote}`,
                    'success'
                );
            } else {
                showAlert(`ℹ️ 已取消重複名片的資料變更，圖檔已依「公司名稱.名字」移至 <code>done/</code> 目錄。${multiCardNote}${renameNote}`, 'secondary');
            }
        } catch (err) {
            showAlert('提取過程發生錯誤：' + err.message, 'danger');
        } finally {
            extractBtn.innerHTML = `✨ 自動提取資料並新增至資料庫 (<span id="selectedCount">${selectedFiles.size}</span>)`;
            updateSelectionUI();
        }
    }

    async function restoreFiles(fileList) {
        try {
            const res = await fetch('/api/restore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: fileList })
            });
            const data = await res.json();
            if (res.ok) {
                pendingFiles = data.pending || [];
                doneFiles = data.done || [];
                renderPendingImages();
                showAlert(`↩️ 已將 ${data.restored.length} 張名片圖檔從 done/ 移回 img/ 目錄。`, 'info');
            }
        } catch (err) {
            showAlert('還原檔案失敗：' + err.message, 'danger');
        }
    }

    function startEditCard(card) {
        editCardIdInput.value = card.id;
        document.getElementById('name').value = card.name || '';
        document.getElementById('english_name').value = card.english_name || '';
        document.getElementById('company').value = card.company || '';
        document.getElementById('tax_id').value = card.tax_id || '';
        document.getElementById('title').value = card.title || '';
        document.getElementById('phone').value = card.phone || '';
        document.getElementById('mobile').value = card.mobile || '';
        document.getElementById('fax').value = card.fax || '';
        document.getElementById('email').value = card.email || '';
        document.getElementById('address').value = card.address || '';
        document.getElementById('website').value = card.website || '';
        document.getElementById('notes').value = card.notes || '';
        const impCheck = document.getElementById('important');
        if (impCheck) impCheck.checked = Boolean(card.important);

        formHeaderTitle.textContent = `✏️ 編輯名片：${card.name}`;
        submitCardBtn.textContent = '💾 儲存修改';
        submitCardBtn.classList.replace('btn-primary', 'btn-warning');
        cancelEditBtn.classList.remove('d-none');
        toggleManualFormSection(true);
        cardForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function resetEditForm() {
        cardForm.reset();
        const impCheck = document.getElementById('important');
        if (impCheck) impCheck.checked = false;
        editCardIdInput.value = '';
        formHeaderTitle.textContent = '✍️ 手動輸入 / 新增名片';
        submitCardBtn.textContent = '➕ 新增至名片資料庫';
        submitCardBtn.classList.replace('btn-warning', 'btn-primary');
        cancelEditBtn.classList.add('d-none');
        toggleManualFormSection(false);
    }

    async function deleteCard(id, name) {
        if (!confirm(`確定要從資料庫刪除「${name}」的名片嗎？`)) return;
        try {
            const res = await fetch(`/api/cards/${encodeURIComponent(id)}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                cards = data.cards || [];
                renderCards();
                showAlert(`🗑️ 已刪除「${escapeHtml(name)}」的名片。`, 'secondary');
            }
        } catch (err) {
            showAlert('刪除失敗：' + err.message, 'danger');
        }
    }

    // Event Listeners
    refreshImgBtn.addEventListener('click', () => {
        fetchImgFiles();
        showAlert('🔄 已重新掃描 img/ 目錄。', 'info');
    });

    selectAllBtn.addEventListener('click', () => {
        pendingFiles.forEach(f => selectedFiles.add(f.filename));
        updateSelectionUI();
    });

    deselectAllBtn.addEventListener('click', () => {
        selectedFiles.clear();
        updateSelectionUI();
    });

    extractBtn.addEventListener('click', () => {
        extractFiles(Array.from(selectedFiles));
    });

    toggleDoneBtn.addEventListener('click', () => {
        doneSection.classList.toggle('d-none');
    });

    restoreAllBtn.addEventListener('click', () => {
        const allDone = doneFiles.map(f => f.filename);
        if (allDone.length > 0) {
            restoreFiles(allDone);
        }
    });

    function togglePendingSection(forceOpen) {
        if (!pendingCardsBody) return;
        const willOpen = (typeof forceOpen === 'boolean') ? forceOpen : pendingCardsBody.classList.contains('d-none');
        if (willOpen) {
            pendingCardsBody.classList.remove('d-none');
            if (togglePendingBtn) togglePendingBtn.textContent = '收折處理名片 ▲';
        } else {
            pendingCardsBody.classList.add('d-none');
            if (togglePendingBtn) togglePendingBtn.textContent = '展開處理名片 ▼';
        }
    }

    function toggleManualFormSection(forceOpen) {
        if (!manualFormBody) return;
        const willOpen = (typeof forceOpen === 'boolean') ? forceOpen : manualFormBody.classList.contains('d-none');
        if (willOpen) {
            manualFormBody.classList.remove('d-none');
            if (toggleManualBtn) toggleManualBtn.textContent = '收折手動輸入 ▲';
        } else {
            manualFormBody.classList.add('d-none');
            if (toggleManualBtn) toggleManualBtn.textContent = '展開手動輸入 ▼';
        }
    }

    if (togglePendingBtn) {
        togglePendingBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            togglePendingSection();
        });
    }
    if (pendingSectionToggle) {
        pendingSectionToggle.addEventListener('click', () => {
            togglePendingSection();
        });
    }

    if (toggleManualBtn) {
        toggleManualBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleManualFormSection();
        });
    }
    if (manualFormToggle) {
        manualFormToggle.addEventListener('click', () => {
            toggleManualFormSection();
        });
    }

    cancelEditBtn.addEventListener('click', resetEditForm);

    cardForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const impCheck = document.getElementById('important');
        const payload = {
            name: document.getElementById('name').value,
            english_name: document.getElementById('english_name').value,
            company: document.getElementById('company').value,
            tax_id: document.getElementById('tax_id').value,
            title: document.getElementById('title').value,
            phone: document.getElementById('phone').value,
            mobile: document.getElementById('mobile').value,
            fax: document.getElementById('fax').value,
            email: document.getElementById('email').value,
            address: document.getElementById('address').value,
            website: document.getElementById('website').value,
            notes: document.getElementById('notes').value,
            important: impCheck ? impCheck.checked : false
        };

        const editId = editCardIdInput.value;
        try {
            if (editId) {
                const res = await fetch(`/api/cards/${encodeURIComponent(editId)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    cards = data.cards || [];
                    renderCards();
                    resetEditForm();
                    showAlert(payload.important ? '✅ 名片資料已更新，並已同步至電腦「聯絡人」資訊！' : '✅ 名片資料已更新！', 'success');
                }
                return;
            }

            // Adding new card - check for duplicate person first
            const res = await fetch('/api/cards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.conflict) {
                const resolutions = await promptConflictResolution([
                    {
                        filename: 'manual',
                        match_reason: data.match_reason,
                        existing_card: data.existing_card,
                        new_card: data.new_card,
                        merged_preview: data.merged_preview
                    }
                ]);
                const choice = resolutions['manual'];
                if (!choice || choice.action === 'skip') {
                    showAlert('ℹ️ 已取消新增重複人員的名片。', 'secondary');
                    return;
                }

                const res2 = await fetch('/api/cards', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ...payload,
                        mode: choice.action,
                        target_id: choice.target_id
                    })
                });
                const data2 = await res2.json();
                if (res2.ok) {
                    cards = data2.cards || [];
                    renderCards();
                    resetEditForm();
                    const finalName = (data2.card && data2.card.name) ? data2.card.name : payload.name;
                    if (choice.action === 'update') {
                        showAlert(`🔄 已更新合併「${escapeHtml(finalName)}」的名片資料！`, 'success');
                    } else if (choice.action === 'replace') {
                        showAlert(`♻️ 已完全取代「${escapeHtml(finalName)}」的名片資料！`, 'warning');
                    } else {
                        showAlert(`✅ 已額外新增「${escapeHtml(finalName)}」的名片至資料庫！`, 'success');
                    }
                }
                return;
            }

            if (res.ok && data.ok) {
                cards = data.cards || [];
                renderCards();
                resetEditForm();
                showAlert('✅ 已手動新增名片至資料庫！', 'success');
            }
        } catch (err) {
            showAlert('儲存失敗：' + err.message, 'danger');
        }
    });

    if (clearCardSelectionBtn) {
        clearCardSelectionBtn.addEventListener('click', () => {
            selectedMergeCardIds = [];
            updateMergeCardSelectionUI();
        });
    }

    if (mergeSelectedCardsBtn) {
        mergeSelectedCardsBtn.addEventListener('click', () => {
            openMergeCardsModal();
        });
    }

    if (swapMergeOrderBtn) {
        swapMergeOrderBtn.addEventListener('click', () => {
            if (selectedMergeCardIds.length === 2) {
                selectedMergeCardIds.reverse();
                updateMergeCardSelectionUI();
                openMergeCardsModal();
            }
        });
    }

    if (cancelMergeModalBtn) {
        cancelMergeModalBtn.addEventListener('click', () => {
            mergeCardsModal.classList.add('d-none');
        });
    }

    if (confirmMergeModalBtn) {
        confirmMergeModalBtn.addEventListener('click', () => {
            executeMergeSelectedCards();
        });
    }

    searchInput.addEventListener('input', renderCards);
    searchFieldSelect.addEventListener('change', renderCards);
    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchFieldSelect.value = 'all';
        activeCompanyFilter = '';
        renderCards();
    });

    exportCsvBtn.addEventListener('click', () => {
        if (cards.length === 0) {
            alert('目前資料庫中沒有名片可匯出！');
            return;
        }
        const headers = ['公司名稱', '統一編號', '姓名', '英文姓名', '部門職稱', '公司電話', '個人電話', '傳真', '電子郵件', '公司地址', '公司網址', '備註', '來源圖檔'];
        const rows = cards.map(c => [
            c.company || '',
            c.tax_id || '',
            c.name || '',
            c.english_name || '',
            c.title || '',
            c.phone || '',
            c.mobile || '',
            c.fax || '',
            c.email || '',
            c.address || '',
            c.website || '',
            c.notes || '',
            c.source_file || ''
        ]);
        const csvContent = '\uFEFF' + [headers, ...rows]
            .map(r => r.map(field => `"${String(field).replace(/"/g, '""')}"`).join(','))
            .join('\r\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `CardHelper_contacts_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    });

    window.openImageModal = (url, title) => {
        document.getElementById('modalImage').src = url;
        document.getElementById('modalImageTitle').textContent = title || '';
        document.getElementById('imageModal').classList.remove('d-none');
    };

    window.closeImageModal = () => {
        document.getElementById('imageModal').classList.add('d-none');
        document.getElementById('modalImage').src = '';
    };

    // Initial load
    fetchImgFiles();
    fetchCards();
});
