import { useEffect, useRef, useState } from "react";

const VOICE_API =
  import.meta.env.VITE_VOICE_API_URL ||
  "http://127.0.0.1:8010";

function httpToWs(url) {
  return url
    .replace(/^http:/, "ws:")
    .replace(/^https:/, "wss:");
}

function downsampleBuffer(
  buffer,
  inputSampleRate,
  outputSampleRate = 16000
) {
  if (inputSampleRate === outputSampleRate) {
    return buffer;
  }

  const ratio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round(
      (offsetResult + 1) * ratio
    );

    let accum = 0;
    let count = 0;

    for (
      let i = offsetBuffer;
      i < nextOffsetBuffer && i < buffer.length;
      i++
    ) {
      accum += buffer[i];
      count++;
    }

    result[offsetResult] =
      count > 0 ? accum / count : 0;

    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function float32ToPCM16(float32) {
  const pcm = new Int16Array(float32.length);

  for (let i = 0; i < float32.length; i++) {
    const sample = Math.max(
      -1,
      Math.min(1, float32[i])
    );

    pcm[i] =
      sample < 0
        ? sample * 0x8000
        : sample * 0x7fff;
  }

  return pcm.buffer;
}

export default function VoiceAgent({
  token,
  onActionComplete,
}) {
  const socketRef = useRef(null);

  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);

  const playbackContextRef = useRef(null);
  const playbackTimeRef = useRef(0);

  const [connected, setConnected] = useState(false);
  const [listening, setListening] = useState(false);
  const [status, setStatus] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  async function playPCM24k(arrayBuffer) {
    if (!playbackContextRef.current) {
      playbackContextRef.current =
        new AudioContext({
          sampleRate: 24000,
        });
    }

    const ctx = playbackContextRef.current;

    if (ctx.state === "suspended") {
      await ctx.resume();
    }

    const pcm = new Int16Array(arrayBuffer);

    const audioBuffer = ctx.createBuffer(
      1,
      pcm.length,
      24000
    );

    const channel = audioBuffer.getChannelData(0);

    for (let i = 0; i < pcm.length; i++) {
      channel[i] = pcm[i] / 32768;
    }

    const source = ctx.createBufferSource();

    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    const now = ctx.currentTime;

    const startAt = Math.max(
      now,
      playbackTimeRef.current
    );

    source.start(startAt);

    playbackTimeRef.current =
      startAt + audioBuffer.duration;
  }

  async function connect() {
    setError("");
    setStatus("connecting");

    if (!token) {
      setError(
        "Please login before using ASHA AI."
      );
      setStatus("error");
      return;
    }

    const wsBase = httpToWs(VOICE_API);

    const wsUrl =
      `${wsBase}/voice/live` +
      `?token=${encodeURIComponent(token)}`;

    const socket = new WebSocket(wsUrl);

    socket.binaryType = "arraybuffer";
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      setStatus("connected");
    };

    socket.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        await playPCM24k(event.data);
        return;
      }

      let message;

      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }

      if (message.type === "live_ready") {
        setStatus("ready");
        await startMicrophone();
        return;
      }

      if (message.type === "input_transcript") {
        setTranscript((previous) =>
          `${previous} ${message.text || ""}`.trim()
        );
        return;
      }

      if (message.type === "output_transcript") {
        setResponse((previous) =>
          `${previous} ${message.text || ""}`.trim()
        );
        return;
      }

      if (message.type === "action_executed") {
        onActionComplete?.(message);
        return;
      }

      if (message.type === "error") {
        setError(
          message.message ||
          "Gemini Live error"
        );

        setStatus("error");
      }
    };

    socket.onerror = (event) => {
      console.error("Voice socket error:", event);

      setError(
        "Could not connect to ASHA AI."
      );

      setStatus("error");
    };

    socket.onclose = () => {
      setConnected(false);
      setListening(false);

      if (status !== "error") {
        setStatus("idle");
      }

      stopMicrophone();
    };
  }

  async function startMicrophone() {
    try {
      if (
        !socketRef.current ||
        socketRef.current.readyState !== WebSocket.OPEN
      ) {
        return;
      }

      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

      streamRef.current = stream;

      const audioContext = new AudioContext();

      audioContextRef.current = audioContext;

      const source =
        audioContext.createMediaStreamSource(
          stream
        );

      sourceRef.current = source;

      const processor =
        audioContext.createScriptProcessor(
          4096,
          1,
          1
        );

      processorRef.current = processor;

      processor.onaudioprocess = (event) => {
        const socket = socketRef.current;

        if (
          !socket ||
          socket.readyState !== WebSocket.OPEN
        ) {
          return;
        }

        const input =
          event.inputBuffer.getChannelData(0);

        const downsampled =
          downsampleBuffer(
            input,
            audioContext.sampleRate,
            16000
          );

        const pcm =
          float32ToPCM16(downsampled);

        socket.send(pcm);
      };

      source.connect(processor);
      processor.connect(
        audioContext.destination
      );

      setListening(true);
      setStatus("listening");

    } catch (err) {
      console.error(err);

      setError(
        "Microphone access failed."
      );

      setStatus("error");
    }
  }

  function stopMicrophone() {
    if (processorRef.current) {
      try {
        processorRef.current.disconnect();
      } catch {}

      processorRef.current = null;
    }

    if (sourceRef.current) {
      try {
        sourceRef.current.disconnect();
      } catch {}

      sourceRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current
        .getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current
        .close()
        .catch(() => {});

      audioContextRef.current = null;
    }

    setListening(false);
  }

  function disconnect() {
    stopMicrophone();

    if (socketRef.current) {
      try {
        socketRef.current.close();
      } catch {}

      socketRef.current = null;
    }

    if (playbackContextRef.current) {
      playbackContextRef.current
        .close()
        .catch(() => {});

      playbackContextRef.current = null;
    }

    playbackTimeRef.current = 0;

    setConnected(false);
    setListening(false);
    setStatus("idle");
  }

  function toggleVoice() {
    setError("");

    // One click begins the continuous ASHA AI session.
    if (!connected) {
      setTranscript("");
      setResponse("");
      connect();
      return;
    }

    // Second click ends the entire conversation.
    disconnect();
  }

  const buttonText =
    status === "connecting"
      ? "Connecting..."
      : connected
      ? "■ End ASHA AI"
      : "🎙️ Ask ASHA AI";

  return (
    <div className="asha-voice-agent">
      <button
        type="button"
        className={
          listening
            ? "voice-agent-button recording"
            : "voice-agent-button"
        }
        onClick={toggleVoice}
        disabled={status === "connecting"}
      >
        {buttonText}
      </button>

      {status === "listening" && (
        <div className="voice-agent-status">
          ● ASHA AI is listening...
        </div>
      )}


      {transcript && (
        <div className="voice-agent-transcript">
          <strong>You:</strong>
          <div>{transcript}</div>
        </div>
      )}

      {response && (
        <div className="voice-agent-response">
          <strong>ASHA AI:</strong>
          <div>{response}</div>
        </div>
      )}

      {error && (
        <div className="voice-agent-error">
          {error}
        </div>
      )}
    </div>
  );
}
