# JARVIS Voice Runtime

JARVIS uses a local-first voice pipeline. The dashboard can stay armed for a wake phrase, capture the following command, transcribe it locally, send the text through the normal router/agent path, and then speak the response.

## Runtime flow

`ARMED -> LISTENING -> TRANSCRIBING -> THINKING/EXECUTING -> SPEAKING -> ARMED`

The wake listener is only active while the desktop dashboard is running. Use the `WAKE WORD: ON/OFF` control in the runtime panel to disable or re-enable the always-on microphone listener. Manual `LISTEN` remains available when wake word is off or unavailable.

## Wake word

The default wake phrase is `Hey Jarvis`, implemented with openWakeWord using local 16 kHz mono PCM and ONNX inference on Windows. A short pause after the wake phrase is recommended before speaking the command because wake detection and command capture currently use separate microphone stream phases.

Defaults:

- `JARVIS_WAKE_WORD_ENABLED=1`
- `JARVIS_WAKE_WORD=hey_jarvis`
- `JARVIS_WAKE_THRESHOLD=0.62`
- `JARVIS_WAKE_VAD_THRESHOLD=0.45`

Example:

`Hey Jarvis` -> short pause -> `Chrome kholo`

The openWakeWord library code is Apache-2.0. Its bundled pre-trained wake-word models, including the pre-trained `hey_jarvis` model used by this development profile, have a non-commercial Creative Commons model license. Do not treat that pre-trained model as a commercial-distribution asset. If JARVIS is later distributed commercially, replace it with an appropriately licensed/custom wake model before release.

Model files are not committed to this repository. The wake model is downloaded on first use and then reused locally.

## Speech to text

The default STT provider is `faster-whisper`, loaded lazily and kept resident for the dashboard session. The default profile intentionally uses CPU INT8 so the local LLM can retain the GPU unless the user explicitly changes the STT profile.

Defaults:

- `JARVIS_STT_MODEL=small`
- `JARVIS_STT_DEVICE=cpu`
- `JARVIS_STT_COMPUTE=int8`

The Whisper model may download on first use. After it is cached, transcription is local. Google SpeechRecognition remains only as a compatibility/fallback provider when explicitly injected/configured.

## Current limitation

The first wake-word implementation is intentionally conservative: wake detection and the subsequent command recording are two separate audio phases. Therefore `Hey Jarvis, open Chrome` spoken as one uninterrupted phrase can lose the beginning of the command on some machines. The reliable form for this phase is `Hey Jarvis`, a short pause, then the command. The next voice-runtime refinement should use a single continuous audio stream with a pre-roll/ring buffer and VAD-driven utterance capture.
