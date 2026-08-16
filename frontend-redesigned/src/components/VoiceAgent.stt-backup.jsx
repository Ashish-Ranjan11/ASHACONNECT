import { useRef, useState } from "react";

const VOICE_API =
  import.meta.env.VITE_VOICE_API_URL ||
  "http://127.0.0.1:8010";


export default function VoiceAgent({
  token,
  onActionComplete,
}) {
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [error, setError] = useState("");


  async function startRecording() {
    try {
      setError("");
      setResponse("");

      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      const recorder = new MediaRecorder(stream);

      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(
          chunksRef.current,
          {
            type:
              recorder.mimeType ||
              "audio/webm",
          }
        );

        stream
          .getTracks()
          .forEach((track) => track.stop());

        await processAudio(blob);
      };

      recorderRef.current = recorder;

      recorder.start();

      setRecording(true);
    } catch (err) {
      console.error(err);

      setError(
        "Microphone access could not be started."
      );
    }
  }


  function stopRecording() {
    if (
      recorderRef.current &&
      recorderRef.current.state !== "inactive"
    ) {
      recorderRef.current.stop();
    }

    setRecording(false);
  }


  function speak(text) {
    if (!text) return;

    // Browser speech is a temporary fallback.
    // Backend TTS can replace this afterwards.
    window.speechSynthesis.cancel();

    const utterance =
      new SpeechSynthesisUtterance(text);

    utterance.lang = "hi-IN";

    window.speechSynthesis.speak(utterance);
  }


  async function processAudio(blob) {
    try {
      setProcessing(true);
      setError("");

      // ---------------------------------------------
      // 1. SPEECH -> TEXT
      // ---------------------------------------------

      const form = new FormData();

      form.append(
        "audio",
        blob,
        "asha-command.webm"
      );

      form.append(
        "language",
        "hi"
      );

      const transcriptionResponse =
        await fetch(
          `${VOICE_API}/voice/transcribe`,
          {
            method: "POST",
            body: form,
          }
        );

      const transcription =
        await transcriptionResponse.json();

      if (!transcriptionResponse.ok) {
        throw new Error(
          transcription.detail ||
          "Transcription failed"
        );
      }

      const text =
        transcription.text ||
        transcription.transcript ||
        transcription.transcription;

      if (!text) {
        throw new Error(
          "No speech was detected."
        );
      }

      setTranscript(text);


      // ---------------------------------------------
      // 2. TEXT -> GEMINI AGENT
      // ---------------------------------------------

      const agentResponse =
        await fetch(
          `${VOICE_API}/voice/agent`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,
            },

            body: JSON.stringify({
              text,
            }),
          }
        );

      const agent =
        await agentResponse.json();

      if (!agentResponse.ok) {
        throw new Error(
          agent.detail ||
          agent.error ||
          "Voice agent failed"
        );
      }

      const answer =
        agent.response ||
        "कार्य पूरा हो गया है।";

      setResponse(answer);

      speak(answer);


      // ---------------------------------------------
      // Refresh frontend database state
      // after successful actions.
      // ---------------------------------------------

      if (
        agent.type === "action_executed" ||
        agent.success
      ) {
        onActionComplete?.(agent);
      }

    } catch (err) {
      console.error(err);

      setError(
        err.message ||
        "Voice request failed."
      );
    } finally {
      setProcessing(false);
    }
  }


  return (
    <div className="asha-voice-agent">

      <button
        type="button"
        className={
          recording
            ? "voice-agent-button recording"
            : "voice-agent-button"
        }
        disabled={processing}
        onClick={
          recording
            ? stopRecording
            : startRecording
        }
      >
        {processing
          ? "Processing..."
          : recording
          ? "Stop"
          : "🎙️ Ask ASHA AI"}
      </button>


      {recording && (
        <div className="voice-agent-status">
          Listening...
        </div>
      )}


      {transcript && (
        <div className="voice-agent-transcript">
          <strong>You said:</strong>
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
