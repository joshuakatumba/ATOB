import { useEffect, useRef, useState } from "react";
import { http } from "../lib/http.js";

function pickAudioMime() {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const mime of candidates) {
    try {
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(mime)) return mime;
    } catch { /* ignore */ }
  }
  return "";
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
    reader.onerror = () => reject(new Error("Could not read recorded audio."));
    reader.readAsDataURL(blob);
  });
}

function useMic(onText, notify) {
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const bars = useRef([]);
  const r = useRef({ heard: "", chunks: [] });

  const stop = async (keep) => {
    const s = r.current;
    r.current = { heard: "", chunks: [] };
    cancelAnimationFrame(s.raf);
    if (s.rec) { try { s.rec.stop(); } catch (e) { /* ignore */ } }
    if (s.ac) { try { s.ac.close(); } catch (e) { /* ignore */ } }

    let recordedBlob = null;
    if (s.media && s.media.state !== "inactive") {
      recordedBlob = await new Promise((resolve) => {
        s.media.onstop = () => {
          const mime = s.media.mimeType || s.mime || "audio/webm";
          const blob = s.chunks?.length ? new Blob(s.chunks, { type: mime }) : null;
          resolve(blob);
        };
        try {
          s.media.stop();
        } catch {
          resolve(null);
        }
      });
    } else if (s.chunks?.length) {
      recordedBlob = new Blob(s.chunks, { type: s.mime || "audio/webm" });
    }

    if (s.stream) s.stream.getTracks().forEach((t) => t.stop());

    if (!keep) {
      setText("");
      setBusy(false);
      setOn(false);
      return;
    }

    if (recordedBlob && recordedBlob.size > 200) {
      setBusy(true);
      setText("Transcribing audio\u2026");
      try {
        const base64 = await blobToBase64(recordedBlob);
        const res = await http("/v1/audio/transcribe", {
          body: {
            data_base64: base64,
            content_type: recordedBlob.type || s.mime || "audio/webm",
          },
        });
        const finalTranscript = (res?.text || "").trim() || (s.heard || "").trim();
        setText("");
        setBusy(false);
        setOn(false);
        if (finalTranscript) {
          onText(finalTranscript);
        } else {
          notify("No speech detected. Speak clearly into your microphone and try again.");
        }
        return;
      } catch (err) {
        const fallback = (s.heard || "").trim();
        setText("");
        setBusy(false);
        setOn(false);
        if (fallback) {
          onText(fallback);
        } else {
          notify(err?.message || "Could not transcribe audio.");
        }
        return;
      }
    }

    setText("");
    setBusy(false);
    setOn(false);
    if (s.heard && s.heard.trim()) {
      onText(s.heard.trim());
    } else {
      notify("No audio was captured. Check your microphone and try again.");
    }
  };

  const start = async () => {
    if (busy) return;
    if (!navigator.mediaDevices?.getUserMedia) return notify("Microphone is not supported in this browser");
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (e) {
      return notify("Microphone access was blocked. Allow it in your browser settings.");
    }
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    if (ac.resume) ac.resume();
    const an = ac.createAnalyser();
    an.fftSize = 64;
    ac.createMediaStreamSource(stream).connect(an);
    const d = new Uint8Array(an.frequencyBinCount);
    const s = { heard: "", stream, ac, chunks: [], mime: "audio/webm" };
    const loop = (t) => {
      an.getByteFrequencyData(d);
      bars.current.forEach((b, i) => {
        if (b) b.style.transform = `scaleY(${Math.min(1, 0.14 + (d[i % d.length] / 255) * 0.9 + 0.08 * Math.abs(Math.sin(t / 180 + i)))})`;
      });
      s.raf = requestAnimationFrame(loop);
    };
    s.raf = requestAnimationFrame(loop);

    if (typeof MediaRecorder !== "undefined") {
      try {
        const mime = pickAudioMime();
        const media = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
        s.mime = media.mimeType || mime || "audio/webm";
        media.ondataavailable = (ev) => {
          if (ev.data && ev.data.size > 0) s.chunks.push(ev.data);
        };
        media.start(250);
        s.media = media;
      } catch (e) { /* ignore */ }
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      try {
        const rec = new SR();
        rec.continuous = true;
        rec.interimResults = true;
        rec.onresult = (e) => {
          let x = "";
          for (let i = 0; i < e.results.length; i++) x += e.results[i][0].transcript;
          s.heard = x;
          setText(x);
        };
        rec.onerror = () => {};
        rec.start();
        s.rec = rec;
      } catch (e) { /* ignore */ }
    }
    r.current = s;
    setOn(true);
  };

  useEffect(() => () => { stop(false); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return { on, busy, text, bars, start, stop };
}

export default useMic;
