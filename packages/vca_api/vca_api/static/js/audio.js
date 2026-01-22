let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

function toggleInputMethod(method) {
    document.getElementById('mic-input').classList.toggle('hidden', method !== 'mic');
    document.getElementById('file-input').classList.toggle('hidden', method !== 'file');

    // Clear status messages
    document.getElementById('recording-status').textContent = '';
    document.getElementById('file-status').textContent = '';
    document.getElementById('form-audio-data').value = '';
}

async function toggleRecording() {
    const btn = document.getElementById('record-btn');
    const status = document.getElementById('recording-status');

    if (!isRecording) {
        try {
            // 録音開始
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
            mediaRecorder.onstop = async () => {
                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const base64 = await blobToBase64(blob);
                document.getElementById('form-audio-data').value = base64;
                document.getElementById('form-audio-format').value = 'webm';
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            btn.innerHTML = '<span class="text-2xl">⏹</span><span>録音停止</span>';
            btn.classList.remove('bg-red-500', 'hover:bg-red-600');
            btn.classList.add('bg-gray-700', 'hover:bg-gray-800');
            status.textContent = '🔴 録音中...';
        } catch (error) {
            console.error('Microphone access error:', error);
            status.textContent = '❌ マイクへのアクセスが拒否されました';
            status.classList.add('text-red-600');
        }
    } else {
        // 録音停止
        mediaRecorder.stop();
        isRecording = false;
        btn.innerHTML = '<span class="text-2xl">🎤</span><span>録音開始</span>';
        btn.classList.remove('bg-gray-700', 'hover:bg-gray-800');
        btn.classList.add('bg-red-500', 'hover:bg-red-600');
        status.textContent = '✅ 録音完了';
        status.classList.remove('text-red-600');
    }
}

async function handleFileSelect() {
    const fileInput = document.getElementById('audio-file');
    const status = document.getElementById('file-status');

    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const base64 = await blobToBase64(file);
        document.getElementById('form-audio-data').value = base64;

        // Extract file extension
        const extension = file.name.split('.').pop().toLowerCase();
        document.getElementById('form-audio-format').value = extension;

        status.textContent = `✅ ${file.name} を選択しました`;
        status.classList.remove('text-red-600');
    }
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

async function submitAction(action) {
    const speakerId = document.getElementById('speaker-id').value.trim();
    const audioData = document.getElementById('form-audio-data').value;

    // Validation
    if (!speakerId) {
        alert('Speaker IDを入力してください');
        return;
    }

    if (!audioData) {
        alert('音声を録音またはファイルを選択してください');
        return;
    }

    // フォームデータをセット
    document.getElementById('form-speaker-id').value = speakerId;
    document.getElementById('form-speaker-name').value =
        document.getElementById('speaker-name').value;

    // htmxでPOST
    const form = document.getElementById('action-form');
    form.setAttribute('hx-post', `/demo/${action}`);
    htmx.process(form);
    htmx.trigger(form, 'submit');
}
