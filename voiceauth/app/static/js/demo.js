/**
 * VoiceAuth Demo JavaScript
 * Handles WebSocket communication and audio recording
 */

// State
let enrollWs = null;
let verifyWs = null;
let mediaRecorder = null;
let audioChunks = [];
let currentMode = null; // 'enroll' or 'verify'
let enrollState = {
    prompts: [],
    currentSet: 0,
    speakerId: null
};

// WebSocket URL
const WS_BASE = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`;

// ============================================
// Tab Switching
// ============================================

function switchTab(tab) {
    const enrollTab = document.getElementById('tab-enroll');
    const verifyTab = document.getElementById('tab-verify');
    const enrollSection = document.getElementById('section-enroll');
    const verifySection = document.getElementById('section-verify');

    if (tab === 'enroll') {
        enrollTab.className = 'flex-1 py-3 px-4 text-center font-medium rounded-l-lg bg-blue-500 text-white';
        verifyTab.className = 'flex-1 py-3 px-4 text-center font-medium rounded-r-lg bg-gray-200 text-gray-700 hover:bg-gray-300';
        enrollSection.classList.remove('hidden');
        verifySection.classList.add('hidden');
    } else {
        verifyTab.className = 'flex-1 py-3 px-4 text-center font-medium rounded-r-lg bg-blue-500 text-white';
        enrollTab.className = 'flex-1 py-3 px-4 text-center font-medium rounded-l-lg bg-gray-200 text-gray-700 hover:bg-gray-300';
        verifySection.classList.remove('hidden');
        enrollSection.classList.add('hidden');
    }
}

// ============================================
// Enrollment
// ============================================

function startEnrollment() {
    const speakerId = document.getElementById('enroll-speaker-id').value.trim();
    const speakerName = document.getElementById('enroll-speaker-name').value.trim();

    if (!speakerId) {
        showError('Speaker IDを入力してください');
        return;
    }

    enrollState.speakerId = speakerId;

    // Connect WebSocket
    enrollWs = new WebSocket(`${WS_BASE}/ws/enrollment`);

    enrollWs.onopen = () => {
        // Send start message
        enrollWs.send(JSON.stringify({
            type: 'start_enrollment',
            speaker_id: speakerId,
            speaker_name: speakerName || null
        }));
    };

    enrollWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEnrollMessage(data);
    };

    enrollWs.onerror = (error) => {
        console.error('WebSocket error:', error);
        showError('接続エラーが発生しました');
    };

    enrollWs.onclose = () => {
        console.log('Enrollment WebSocket closed');
    };
}

function handleEnrollMessage(data) {
    console.log('Enrollment message:', data);

    switch (data.type) {
        case 'prompts':
            enrollState.prompts = data.prompts;
            enrollState.currentSet = data.current_set;
            showEnrollRecording();
            updateEnrollPrompt();
            break;

        case 'asr_result':
            if (data.success) {
                enrollState.currentSet++;
                updateEnrollProgress();
                if (data.remaining_sets === 0) {
                    showEnrollPin();
                } else {
                    updateEnrollPrompt();
                    showFeedback('enroll', data.message, 'success');
                }
            } else {
                showFeedback('enroll', data.message, 'error');
            }
            break;

        case 'enrollment_complete':
            showEnrollComplete();
            break;

        case 'error':
            showError(data.message);
            break;
    }
}

function showEnrollRecording() {
    document.getElementById('enroll-form').classList.add('hidden');
    document.getElementById('enroll-recording').classList.remove('hidden');
}

function updateEnrollPrompt() {
    const prompt = enrollState.prompts[enrollState.currentSet];
    document.getElementById('enroll-prompt').textContent = prompt.split('').join(' ');
    document.getElementById('enroll-progress-text').textContent =
        `${enrollState.currentSet} / ${enrollState.prompts.length}`;
}

function updateEnrollProgress() {
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById(`progress-${i}`);
        if (i <= enrollState.currentSet) {
            el.className = 'h-2 flex-1 rounded bg-green-500';
        } else {
            el.className = 'h-2 flex-1 rounded bg-gray-200';
        }
    }
    document.getElementById('enroll-progress-text').textContent =
        `${enrollState.currentSet} / ${enrollState.prompts.length}`;
}

function showEnrollPin() {
    document.getElementById('enroll-recording').classList.add('hidden');
    document.getElementById('enroll-pin').classList.remove('hidden');
}

function submitPin() {
    const pin = document.getElementById('enroll-pin-input').value;
    const pinConfirm = document.getElementById('enroll-pin-confirm').value;

    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
        showError('PINは4桁の数字で入力してください');
        return;
    }

    if (pin !== pinConfirm) {
        showError('PINが一致しません');
        return;
    }

    enrollWs.send(JSON.stringify({
        type: 'register_pin',
        pin: pin
    }));
}

function showEnrollComplete() {
    document.getElementById('enroll-pin').classList.add('hidden');
    document.getElementById('enroll-complete').classList.remove('hidden');
    if (enrollWs) {
        enrollWs.close();
        enrollWs = null;
    }
}

function resetEnrollment() {
    enrollState = { prompts: [], currentSet: 0, speakerId: null };
    document.getElementById('enroll-form').classList.remove('hidden');
    document.getElementById('enroll-recording').classList.add('hidden');
    document.getElementById('enroll-pin').classList.add('hidden');
    document.getElementById('enroll-complete').classList.add('hidden');
    document.getElementById('enroll-speaker-id').value = '';
    document.getElementById('enroll-speaker-name').value = '';
    document.getElementById('enroll-pin-input').value = '';
    document.getElementById('enroll-pin-confirm').value = '';
    for (let i = 1; i <= 5; i++) {
        document.getElementById(`progress-${i}`).className = 'h-2 flex-1 rounded bg-gray-200';
    }
}

// ============================================
// Verification
// ============================================

function startVerification() {
    const speakerId = document.getElementById('verify-speaker-id').value.trim();

    if (!speakerId) {
        showError('Speaker IDを入力してください');
        return;
    }

    // Connect WebSocket
    verifyWs = new WebSocket(`${WS_BASE}/ws/verify`);

    verifyWs.onopen = () => {
        verifyWs.send(JSON.stringify({
            type: 'start_verify',
            speaker_id: speakerId
        }));
    };

    verifyWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleVerifyMessage(data);
    };

    verifyWs.onerror = (error) => {
        console.error('WebSocket error:', error);
        showError('接続エラーが発生しました');
    };

    verifyWs.onclose = () => {
        console.log('Verify WebSocket closed');
    };
}

function handleVerifyMessage(data) {
    console.log('Verify message:', data);

    switch (data.type) {
        case 'prompt':
            showVerifyRecording(data.prompt);
            break;

        case 'verify_result':
            showVerifyResult(data);
            break;

        case 'error':
            showError(data.message);
            break;
    }
}

function showVerifyRecording(prompt) {
    document.getElementById('verify-form').classList.add('hidden');
    document.getElementById('verify-recording').classList.remove('hidden');
    document.getElementById('verify-prompt').textContent = prompt.split('').join(' ');
}

function showVerifyResult(data) {
    document.getElementById('verify-recording').classList.add('hidden');
    document.getElementById('verify-result').classList.remove('hidden');

    const content = document.getElementById('verify-result-content');

    let html = '';

    // Authentication status
    if (data.authenticated) {
        html += `
            <div class="text-center py-4 bg-green-50 rounded-lg">
                <div class="text-green-500 text-4xl mb-2">&#10003;</div>
                <p class="text-xl font-semibold text-green-600">認証成功</p>
                ${data.auth_method ? `<p class="text-sm text-gray-500">認証方法: ${data.auth_method}</p>` : ''}
            </div>
        `;
    } else {
        html += `
            <div class="text-center py-4 bg-red-50 rounded-lg">
                <div class="text-red-500 text-4xl mb-2">&#10007;</div>
                <p class="text-xl font-semibold text-red-600">認証失敗</p>
                <p class="text-sm text-gray-500">${data.message}</p>
            </div>
        `;
    }

    // Details
    html += '<div class="mt-4 space-y-2 text-sm">';

    html += `<div class="flex justify-between">
        <span class="text-gray-500">ASR結果:</span>
        <span class="${data.asr_matched ? 'text-green-600' : 'text-red-600'}">${data.asr_result || '-'} ${data.asr_matched ? '&#10003;' : '&#10007;'}</span>
    </div>`;

    if (data.voice_similarity !== null && data.voice_similarity !== undefined) {
        const similarity = (data.voice_similarity * 100).toFixed(1);
        const isPass = data.voice_similarity >= 0.75;
        html += `<div class="flex justify-between">
            <span class="text-gray-500">声紋スコア:</span>
            <span class="${isPass ? 'text-green-600' : 'text-red-600'}">${similarity}% ${isPass ? '&#10003;' : '&#10007;'}</span>
        </div>`;
    }

    if (data.digit_scores) {
        html += '<div class="mt-2 pt-2 border-t">';
        html += '<p class="text-gray-500 mb-1">数字別スコア:</p>';
        html += '<div class="flex flex-wrap gap-2">';
        for (const [digit, score] of Object.entries(data.digit_scores)) {
            const pct = (score * 100).toFixed(0);
            const color = score >= 0.75 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
            html += `<span class="px-2 py-1 rounded ${color}">${digit}: ${pct}%</span>`;
        }
        html += '</div></div>';
    }

    html += '</div>';
    content.innerHTML = html;

    // Show PIN fallback if available
    if (data.can_fallback_to_pin && !data.authenticated) {
        document.getElementById('verify-pin-fallback').classList.remove('hidden');
    } else {
        document.getElementById('verify-pin-fallback').classList.add('hidden');
    }
}

function submitVerifyPin() {
    const pin = document.getElementById('verify-pin-input').value;

    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
        showError('PINは4桁の数字で入力してください');
        return;
    }

    verifyWs.send(JSON.stringify({
        type: 'verify_pin',
        pin: pin
    }));
}

function resetVerification() {
    document.getElementById('verify-form').classList.remove('hidden');
    document.getElementById('verify-recording').classList.add('hidden');
    document.getElementById('verify-result').classList.add('hidden');
    document.getElementById('verify-pin-fallback').classList.add('hidden');
    document.getElementById('verify-pin-input').value = '';
    if (verifyWs) {
        verifyWs.close();
        verifyWs = null;
    }
}

// ============================================
// Audio Recording
// ============================================

async function startRecording(mode) {
    currentMode = mode;
    audioChunks = [];

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            sendAudio(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        updateRecordingUI(mode, true);

    } catch (error) {
        console.error('Error accessing microphone:', error);
        showError('マイクにアクセスできません。マイクの許可を確認してください。');
    }
}

function stopRecording(mode) {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        updateRecordingUI(mode, false);
    }
}

function updateRecordingUI(mode, isRecording) {
    const btn = document.getElementById(`${mode}-record-btn`);
    const text = document.getElementById(`${mode}-record-text`);

    if (isRecording) {
        btn.classList.add('recording', 'bg-red-700');
        btn.classList.remove('bg-red-500');
        text.innerHTML = '録音中...';
    } else {
        btn.classList.remove('recording', 'bg-red-700');
        btn.classList.add('bg-red-500');
        text.innerHTML = '押しながら<br>話す';
    }
}

function sendAudio(blob) {
    const ws = currentMode === 'enroll' ? enrollWs : verifyWs;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(blob);
        showFeedback(currentMode, '処理中...', 'info');
    }
}

// ============================================
// File Upload (Verify)
// ============================================

function handleVerifyFileUpload(input) {
    const file = input.files[0];
    if (!file) return;

    if (!verifyWs || verifyWs.readyState !== WebSocket.OPEN) {
        showError('WebSocket が接続されていません。認証を開始してください。');
        input.value = '';
        return;
    }

    currentMode = 'verify';
    showFeedback('verify', `${file.name} を送信中...`, 'info');

    file.arrayBuffer().then(buffer => {
        verifyWs.send(new Blob([buffer]));
        showFeedback('verify', '処理中...', 'info');
    }).catch(error => {
        console.error('File read error:', error);
        showError('ファイルの読み込みに失敗しました');
    });

    input.value = '';
}

// ============================================
// Utilities
// ============================================

function showFeedback(mode, message, type) {
    const feedback = document.getElementById(`${mode}-feedback`);
    const colors = {
        success: 'bg-green-50 text-green-700',
        error: 'bg-red-50 text-red-700',
        info: 'bg-blue-50 text-blue-700'
    };
    feedback.className = `text-center p-4 rounded-lg ${colors[type] || colors.info}`;
    feedback.innerHTML = `<p>${message}</p>`;
}

function showError(message) {
    const toast = document.getElementById('error-toast');
    const msgEl = document.getElementById('error-message');
    msgEl.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 5000);
}

// Prevent context menu on long press (mobile)
document.addEventListener('contextmenu', (e) => {
    if (e.target.id && e.target.id.includes('record-btn')) {
        e.preventDefault();
    }
});
