// Minimal JS setup
console.log('App.js loaded v0.6.2');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');

    // Tab Switching Logic
    const tabs = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.tab-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            sections.forEach(s => s.classList.add('hidden'));
            
            const targetId = tab.dataset.target;
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.remove('hidden');
            }
        });
    });

    // --- Modal Logic ---
    
    function openModal(modalId) {
        console.log('Opening modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            // Support legacy 'active' class used in settings_form.html
            modal.classList.add('active');
        } else {
            console.error('Modal element not found:', modalId);
        }
    }

    function closeModal(modalId) {
        console.log('Closing modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            modal.classList.remove('active');
        }
    }

    // Help Modal
    const helpBtn = document.getElementById('help-btn');
    if (helpBtn) {
        helpBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('help-modal');
        });
    }

    const closeHelpBtn = document.querySelector('#help-modal .close-modal-btn');
    if (closeHelpBtn) {
        closeHelpBtn.addEventListener('click', () => closeModal('help-modal'));
    }

    // Upload Modal
    const uploadBtn = document.getElementById('upload-btn');
    const uploadForm = document.getElementById('upload-form');
    const uploadSubmitInput = document.getElementById('upload-submit-files');
    const uploadPickFilesInput = document.getElementById('upload-pick-files');
    const uploadPickFolderInput = document.getElementById('upload-pick-folder');
    const pickUploadFilesBtn = document.getElementById('pick-upload-files-btn');
    const pickUploadFolderBtn = document.getElementById('pick-upload-folder-btn');
    const clearUploadFilesBtn = document.getElementById('clear-upload-files-btn');
    const uploadSelectionSummary = document.getElementById('upload-selection-summary');
    const uploadSelectionList = document.getElementById('upload-selection-list');
    const uploadStore = {
        dataTransfer: new DataTransfer(),
        keys: new Set(),
    };

    const updateUploadSelectionView = () => {
        if (!uploadSelectionSummary || !uploadSelectionList || !uploadSubmitInput) {
            return;
        }

        const files = Array.from(uploadSubmitInput.files || []);
        if (files.length === 0) {
            uploadSelectionSummary.textContent = 'まだ CSV は選択されていません';
            uploadSelectionList.innerHTML = '';
            return;
        }

        uploadSelectionSummary.textContent = `${files.length} 件の CSV を選択中です`;
        uploadSelectionList.innerHTML = files
            .map((file) => {
                const relPath = file.webkitRelativePath || file.name;
                return `<li>${relPath}</li>`;
            })
            .join('');
    };

    const syncUploadFiles = () => {
        if (!uploadSubmitInput) {
            return;
        }
        uploadSubmitInput.files = uploadStore.dataTransfer.files;
        updateUploadSelectionView();
    };

    const addUploadFiles = (fileList) => {
        Array.from(fileList || []).forEach((file) => {
            const fileKey = [
                file.name,
                file.size,
                file.lastModified,
                file.webkitRelativePath || '',
            ].join('::');
            if (uploadStore.keys.has(fileKey)) {
                return;
            }
            uploadStore.keys.add(fileKey);
            uploadStore.dataTransfer.items.add(file);
        });
        syncUploadFiles();
    };

    const clearUploadFiles = () => {
        uploadStore.dataTransfer = new DataTransfer();
        uploadStore.keys = new Set();
        if (uploadPickFilesInput) {
            uploadPickFilesInput.value = '';
        }
        if (uploadPickFolderInput) {
            uploadPickFolderInput.value = '';
        }
        syncUploadFiles();
    };

    if (uploadBtn) {
        uploadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('upload-modal');
        });
    }

    if (pickUploadFilesBtn && uploadPickFilesInput) {
        pickUploadFilesBtn.addEventListener('click', () => uploadPickFilesInput.click());
        uploadPickFilesInput.addEventListener('change', (e) => addUploadFiles(e.target.files));
    }

    if (pickUploadFolderBtn && uploadPickFolderInput) {
        pickUploadFolderBtn.addEventListener('click', () => uploadPickFolderInput.click());
        uploadPickFolderInput.addEventListener('change', (e) => addUploadFiles(e.target.files));
    }

    if (clearUploadFilesBtn) {
        clearUploadFilesBtn.addEventListener('click', clearUploadFiles);
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            if (!uploadSubmitInput || !uploadSubmitInput.files || uploadSubmitInput.files.length === 0) {
                e.preventDefault();
                window.alert('CSVファイルまたはフォルダを選択してください');
            }
        });
        uploadForm.addEventListener('htmx:afterRequest', clearUploadFiles);
    }

    updateUploadSelectionView();

    // Close buttons for Upload Modal
    const closeUploadBtns = [
        document.getElementById('close-upload-modal-btn'),
        document.getElementById('x-close-upload-modal-btn')
    ];
    closeUploadBtns.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', () => closeModal('upload-modal'));
        }
    });

    // Close any modal when clicking overlay
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('show');
                overlay.classList.remove('active');
            }
        });
    });
});

// Variant tab switching (event delegation for HTMX swaps)
document.addEventListener('click', (event) => {
    const tab = event.target.closest('.variant-tab');
    if (!tab) return;

    const wrapper = tab.closest('.result-wrapper');
    if (!wrapper) return;

    const targetId = tab.getAttribute('data-variant-tab');
    if (targetId === null) return;

    const tabs = wrapper.querySelectorAll('.variant-tab');
    const panels = wrapper.querySelectorAll('.variant-panel');

    tabs.forEach((item) => item.classList.remove('active'));
    tab.classList.add('active');

    panels.forEach((panel) => {
        const panelId = panel.getAttribute('data-variant-panel');
        if (panelId === targetId) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
});

// NG table filtering (event delegation for HTMX swaps)
document.addEventListener('click', (event) => {
    const button = event.target.closest('.ng-filter-btn');
    if (!button) return;

    const tableId = button.getAttribute('data-ng-table');
    const filterMode = button.getAttribute('data-ng-filter');
    if (!tableId || !filterMode) return;

    const table = document.getElementById(tableId);
    if (!table) return;

    const group = button.closest('[data-ng-filter-group]');
    if (group) {
        group.querySelectorAll('.ng-filter-btn').forEach((item) => {
            item.classList.remove('active');
        });
    }
    button.classList.add('active');

    const rows = table.querySelectorAll('tbody tr[data-ng-row]');
    let visibleCount = 0;
    rows.forEach((row) => {
        const hasNg = row.getAttribute('data-ng-row') === 'true';
        const shouldShow = filterMode === 'all' || hasNg;
        row.classList.toggle('hidden', !shouldShow);
        if (shouldShow) {
            visibleCount += 1;
        }
    });

    const emptyRow = table.querySelector('tbody tr.ng-filter-empty');
    if (emptyRow) {
        const showEmpty = filterMode === 'ng' && visibleCount === 0;
        emptyRow.classList.toggle('hidden', !showEmpty);
    }
});

// Keep NG sub-tab after HTMX refresh
document.body.addEventListener('htmx:afterSwap', (event) => {
    const target = event.detail && event.detail.target;
    if (!target || target.id !== 'ng-dates-container') return;
    if (typeof window.restoreNgTab === 'function') {
        window.restoreNgTab();
    }
});

// Member modal management
let currentMemberName = "";

function openMemberModal(name, minDaysDay, minDaysNight) {
    currentMemberName = name;
    const modal = document.getElementById('member-modal');
    if (modal) {
        document.getElementById("modal-member-name").textContent = name;
        document.getElementById("modal-min-days-day").value = minDaysDay || "";
        document.getElementById("modal-min-days-night").value = minDaysNight || "";
        modal.classList.add('active');
        modal.classList.add('show');
    }
}

function closeMemberModal() {
    const modal = document.getElementById('member-modal');
    if (modal) {
        modal.classList.remove('active');
        modal.classList.remove('show');
    }
    currentMemberName = "";
}

function saveMemberAttributes() {
    if (!currentMemberName) {
        console.error('No member selected');
        return;
    }

    const data = {
        name: currentMemberName,
        min_days_day: document.getElementById("modal-min-days-day").value,
        min_days_night: document.getElementById("modal-min-days-night").value,
    };

    fetch("/settings/member/update", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
        .then((response) => response.json())
        .then((result) => {
            if (result.success) {
                closeMemberModal();
                window.location.reload();
            } else {
                alert("エラー: " + result.error);
            }
        })
        .catch((error) => {
            console.error('Save error:', error);
            alert("通信エラー: " + error);
        });
}

/**
 * メンバーを追加する関数
 * @param {HTMLInputElement} inputElement - 名前入力欄
 * @param {string} groupName - グループ名（例: 'day_index_1_2'）
 */
function addMember(inputElement, groupName) {
    const name = inputElement.value.trim();

    if (!name) {
        alert('名前を入力してください');
        return;
    }

    // 対象のリストコンテナを取得
    const listContainer = document.querySelector(`.sortable-list[data-input-name="${groupName}"]`);

    if (!listContainer) {
        console.error(`List container not found for group: ${groupName}`);
        return;
    }

    // グループに応じた移動先と勤務種別を判定
    const moveConfig = getMoveConfig(groupName);

    // 新しいメンバーカードを作成
    const memberCard = document.createElement('div');
    memberCard.className = 'member-card';
    memberCard.innerHTML = `
        <input type="hidden" name="${groupName}[]" value="${name}" class="member-id" />
        <label style="display: flex; align-items: center; width: 100%; margin: 0;">
            <input type="checkbox" name="active_${name}_${moveConfig.shiftType}" checked />
            <span style="flex: 1; font-weight: 500;">${name}</span>
        </label>
        ${moveConfig.moveButton}
        <button type="button" class="btn-edit" onclick="openMemberModal('${name}', '', '')">
            ✎
        </button>
        <button type="button" class="btn-remove" onclick="this.closest('.member-card').remove()" title="削除">
            ×
        </button>
    `;

    // リストに追加
    listContainer.appendChild(memberCard);

    // 入力欄をクリア
    inputElement.value = '';
    inputElement.focus();
}

/**
 * グループ名から移動設定を取得
 * @param {string} groupName - グループ名
 * @returns {Object} - 移動設定
 */
function getMoveConfig(groupName) {
    const configs = {
        'day_index_1_2': {
            targetGroup: 'day_index_3',
            arrow: '→',
            shiftType: 'day'
        },
        'day_index_3': {
            targetGroup: 'day_index_1_2',
            arrow: '←',
            shiftType: 'day'
        },
        'night_index_1': {
            targetGroup: 'night_index_2',
            arrow: '→',
            shiftType: 'night'
        },
        'night_index_2': {
            targetGroup: 'night_index_1',
            arrow: '←',
            shiftType: 'night'
        }
    };

    const config = configs[groupName];
    if (config) {
        return {
            shiftType: config.shiftType,
            moveButton: `<button type="button" class="btn-move" onclick="moveMemberToGroup(this, '${config.targetGroup}')" title="${config.arrow === '→' ? '右' : '左'}のグループへ移動">${config.arrow}</button>`
        };
    }

    // デフォルト（移動ボタンなし）
    return {
        shiftType: 'day',
        moveButton: ''
    };
}

/**
 * メンバーを別のグループに移動
 * @param {HTMLElement} buttonElement - クリックされたボタン要素
 * @param {string} targetGroupName - 移動先グループ名
 */
function moveMemberToGroup(buttonElement, targetGroupName) {
    const memberCard = buttonElement.closest('.member-card');
    if (!memberCard) {
        console.error('Member card not found');
        return;
    }

    // メンバー情報を取得
    const memberNameSpan = memberCard.querySelector('label span');
    const memberName = memberNameSpan ? memberNameSpan.textContent.trim() : '';
    const isActive = memberCard.querySelector('input[type="checkbox"]').checked;

    if (!memberName) {
        console.error('Member name not found');
        return;
    }

    // 移動先のリストコンテナを取得
    const targetContainer = document.querySelector(`.sortable-list[data-input-name="${targetGroupName}"]`);
    if (!targetContainer) {
        console.error(`Target container not found: ${targetGroupName}`);
        return;
    }

    // 現在のカードを削除
    memberCard.remove();

    // 移動先グループの設定を取得
    const moveConfig = getMoveConfig(targetGroupName);

    // 新しいメンバーカードを作成
    const newMemberCard = document.createElement('div');
    newMemberCard.className = 'member-card';
    newMemberCard.innerHTML = `
        <input type="hidden" name="${targetGroupName}[]" value="${memberName}" class="member-id" />
        <label style="display: flex; align-items: center; width: 100%; margin: 0;">
            <input type="checkbox" name="active_${memberName}_${moveConfig.shiftType}" ${isActive ? 'checked' : ''} />
            <span style="flex: 1; font-weight: 500;">${memberName}</span>
        </label>
        ${moveConfig.moveButton}
        <button type="button" class="btn-edit" onclick="openMemberModal('${memberName}', '', '')" title="編集">
            ✎
        </button>
        <button type="button" class="btn-remove" onclick="this.closest('.member-card').remove()" title="削除">
            ×
        </button>
    `;

    // 移動先リストに追加
    targetContainer.appendChild(newMemberCard);
}

/**
 * 作成結果パネルから日勤・夜勤の担当を JSON にまとめる（保存・印刷用）
 */
function buildScheduleJsonFromPanel(panel) {
    if (!panel) return '{}';
    const variantIdx = panel.getAttribute('data-variant-panel');
    const day = {};
    const night = {};
    const dayTable = panel.querySelector('#day-table-' + variantIdx);
    const nightTable = panel.querySelector('#night-table-' + variantIdx);

    function collectRows(table, shiftType, bucket) {
        if (!table) return;
        table.querySelectorAll('tbody tr[data-date-key]').forEach(function (tr) {
            const dk = tr.getAttribute('data-date-key');
            if (!dk) return;
            const row = {};
            tr.querySelectorAll(
                'select.schedule-cell-select[data-shift-type="' + shiftType + '"]'
            ).forEach(function (sel) {
                const slot = parseInt(sel.getAttribute('data-slot'), 10);
                const v = (sel.value || '').trim();
                if (v) row[slot] = v;
            });
            bucket[dk] = row;
        });
    }

    collectRows(dayTable, 'day', day);
    collectRows(nightTable, 'night', night);
    return JSON.stringify({ day: day, night: night });
}

function syncScheduleJsonIntoForm(form) {
    const panel = form.closest('.variant-panel');
    const field = form.querySelector('.schedule-json-field');
    if (field && panel) {
        field.value = buildScheduleJsonFromPanel(panel);
    }
}

document.body.addEventListener('htmx:beforeRequest', function (evt) {
    const elt = evt.detail && evt.detail.elt;
    if (!elt || elt.tagName !== 'FORM') return;
    if (!elt.classList.contains('schedule-save-form')) return;
    syncScheduleJsonIntoForm(elt);
});

function closePrintCalendarModal() {
    var modal = document.getElementById('print-calendar-modal');
    var iframe = document.getElementById('print-calendar-iframe');
    if (iframe) {
        if (iframe._blobUrl) {
            try {
                URL.revokeObjectURL(iframe._blobUrl);
            } catch (e) {}
            iframe._blobUrl = null;
        }
        iframe.src = 'about:blank';
    }
    if (modal) {
        modal.classList.remove('show', 'active');
        modal.setAttribute('aria-hidden', 'true');
    }
}

/** 印刷ビュー HTML を同一ページのモーダル iframe に表示（新規タブ不要・ポップアップブロック無関係） */
function openPrintCalendarModal(html) {
    var modal = document.getElementById('print-calendar-modal');
    var iframe = document.getElementById('print-calendar-iframe');
    if (!modal || !iframe) {
        alert('印刷ビューを表示できません。ページを再読み込みしてください。');
        return;
    }
    if (iframe._blobUrl) {
        try {
            URL.revokeObjectURL(iframe._blobUrl);
        } catch (e) {}
        iframe._blobUrl = null;
    }
    var blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    iframe._blobUrl = url;
    iframe.src = url;
    modal.classList.add('show', 'active');
    modal.setAttribute('aria-hidden', 'false');
}

document.body.addEventListener('click', function (evt) {
    const printBtn = evt.target.closest('.btn-open-print-calendar');
    if (printBtn) {
        evt.preventDefault();
        const panel = printBtn.closest('.variant-panel');
        const scheduleJson = buildScheduleJsonFromPanel(panel);
        const fd = new FormData();
        fd.append('schedule_json', scheduleJson);
        fd.append('start_date', printBtn.getAttribute('data-start-date') || '');
        fd.append('end_date', printBtn.getAttribute('data-end-date') || '');
        fd.append('variant_index', printBtn.getAttribute('data-variant-index') || '0');
        fetch('/print/calendar', { method: 'POST', body: fd })
            .then(function (res) {
                return res.text().then(function (text) {
                    return { ok: res.ok, text: text };
                });
            })
            .then(function (result) {
                openPrintCalendarModal(result.text);
            })
            .catch(function () {
                openPrintCalendarModal(
                    '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>エラー</title></head><body style="font-family:sans-serif;padding:1rem">通信エラーで印刷ビューを取得できませんでした。</body></html>'
                );
            });
        return;
    }
});

(function initPrintCalendarModalUi() {
    var modal = document.getElementById('print-calendar-modal');
    var closeBtn = document.getElementById('print-calendar-close-btn');
    var printBtn = document.getElementById('print-calendar-print-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', function () {
            closePrintCalendarModal();
        });
    }
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                closePrintCalendarModal();
            }
        });
    }
    if (printBtn) {
        printBtn.addEventListener('click', function () {
            var iframe = document.getElementById('print-calendar-iframe');
            if (iframe && iframe.contentWindow) {
                try {
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                } catch (e) {}
            }
        });
    }
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        var m = document.getElementById('print-calendar-modal');
        if (m && (m.classList.contains('show') || m.classList.contains('active'))) {
            closePrintCalendarModal();
        }
    });
})();

document.body.addEventListener('click', function (evt) {
    const btn = evt.target.closest('.btn-swap-row');
    if (!btn) return;
    const tr = btn.closest('tr[data-date-key]');
    const table = tr && tr.closest('table');
    if (!tr || !table) return;
    const rows = Array.prototype.slice.call(
        table.querySelectorAll('tbody tr[data-date-key]')
    );
    const idx = rows.indexOf(tr);
    const dir = btn.getAttribute('data-swap');
    const j = dir === 'up' ? idx - 1 : idx + 1;
    if (j < 0 || j >= rows.length) return;
    const trOther = rows[j];
    const selectsA = tr.querySelectorAll('select.schedule-cell-select');
    const selectsB = trOther.querySelectorAll('select.schedule-cell-select');
    if (selectsA.length !== selectsB.length || selectsA.length === 0) return;
    for (let i = 0; i < selectsA.length; i++) {
        const tmp = selectsA[i].value;
        selectsA[i].value = selectsB[i].value;
        selectsB[i].value = tmp;
    }
});

// --- 履歴CSV テーブル編集（ページ単位保存）---
function syncHistoryNightIndexOptions(tr) {
    const cat = tr.querySelector('.history-select-cat');
    const idx = tr.querySelector('.history-select-idx');
    if (!cat || !idx) return;
    const opt3 = idx.querySelector('option[value="3"]');
    if (!opt3) return;
    if (cat.value === 'Night') {
        opt3.disabled = true;
        if (idx.value === '3') {
            idx.value = '1';
        }
    } else {
        opt3.disabled = false;
    }
}

function initHistoryEditForm(root) {
    const form = (root && root.querySelector('#history-edit-form')) || document.getElementById('history-edit-form');
    if (!form) return;
    form.querySelectorAll('.history-edit-row').forEach(function (tr) {
        syncHistoryNightIndexOptions(tr);
    });
}

document.body.addEventListener('change', function (evt) {
    const cat = evt.target.closest('.history-select-cat');
    if (!cat) return;
    const tr = cat.closest('.history-edit-row');
    if (tr) syncHistoryNightIndexOptions(tr);
});

document.body.addEventListener('htmx:afterSwap', function (evt) {
    const t = evt.detail && evt.detail.target;
    if (t && t.id === 'history-container') {
        initHistoryEditForm(t);
    }
});

document.addEventListener('DOMContentLoaded', function () {
    initHistoryEditForm(document);
});

document.body.addEventListener('submit', function (evt) {
    const form = evt.target;
    if (!form.id || form.id !== 'history-edit-form') return;
    evt.preventDefault();
    const msgEl = document.getElementById('history-save-message');
    const page = parseInt(form.querySelector('[name="page"]').value, 10) || 1;
    const pageSize = parseInt(form.querySelector('[name="page_size"]').value, 10) || 50;
    const rows = [];
    form.querySelectorAll('.history-edit-row').forEach(function (tr) {
        const dateInput = tr.querySelector('.history-input-date');
        const cat = tr.querySelector('.history-select-cat');
        const idx = tr.querySelector('.history-select-idx');
        const name = tr.querySelector('.history-input-name');
        rows.push({
            date: dateInput ? dateInput.value : '',
            shift_category: cat ? cat.value : '',
            shift_index: idx ? parseInt(idx.value, 10) : 1,
            person_name: name ? name.value.trim() : '',
        });
    });

    if (msgEl) {
        msgEl.textContent = '保存中…';
        msgEl.className = 'history-save-message';
    }

    fetch('/history/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: page, page_size: pageSize, rows: rows }),
    })
        .then(function (r) {
            return r.json().then(function (data) {
                return { ok: r.ok, data: data };
            });
        })
        .then(function (result) {
            if (!msgEl) return;
            if (result.ok && result.data.success) {
                msgEl.textContent = result.data.message || '保存しました';
                msgEl.className = 'history-save-message success';
            } else {
                msgEl.textContent = (result.data && result.data.message) || '保存に失敗しました';
                msgEl.className = 'history-save-message error';
            }
        })
        .catch(function () {
            if (msgEl) {
                msgEl.textContent = '通信エラーで保存できませんでした';
                msgEl.className = 'history-save-message error';
            }
        });
});
