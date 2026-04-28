    (function() {
        const WIN = window.parent;
        const DOC = WIN.document;
        const BACKEND = "%%BACKEND%%";

        // ── Persistent state — initialise once ─────────────────────────────
        if (typeof WIN._rmInited === 'undefined') {
            WIN._rmInited     = true;
            WIN._rmRecording  = false;
            WIN._rmProcessing = false;
            WIN._rmVoiceReady = false;
            WIN._rmAudioCtx   = null;
            WIN._rmRecorder   = null;
            WIN._rmStream     = null;
            WIN._rmAnalyser   = null;
            WIN._rmRecordStart = 0;
            WIN._rmSilStart    = null;
            WIN._rmAborted     = false;
        }

        const firstRun = !DOC.getElementById('rm-mic-fab');

        // ── One-time DOM injection ─────────────────────────────────────────
        if (firstRun) {
            const style = DOC.createElement('style');
            style.textContent = `
                .rm-fab {
                    position: fixed;
                    width: 44px; height: 44px;
                    border-radius: 50%;
                    border: 1.5px solid #E2E8F0;
                    background: #FFFFFF;
                    font-size: 19px;
                    cursor: pointer;
                    z-index: 9999;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.10);
                    display: flex; align-items: center; justify-content: center;
                    padding: 0; line-height: 1;
                    transition: background 0.2s, border-color 0.2s, opacity 0.15s;
                }
                #rm-mic-fab.rm-recording {
                    background: #FEE2E2; border-color: #EF4444;
                    animation: rm-mic-pulse 0.8s ease-in-out infinite;
                }
                #rm-voice-fab.rm-voice-on {
                    background: #EDE9FE; border-color: #7C3AED;
                }
                @keyframes rm-mic-pulse {
                    0%,100% { box-shadow: 0 0 0 0px rgba(239,68,68,0.4); }
                    50%      { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
                }
            `;
            DOC.head.appendChild(style);

            const micBtn = DOC.createElement('button');
            micBtn.id = 'rm-mic-fab';  micBtn.className = 'rm-fab';
            micBtn.title = 'Voice input';  micBtn.innerHTML = '🎙️';
            DOC.body.appendChild(micBtn);

            const voiceBtn = DOC.createElement('button');
            voiceBtn.id = 'rm-voice-fab';  voiceBtn.className = 'rm-fab';
            voiceBtn.title = 'Voice mode';  voiceBtn.innerHTML = '🗣️';
            DOC.body.appendChild(voiceBtn);

            // ── Mic FAB: click-to-record → transcribe → fill input ──────────
            let micRec, micChunks = [], micActive = false;
            micBtn.addEventListener('click', async () => {
                if (!micActive) {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({audio:true});
                        micRec = new MediaRecorder(stream);
                        micChunks = [];
                        micRec.ondataavailable = e => micChunks.push(e.data);
                        micRec.onstop = async () => {
                            micBtn.innerHTML = '⌛';
                            try {
                                const fd = new FormData();
                                fd.append('file', new Blob(micChunks,{type:'audio/webm'}), 'voice.webm');
                                const r = await fetch(BACKEND+'/query/transcribe',{method:'POST',body:fd});
                                const {text} = await r.json();
                                if (text) {
                                    const ta = DOC.querySelector('[data-testid="stChatInputTextArea"]');
                                    if (ta) {
                                        const s = Object.getOwnPropertyDescriptor(WIN.HTMLTextAreaElement.prototype,'value').set;
                                        s.call(ta, text);
                                        ta.dispatchEvent(new Event('input',{bubbles:true}));
                                        ta.focus();
                                    }
                                }
                            } finally { micBtn.innerHTML = '🎙️'; }
                        };
                        micRec.start();
                        micActive = true;
                        micBtn.innerHTML = '⏹️';
                        micBtn.classList.add('rm-recording');
                    } catch(e) { alert('Microphone access denied.'); }
                } else {
                    micRec.stop();
                    micRec.stream.getTracks().forEach(t => t.stop());
                    micActive = false;
                    micBtn.classList.remove('rm-recording');
                }
            });

            // ── Voice FAB: toggle voice mode ─────────────────────────────────
            voiceBtn.addEventListener('click', async () => {
                const isOn = !!DOC.getElementById('rm-voice-active');
                if (!isOn) {
                    // Must request mic on user gesture (AudioContext + permission)
                    try {
                        const ts = await navigator.mediaDevices.getUserMedia({audio:true});
                        ts.getTracks().forEach(t => t.stop());
                    } catch(e) { alert('Microphone access denied. Cannot start voice mode.'); return; }
                    if (!WIN._rmAudioCtx || WIN._rmAudioCtx.state === 'closed') {
                        WIN._rmAudioCtx = new WIN.AudioContext();
                    }
                    await WIN._rmAudioCtx.resume();
                    WIN._rmVoiceReady = true;
                    WIN._rmAborted = false;
                } else {
                    WIN._rmAborted = true;
                    WIN._rmVoiceReady = false;
                    WIN._rmProcessing = false;
                    DOC.body.classList.remove('rm-voice-thinking');
                    if (WIN._rmStopFn) WIN._rmStopFn();
                }
                const sel = isOn
                    ? '[class*="st-key-rm-voice-off"] button'
                    : '[class*="st-key-rm-voice-on"] button';
                const btn = DOC.querySelector(sel);
                if (btn) btn.click();
            });
        } // end firstRun

        // ── Helper functions — re-defined every render ─────────────────────
        // All DOM queries are fresh; all state via WIN._rm*

        function getCircle() { return DOC.getElementById('rm-voice-circle-main'); }

        function shouldRecord() {
            if (!DOC.getElementById('rm-voice-active')) return false;
            if (!WIN._rmVoiceReady || WIN._rmAborted) return false;
            if (WIN._rmRecording || WIN._rmProcessing) return false;
            if (!WIN._rmAudioCtx || WIN._rmAudioCtx.state !== 'running') return false;
            // Block while Streamlit is mid-rerun (LLM running = data-stale)
            if (DOC.querySelector('[data-testid="stApp"][data-stale="true"]')) return false;
            // Circle must be in DOM (page finished rendering)
            if (!getCircle()) return false;
            return true;
        }

        async function arStart() {
            if (!shouldRecord()) return;
            try {
                await WIN._rmAudioCtx.resume();
                const stream   = await navigator.mediaDevices.getUserMedia({audio:true});
                const analyser = WIN._rmAudioCtx.createAnalyser();
                analyser.fftSize = 512;
                WIN._rmAudioCtx.createMediaStreamSource(stream).connect(analyser);
                const recorder = new MediaRecorder(stream);
                const chunks   = [];
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = () => arProcess(chunks);
                recorder.start();
                WIN._rmRecorder    = recorder;
                WIN._rmStream      = stream;
                WIN._rmAnalyser    = analyser;
                WIN._rmRecording   = true;
                WIN._rmRecordStart = Date.now();
                WIN._rmSilStart    = null;
                // Use body class for circle state — React never touches document.body
                DOC.body.classList.remove('rm-voice-thinking');
                WIN.requestAnimationFrame(arCheckSilence);
            } catch(e) { console.error('arStart:', e); }
        }

        function arCheckSilence() {
            if (!WIN._rmRecording) return;
            const data = new Uint8Array(WIN._rmAnalyser.fftSize);
            WIN._rmAnalyser.getByteTimeDomainData(data);
            let sum = 0;
            for (let i = 0; i < data.length; i++) {
                const v = (data[i] - 128) / 128; sum += v * v;
            }
            const rms     = Math.sqrt(sum / data.length) * 128;
            const elapsed = Date.now() - WIN._rmRecordStart;
            if (rms < 13 && elapsed > 800) {
                if (!WIN._rmSilStart) WIN._rmSilStart = Date.now();
                if (Date.now() - WIN._rmSilStart >= 2500) { arStop(); return; }
            } else {
                WIN._rmSilStart = null;
            }
            WIN.requestAnimationFrame(arCheckSilence);
        }

        function arStop() {
            if (!WIN._rmRecording) return;
            WIN._rmRecording = false;
            if (WIN._rmRecorder) WIN._rmRecorder.stop();
            if (WIN._rmStream)   WIN._rmStream.getTracks().forEach(t => t.stop());
            // body class drives thinking animation — React can't overwrite it
            DOC.body.classList.add('rm-voice-thinking');
        }
        WIN._rmStopFn = arStop;  // expose latest version for voice FAB click handler

        async function arProcess(chunks) {
            if (WIN._rmAborted) { WIN._rmProcessing = false; DOC.body.classList.remove('rm-voice-thinking'); return; }
            WIN._rmProcessing = true;
            try {
                const fd = new FormData();
                fd.append('file', new Blob(chunks,{type:'audio/webm'}), 'voice.webm');
                const res    = await fetch(BACKEND+'/query/transcribe',{method:'POST',body:fd});
                const {text} = await res.json();
                if (text && !WIN._rmAborted) {
                    const ta = DOC.querySelector('[data-testid="stChatInputTextArea"]');
                    if (ta) {
                        const setter = Object.getOwnPropertyDescriptor(WIN.HTMLTextAreaElement.prototype,'value').set;
                        setter.call(ta, text);
                        ta.dispatchEvent(new Event('input', {bubbles:true}));
                        // Give React 100ms to enable the submit button, then try both methods
                        await new Promise(r => WIN.setTimeout(r, 100));
                        const sub = DOC.querySelector('[data-testid="stChatInputSubmitButton"]');
                        if (sub) {
                            sub.click();
                        } else {
                            ta.dispatchEvent(new KeyboardEvent('keydown', {
                                key:'Enter', code:'Enter', keyCode:13, bubbles:true, cancelable:true
                            }));
                        }
                    }
                }
            } catch(e) { console.error('arProcess:', e); }
            finally {
                // Small delay so Streamlit has time to mark data-stale before we clear _rmProcessing
                WIN.setTimeout(() => { WIN._rmProcessing = false; }, 300);
            }
        }

        function updatePosition() {
            const mic   = DOC.getElementById('rm-mic-fab');
            const voice = DOC.getElementById('rm-voice-fab');
            if (!mic || !voice) return;

            const inputBox = DOC.querySelector('[data-testid="stChatInput"]');
            const r        = inputBox ? inputBox.getBoundingClientRect() : null;
            const visible  = r && r.width > 0;

            if (!visible) {
                mic.style.opacity = '0'; mic.style.pointerEvents = 'none';
                const isMob = WIN.innerWidth <= 640;
                Object.assign(voice.style, {
                    bottom: '14px', top: 'auto', opacity: '1', pointerEvents: 'auto',
                    ...(isMob
                        ? {left:'50%', right:'auto', transform:'translateX(-50%)'}
                        : {right:'1.5rem', left:'auto', transform:'none'})
                });
                return;
            }
            const cx = r.left + r.width / 2;
            const isMobile = WIN.innerWidth <= 640;
            Object.assign(mic.style, {opacity:'1', pointerEvents:'auto', transform:'none'});
            Object.assign(voice.style, {opacity:'1', pointerEvents:'auto', transform:'none'});
            if (isMobile) {
                const btm = (WIN.innerHeight - r.top + 10) + 'px';
                Object.assign(mic.style,   {bottom:btm, top:'auto', left:(cx-52)+'px', right:'auto'});
                Object.assign(voice.style, {bottom:btm, top:'auto', left:(cx+8)+'px',  right:'auto'});
            } else {
                const mid = (r.top + r.height/2 - 22) + 'px';
                Object.assign(mic.style,   {top:mid, bottom:'auto', left:(r.right+8)+'px',  right:'auto'});
                Object.assign(voice.style, {top:mid, bottom:'auto', left:(r.right+60)+'px', right:'auto'});
            }
        }

        // ── Refresh intervals on every render ─────────────────────────────
        if (WIN._rmPollId)  WIN.clearInterval(WIN._rmPollId);
        if (WIN._rmPosId)   WIN.clearInterval(WIN._rmPosId);
        if (WIN._rmResFn)   WIN.removeEventListener('resize', WIN._rmResFn);

        WIN._rmPollId = WIN.setInterval(() => {
            if (shouldRecord()) arStart();
            const voiceActive = !!DOC.getElementById('rm-voice-active');
            if (!voiceActive) {
                if (WIN._rmRecording) { arStop(); WIN._rmProcessing = false; }
                DOC.body.classList.remove('rm-voice-thinking');
            }
            const vf = DOC.getElementById('rm-voice-fab');
            if (vf) {
                vf.innerHTML = voiceActive ? '🔴' : '🗣️';
                vf.classList.toggle('rm-voice-on', voiceActive);
            }
        }, 300);

        WIN._rmPosId = WIN.setInterval(updatePosition, 300);
        WIN._rmResFn = updatePosition;
        WIN.addEventListener('resize', WIN._rmResFn);
        updatePosition();

    })();